"""Simulador de redes de filas G/G/c/K para o Trabalho 2 (T2) - Metodos Analiticos.

Calcula:
  - Distribuicao de probabilidades dos estados P(N=n)
  - Clientes perdidos e taxa de descarte
  - Indices de desempenho das filas:
      * Populacao media no sistema (N ou L)
      * Populacao media na fila de espera (Nq ou Lq)
      * Populacao media em atendimento (Ns)
      * Utilizacao media dos servidores (U)
      * Vazao media do sistema/fila (X)
      * Tempo medio de resposta no sistema (W)
      * Tempo medio de espera na fila (Wq)
"""

from __future__ import annotations

import argparse
import heapq
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import yaml

EventType = Literal["external_arrival", "service_completion"]


class RandomBudgetExhausted(Exception):
    pass


class RandomSource:
    def __init__(self, seed: int | None = None, limit: int | None = None, explicit_numbers: list[float] | None = None) -> None:
        self.explicit_numbers = list(explicit_numbers) if explicit_numbers is not None else None
        self.explicit_idx = 0
        self.state = seed if seed is not None else 123456789
        self.remaining = limit if limit is not None else (len(self.explicit_numbers) if self.explicit_numbers else 100000)
        self.used = 0

    def next(self) -> float:
        if self.explicit_numbers is not None:
            if self.explicit_idx >= len(self.explicit_numbers):
                raise RandomBudgetExhausted
            val = self.explicit_numbers[self.explicit_idx]
            self.explicit_idx += 1
            self.used += 1
            return val

        if self.remaining <= 0:
            raise RandomBudgetExhausted
        self.state = (1664525 * self.state + 1013904223) % (2**32)
        self.remaining -= 1
        self.used += 1
        return self.state / (2**32)

    def uniform(self, minimum: float, maximum: float) -> float:
        return minimum + (maximum - minimum) * self.next()


@dataclass
class Queue:
    name: str
    servers: int
    capacity: int | None
    service_min: float
    service_max: float
    arrival_min: float | None = None
    arrival_max: float | None = None

    customers: int = 0
    losses: int = 0
    total_arrivals: int = 0
    completions: int = 0
    accumulated_times: list[float] = field(default_factory=list)
    last_state_change: float = 0.0

    def __post_init__(self) -> None:
        if self.servers < 1:
            raise ValueError(f"A fila {self.name} deve ter ao menos 1 servidor.")
        if self.capacity is not None and self.capacity < self.servers:
            raise ValueError(f"A capacidade da fila {self.name} deve ser >= numero de servidores.")
        if self.service_min > self.service_max:
            raise ValueError(f"Intervalo de servico invalido na fila {self.name}.")
        if self.capacity is not None:
            self.accumulated_times = [0.0] * (self.capacity + 1)

    def update_time(self, now: float) -> None:
        elapsed = now - self.last_state_change
        if self.capacity is None:
            while len(self.accumulated_times) <= self.customers:
                self.accumulated_times.append(0.0)
        self.accumulated_times[self.customers] += elapsed
        self.last_state_change = now

    def accepts_customer(self) -> bool:
        return self.capacity is None or self.customers < self.capacity


@dataclass
class QueueMetrics:
    queue_name: str
    kendall: str
    servers: int
    capacity: int | None
    losses: int
    loss_rate: float
    loss_probability: float
    completions: int
    throughput: float  # X
    population_total: float  # N
    population_queue: float  # Nq
    population_service: float  # Ns
    utilization: float  # U (0..1)
    response_time: float  # W
    queue_wait_time: float  # Wq
    probabilities: list[tuple[int, float, float]]  # (state, time, pct)


@dataclass
class NetworkMetrics:
    external_arrivals: float  # clientes que chegaram do exterior
    external_losses: float  # bloqueados ja na entrada da rede
    internal_losses: float  # bloqueados ao serem roteados entre filas
    departures: float  # sairam da rede apos atendimento
    arrival_rate: float  # lambda de clientes aceitos na rede
    throughput: float  # X da rede (saidas apos atendimento / tempo)
    population: float  # N da rede (soma das filas)
    response_time: float  # W da rede = N / lambda aceito (Little)
    loss_probability: float  # % dos clientes externos que foram perdidos


class QueueNetworkSimulator:
    def __init__(self, config: dict, seed: int | None = None) -> None:
        self.config = config
        
        # Gerenciamento de numeros aleatorios
        if "rndnumbers" in config and config["rndnumbers"]:
            self.random = RandomSource(explicit_numbers=config["rndnumbers"])
        else:
            limit = int(config.get("rndnumbersPerSeed", 100000))
            active_seed = seed if seed is not None else int(config.get("seeds", [123456789])[0])
            self.random = RandomSource(seed=active_seed, limit=limit)

        self.now = 0.0
        self.sequence = 0
        self.external_arrivals = 0
        self.external_losses = 0
        self.departures = 0
        self.events: list[tuple[float, int, EventType, str]] = []

        self.queues: dict[str, Queue] = {}
        for name, definition in config.get("queues", {}).items():
            self.queues[name] = Queue(
                name=name,
                servers=int(definition["servers"]),
                capacity=int(definition["capacity"]) if "capacity" in definition and definition["capacity"] is not None and int(definition["capacity"]) > 0 else None,
                service_min=float(definition["minService"]),
                service_max=float(definition["maxService"]),
                arrival_min=float(definition["minArrival"]) if "minArrival" in definition else None,
                arrival_max=float(definition["maxArrival"]) if "maxArrival" in definition else None,
            )

        self.arrivals = config.get("arrivals", {})
        self.routes: dict[str, list[tuple[str, float]]] = {}
        for route in config.get("network", []):
            self.routes.setdefault(route["source"], []).append(
                (route["target"], float(route["probability"]))
            )

    def schedule(self, time: float, event_type: EventType, queue_name: str) -> None:
        self.sequence += 1
        heapq.heappush(self.events, (time, self.sequence, event_type, queue_name))

    def schedule_service(self, queue: Queue) -> None:
        duration = self.random.uniform(queue.service_min, queue.service_max)
        self.schedule(self.now + duration, "service_completion", queue.name)

    def receive_customer(self, queue_name: str) -> None:
        queue = self.queues[queue_name]
        queue.update_time(self.now)
        queue.total_arrivals += 1

        if not queue.accepts_customer():
            queue.losses += 1
            return

        queue.customers += 1
        if queue.customers <= queue.servers:
            self.schedule_service(queue)

    def route_customer(self, source: str) -> None:
        routes = self.routes.get(source, [])
        if not routes:
            self.departures += 1
            return

        # Rota deterministica unica de 100% nao consome numero aleatorio
        if len(routes) == 1 and abs(routes[0][1] - 1.0) < 1e-9:
            self.receive_customer(routes[0][0])
            return

        choice = self.random.next()
        cumulative = 0.0
        for target, probability in routes:
            cumulative += probability
            if choice < cumulative:
                self.receive_customer(target)
                return
        # Se choice >= cumulative total, o cliente sai da rede
        self.departures += 1

    def handle_external_arrival(self, queue_name: str) -> None:
        queue = self.queues[queue_name]
        losses_before = queue.losses
        self.receive_customer(queue_name)
        self.external_arrivals += 1
        self.external_losses += queue.losses - losses_before
        if queue.arrival_min is not None and queue.arrival_max is not None:
            interval = self.random.uniform(queue.arrival_min, queue.arrival_max)
            self.schedule(self.now + interval, "external_arrival", queue_name)

    def handle_service_completion(self, queue_name: str) -> None:
        queue = self.queues[queue_name]
        queue.update_time(self.now)
        queue.customers -= 1
        queue.completions += 1

        if queue.customers >= queue.servers:
            self.schedule_service(queue)

        self.route_customer(queue_name)

    def run(self) -> None:
        for queue_name, first_arrival in self.arrivals.items():
            self.schedule(float(first_arrival), "external_arrival", queue_name)

        while self.events and self.random.remaining > 0:
            self.now, _, event_type, queue_name = heapq.heappop(self.events)
            try:
                if event_type == "external_arrival":
                    self.handle_external_arrival(queue_name)
                else:
                    self.handle_service_completion(queue_name)
            except RandomBudgetExhausted:
                break

        for queue in self.queues.values():
            queue.update_time(self.now)

    def compute_metrics(self) -> dict[str, QueueMetrics]:
        results: dict[str, QueueMetrics] = {}
        total_time = self.now if self.now > 0 else 1.0

        for name, queue in self.queues.items():
            cap_str = "inf" if queue.capacity is None else str(queue.capacity)
            kendall = f"G/G/{queue.servers}/{cap_str}"

            # Distribuicao de probabilidades
            prob_list: list[tuple[int, float, float]] = []
            n_total = 0.0
            n_queue = 0.0
            n_service = 0.0

            for state, acc_time in enumerate(queue.accumulated_times):
                prob = acc_time / total_time
                prob_pct = prob * 100.0
                prob_list.append((state, acc_time, prob_pct))

                # Populacao total
                n_total += state * prob

                # Fila de espera vs servidores
                if state > queue.servers:
                    n_queue += (state - queue.servers) * prob
                    n_service += queue.servers * prob
                else:
                    n_service += state * prob

            # Utilizacao
            utilization = n_service / queue.servers if queue.servers > 0 else 0.0

            # Vazao (throughput) = atendimentos concluidos / tempo total
            throughput = queue.completions / total_time

            # Tempos de resposta (Little)
            if throughput > 0:
                response_time = n_total / throughput
                wait_time = n_queue / throughput
            else:
                response_time = 0.0
                wait_time = 0.0

            loss_rate = queue.losses / total_time
            loss_prob = (queue.losses / queue.total_arrivals * 100.0) if queue.total_arrivals > 0 else 0.0

            results[name] = QueueMetrics(
                queue_name=name,
                kendall=kendall,
                servers=queue.servers,
                capacity=queue.capacity,
                losses=queue.losses,
                loss_rate=loss_rate,
                loss_probability=loss_prob,
                completions=queue.completions,
                throughput=throughput,
                population_total=n_total,
                population_queue=n_queue,
                population_service=n_service,
                utilization=utilization,
                response_time=response_time,
                queue_wait_time=wait_time,
                probabilities=prob_list,
            )

        return results

    def compute_network_metrics(self) -> NetworkMetrics:
        total_time = self.now if self.now > 0 else 1.0
        total_losses = sum(q.losses for q in self.queues.values())
        internal_losses = total_losses - self.external_losses
        accepted = self.external_arrivals - self.external_losses
        arrival_rate = accepted / total_time
        population = sum(m.population_total for m in self.compute_metrics().values())
        return NetworkMetrics(
            external_arrivals=self.external_arrivals,
            external_losses=self.external_losses,
            internal_losses=internal_losses,
            departures=self.departures,
            arrival_rate=arrival_rate,
            throughput=self.departures / total_time,
            population=population,
            response_time=population / arrival_rate if arrival_rate > 0 else 0.0,
            loss_probability=(total_losses / self.external_arrivals * 100.0) if self.external_arrivals > 0 else 0.0,
        )


def _average(values: list) -> float:
    return sum(values) / len(values)


def _average_dataclass(items: list, cls):
    """Media campo a campo de dataclasses com campos numericos."""
    first = items[0]
    averaged = {}
    for name in first.__dataclass_fields__:
        value = getattr(first, name)
        if isinstance(value, (int, float)) and not isinstance(value, bool) and name not in ("servers", "capacity"):
            averaged[name] = _average([getattr(item, name) for item in items])
        else:
            averaged[name] = value
    return cls(**averaged)


@dataclass
class ReplicationResult:
    seeds: list[int]
    simulation_time: float
    random_used: float
    queues: dict[str, QueueMetrics]
    network: NetworkMetrics
    queue_configs: dict[str, Queue]


def run_replications(config: dict) -> ReplicationResult:
    """Executa uma simulacao por semente do YAML e retorna a media dos indices."""
    if config.get("rndnumbers"):
        seeds: list[int] = [0]  # semente ignorada: usa a lista fixa
    else:
        seeds = [int(s) for s in config.get("seeds", [123456789])]

    sims = []
    for seed in seeds:
        sim = QueueNetworkSimulator(config, seed=seed)
        sim.run()
        sims.append(sim)

    per_seed = [sim.compute_metrics() for sim in sims]
    queues: dict[str, QueueMetrics] = {}
    for name in per_seed[0]:
        items = [m[name] for m in per_seed]
        averaged = _average_dataclass(items, QueueMetrics)
        n_states = max(len(m.probabilities) for m in items)
        probabilities = []
        for state in range(n_states):
            times = [m.probabilities[state][1] if state < len(m.probabilities) else 0.0 for m in items]
            pcts = [m.probabilities[state][2] if state < len(m.probabilities) else 0.0 for m in items]
            probabilities.append((state, _average(times), _average(pcts)))
        averaged.probabilities = probabilities
        queues[name] = averaged

    return ReplicationResult(
        seeds=seeds,
        simulation_time=_average([sim.now for sim in sims]),
        random_used=_average([sim.random.used for sim in sims]),
        queues=queues,
        network=_average_dataclass([sim.compute_network_metrics() for sim in sims], NetworkMetrics),
        queue_configs=sims[0].queues,
    )


def report(result: ReplicationResult) -> str:
    metrics = result.queues
    net = result.network
    seeds_str = ", ".join(str(s) for s in result.seeds)
    lines: list[str] = [
        "=" * 70,
        "         RELATORIO COMPLETO DE SIMULACAO DA REDE DE FILAS",
        "=" * 70,
        f"Sementes ({len(result.seeds)}): {seeds_str}" if result.seeds != [0] else "Aleatorios: lista fixa (rndnumbers)",
        f"Tempo global da simulacao (media): {result.simulation_time:.4f}",
        f"Numeros aleatorios utilizados (por semente): {result.random_used:.0f}",
        "",
    ]

    # Tabela resumo de Indices de Desempenho
    lines.extend([
        "-" * 70,
        "               INDICES DE DESEMPENHO POR FILA",
        "-" * 70,
        f"{'Fila':<14} | {'Kendall':<10} | {'Utilizacao':<10} | {'Vazao (X)':<10} | {'N (Pop)':<8} | {'Nq (Fila)':<9} | {'W (Resp)':<8} | {'Perdas':<8}",
        "-" * 70,
    ])
    for q_name, m in metrics.items():
        lines.append(
            f"{q_name:<14} | {m.kendall:<10} | {m.utilization * 100:>9.2f}% | {m.throughput:>10.4f} | {m.population_total:>8.3f} | {m.population_queue:>9.3f} | {m.response_time:>8.3f} | {m.losses:>8.1f}"
        )
    lines.append("-" * 70)
    lines.extend([
        "Rede completa:",
        f"  Chegadas externas: {net.external_arrivals:.1f} | Perdas na entrada: {net.external_losses:.1f} | Perdas internas: {net.internal_losses:.1f}",
        f"  Taxa de chegada aceita (lambda): {net.arrival_rate:.4f} | Vazao de saida (X): {net.throughput:.4f}",
        f"  Populacao media na rede (N): {net.population:.3f}",
        f"  Tempo medio de permanencia na rede (W = N / lambda): {net.response_time:.3f}",
        f"  Clientes perdidos: {net.loss_probability:.2f}% das chegadas externas",
        "-" * 70,
        "",
    ])

    # Detalhamento estado por estado
    for q_name, m in metrics.items():
        q = result.queue_configs[q_name]
        lines.extend([
            "*" * 60,
            f"Fila: {q_name} ({m.kendall})",
        ])
        if q.arrival_min is not None and q.arrival_max is not None:
            lines.append(f"Chegadas externas: {q.arrival_min:.1f} ... {q.arrival_max:.1f}")
        lines.append(f"Tempo de atendimento: {q.service_min:.1f} ... {q.service_max:.1f}")
        lines.append("*" * 60)
        lines.append(f"{'Estado':>8} | {'Tempo Acumulado':>18} | {'Probabilidade':>14}")
        lines.append("-" * 46)
        for state, acc_time, prob_pct in m.probabilities:
            lines.append(f"{state:8d} | {acc_time:18.4f} | {prob_pct:13.2f}%")
        lines.append(f"Perdas de clientes: {m.losses:.1f} ({m.loss_probability:.2f}% dos clientes)")
        lines.append(f"Tempo medio de espera na fila (Wq): {m.queue_wait_time:.4f}")
        lines.append(f"Tempo medio de resposta total (W):  {m.response_time:.4f}")
        lines.append("")

    return "\n".join(lines)


def load_yaml_config(path: str | Path) -> dict:
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Arquivo nao encontrado: {path}")
    with file_path.open("r", encoding="utf-8") as f:
        content = f.read()
    clean_content = re.sub(r"^!PARAMETERS\s*\n", "", content, flags=re.MULTILINE)
    return yaml.safe_load(clean_content)


def compare_models(path_base: str, path_improved: str) -> str:
    r1 = run_replications(load_yaml_config(path_base))
    m1 = r1.queues

    r2 = run_replications(load_yaml_config(path_improved))
    m2 = r2.queues

    lines = [
        "=" * 85,
        "         COMPARATIVO: MODELO BASE (ATUAL) vs MODELO MELHORADO (FUTURO)",
        "=" * 85,
        f"Tempo Simulacao Base: {r1.simulation_time:.2f} | Tempo Simulacao Melhorado: {r2.simulation_time:.2f}",
        "-" * 85,
        f"{'Metrica / Fila':<24} | {'Modelo Base (Atual)':<26} | {'Modelo Melhorado':<26}",
        "-" * 85,
    ]

    all_queues = sorted(set(list(m1.keys()) + list(m2.keys())))
    for q_name in all_queues:
        lines.append(f">> Fila: {q_name}")
        b = m1.get(q_name)
        imp = m2.get(q_name)

        if b and imp:
            lines.append(f"   Kendall:                | {b.kendall:<26} | {imp.kendall:<26}")
            lines.append(f"   Utilizacao (U):         | {b.utilization*100:>24.2f}% | {imp.utilization*100:>24.2f}%")
            lines.append(f"   Vazao (X):              | {b.throughput:>25.4f} | {imp.throughput:>25.4f}")
            lines.append(f"   Populacao media (N):    | {b.population_total:>25.3f} | {imp.population_total:>25.3f}")
            lines.append(f"   Fila de espera (Nq):    | {b.population_queue:>25.3f} | {imp.population_queue:>25.3f}")
            lines.append(f"   Tempo de Resposta (W):  | {b.response_time:>25.3f} | {imp.response_time:>25.3f}")
            lines.append(f"   Espera na fila (Wq):    | {b.queue_wait_time:>25.3f} | {imp.queue_wait_time:>25.3f}")
            lines.append(f"   Perdas de clientes:     | {b.losses:>25.1f} | {imp.losses:>25.1f}")
        lines.append("-" * 85)

    n1, n2 = r1.network, r2.network
    lines.append(">> Rede completa")
    lines.append(f"   Populacao na rede (N):  | {n1.population:>25.3f} | {n2.population:>25.3f}")
    lines.append(f"   Vazao de saida (X):     | {n1.throughput:>25.4f} | {n2.throughput:>25.4f}")
    lines.append(f"   Permanencia (W):        | {n1.response_time:>25.3f} | {n2.response_time:>25.3f}")
    lines.append(f"   Clientes perdidos (%):  | {n1.loss_probability:>24.2f}% | {n2.loss_probability:>24.2f}%")
    lines.append("-" * 85)

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulador de Redes de Filas - Trabalho T2 (Metodos Analiticos)")
    parser.add_argument("config", nargs="?", default="t2_modelo.yml", help="Caminho do arquivo YAML do modelo")
    parser.add_argument("--compare", nargs=2, metavar=("BASE", "MELHORADO"), help="Compara dois modelos YAML (Base vs Melhorado)")
    args = parser.parse_args()

    if args.compare:
        print(compare_models(args.compare[0], args.compare[1]))
        return

    config_path = Path(args.config)
    if not config_path.exists():
        local_path = Path(__file__).resolve().parent / args.config
        if local_path.exists():
            config_path = local_path

    config = load_yaml_config(config_path)
    print(report(run_replications(config)))


if __name__ == "__main__":
    main()

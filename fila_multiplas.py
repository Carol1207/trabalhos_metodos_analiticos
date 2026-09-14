#!/usr/bin/env python3
"""Simulador de redes de filas G/G/c/K configuradas em YAML."""

from __future__ import annotations

import argparse
import heapq
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import yaml


EventType = Literal["external_arrival", "service_completion"]


class RandomBudgetExhausted(Exception):
    pass


class RandomSource:
    def __init__(self, seed: int, limit: int) -> None:
        self.state = seed
        self.remaining = limit
        self.used = 0

    def next(self) -> float:
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
    customers: int = 0
    losses: int = 0
    accumulated_times: list[float] = field(default_factory=list)
    last_state_change: float = 0.0

    def __post_init__(self) -> None:
        if self.servers < 1:
            raise ValueError(f"A fila {self.name} deve ter ao menos um servidor.")
        if self.capacity is not None and self.capacity < self.servers:
            raise ValueError(f"A capacidade de {self.name} deve ser >= servidores.")
        if self.service_min > self.service_max:
            raise ValueError(f"Intervalo de atendimento invalido em {self.name}.")
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


class QueueNetworkSimulator:
    def __init__(self, config: dict) -> None:
        simulation = config["simulation"]
        self.random = RandomSource(int(simulation.get("seed", 123456789)), int(simulation["random_numbers"]))
        self.now = 0.0
        self.sequence = 0
        self.events: list[tuple[float, int, EventType, str]] = []
        self.queues = {
            name: Queue(
                name=name,
                servers=int(definition["servers"]),
                capacity=definition.get("capacity"),
                service_min=float(definition["service_interval"][0]),
                service_max=float(definition["service_interval"][1]),
            )
            for name, definition in config["queues"].items()
        }
        self.arrivals = config.get("external_arrivals", {})
        self.routes: dict[str, list[tuple[str, float]]] = {}
        for route in config.get("network", []):
            source, target, probability = route["source"], route["target"], float(route["probability"])
            if source not in self.queues or target not in self.queues:
                raise ValueError(f"Rota invalida: {source} -> {target}.")
            self.routes.setdefault(source, []).append((target, probability))
        self._validate_config()

    def _validate_config(self) -> None:
        for queue_name, arrival in self.arrivals.items():
            if queue_name not in self.queues:
                raise ValueError(f"Chegada externa para fila inexistente: {queue_name}.")
            interval = arrival["interval"]
            if len(interval) != 2 or interval[0] > interval[1]:
                raise ValueError(f"Intervalo de chegada invalido em {queue_name}.")
        for source, routes in self.routes.items():
            total = sum(probability for _, probability in routes)
            if any(probability < 0 for _, probability in routes) or total > 1.0 + 1e-12:
                raise ValueError(f"Probabilidades de roteamento invalidas em {source}.")

    def schedule(self, time: float, event_type: EventType, queue_name: str) -> None:
        self.sequence += 1
        heapq.heappush(self.events, (time, self.sequence, event_type, queue_name))

    def schedule_service(self, queue: Queue) -> None:
        duration = self.random.uniform(queue.service_min, queue.service_max)
        self.schedule(self.now + duration, "service_completion", queue.name)

    def receive_customer(self, queue_name: str) -> None:
        queue = self.queues[queue_name]
        queue.update_time(self.now)
        if not queue.accepts_customer():
            queue.losses += 1
            return
        queue.customers += 1
        if queue.customers <= queue.servers:
            self.schedule_service(queue)

    def route_customer(self, source: str) -> None:
        routes = self.routes.get(source, [])
        if not routes:
            return
        if len(routes) == 1 and routes[0][1] == 1.0:
            self.receive_customer(routes[0][0])
            return
        choice = self.random.next()
        cumulative = 0.0
        for target, probability in routes:
            cumulative += probability
            if choice < cumulative:
                self.receive_customer(target)
                return

    def handle_external_arrival(self, queue_name: str) -> None:
        self.receive_customer(queue_name)
        interval = self.arrivals[queue_name]["interval"]
        next_time = self.now + self.random.uniform(float(interval[0]), float(interval[1]))
        self.schedule(next_time, "external_arrival", queue_name)

    def handle_service_completion(self, queue_name: str) -> None:
        queue = self.queues[queue_name]
        queue.update_time(self.now)
        queue.customers -= 1
        if queue.customers >= queue.servers:
            self.schedule_service(queue)
        self.route_customer(queue_name)

    def run(self) -> None:
        for queue_name, arrival in self.arrivals.items():
            self.schedule(float(arrival["first_arrival"]), "external_arrival", queue_name)
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

    def report(self) -> str:
        lines = [
            "RESULTADOS DA SIMULACAO DE REDE DE FILAS",
            f"Tempo global da simulacao: {self.now:.4f}",
            f"Aleatorios utilizados: {self.random.used}",
        ]
        for queue in self.queues.values():
            capacity = "infinita" if queue.capacity is None else str(queue.capacity)
            lines.extend(["", f"Fila {queue.name} (G/G/{queue.servers}/{capacity})", "Estado | Tempo acumulado | Probabilidade"])
            for state, accumulated in enumerate(queue.accumulated_times):
                probability = 0.0 if self.now == 0 else 100 * accumulated / self.now
                lines.append(f"{state:6d} | {accumulated:15.4f} | {probability:11.4f}%")
            lines.append(f"Perdas de clientes: {queue.losses}")
        return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Simula uma rede generica de filas G/G/c/K.")
    parser.add_argument("config", nargs="?", default="tandem.yml", help="arquivo YAML de configuracao")
    arguments = parser.parse_args()
    with Path(arguments.config).open(encoding="utf-8") as config_file:
        simulator = QueueNetworkSimulator(yaml.safe_load(config_file))
    simulator.run()
    print(simulator.report())


if __name__ == "__main__":
    main()
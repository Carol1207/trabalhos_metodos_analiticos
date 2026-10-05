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
    arrival_min: float | None = None
    arrival_max: float | None = None
    customers: int = 0
    losses: int = 0
    accumulated_times: list[float] = field(default_factory=list)
    last_state_change: float = 0.0

    def __post_init__(self) -> None:
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
        # Pega a configuração baseado na sintaxe do YAML do modulo 3
        seed = config.get("seeds", [123456789])[0]
        random_numbers = config.get("rndnumbersPerSeed", 100000)
        self.random = RandomSource(int(seed), int(random_numbers))
        
        self.now = 0.0
        self.sequence = 0
        self.events: list[tuple[float, int, EventType, str]] = []
        
        self.queues = {}
        for name, definition in config.get("queues", {}).items():
            self.queues[name] = Queue(
                name=name,
                servers=int(definition["servers"]),
                capacity=definition.get("capacity"),
                service_min=float(definition["minService"]),
                service_max=float(definition["maxService"]),
                arrival_min=float(definition["minArrival"]) if "minArrival" in definition else None,
                arrival_max=float(definition["maxArrival"]) if "maxArrival" in definition else None,
            )
            
        self.arrivals = config.get("arrivals", {})
        self.routes: dict[str, list[tuple[str, float]]] = {}
        for route in config.get("network", []):
            self.routes.setdefault(route["source"], []).append((route["target"], float(route["probability"])))

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
        choice = self.random.next()
        cumulative = 0.0
        for target, probability in routes:
            cumulative += probability
            if choice < cumulative:
                self.receive_customer(target)
                return

    def handle_external_arrival(self, queue_name: str) -> None:
        self.receive_customer(queue_name)
        queue = self.queues[queue_name]
        if queue.arrival_min is not None and queue.arrival_max is not None:
            next_time = self.now + self.random.uniform(queue.arrival_min, queue.arrival_max)
            self.schedule(next_time, "external_arrival", queue_name)

    def handle_service_completion(self, queue_name: str) -> None:
        queue = self.queues[queue_name]
        queue.update_time(self.now)
        queue.customers -= 1
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
    parser = argparse.ArgumentParser()
    parser.add_argument("config", nargs="?", default="t1_modelo.yml")
    args = parser.parse_args()
    
    with Path(args.config).open(encoding="utf-8") as f:
        yaml_content = f.read()
        
    # Remove a tag customizada "!PARAMETERS" que quebra o interpretador pyyaml padrão
    clean_yaml = re.sub(r'^!PARAMETERS\s*\n', '', yaml_content, flags=re.MULTILINE)
    config = yaml.safe_load(clean_yaml)
    
    simulator = QueueNetworkSimulator(config)
    simulator.run()
    print(simulator.report())

if __name__ == "__main__":
    main()
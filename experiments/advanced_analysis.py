from __future__ import annotations

import csv
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from genetic_algorithm.fitness import Fitness
from genetic_algorithm.individual import Individual
from genetic_algorithm.solver import GeneticAlgorithmSolver
from puzzle.board import Board

RESULTS_DIR = ROOT / "experiments" / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def _write_csv(path: Path, rows: Sequence[Dict[str, Any]], fieldnames: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _fitness_cases() -> List[Dict[str, Any]]:
    cases: List[Dict[str, Any]] = [
        {
            "id": "solved",
            "initial_state": [1, 2, 3, 4, 5, 6, 7, 8, 0],
            "chromosome": ["R"],
            "description": "resolve em um movimento",
        },
        {
            "id": "distance_reduction",
            "initial_state": [1, 2, 3, 4, 5, 6, 0, 8, 7],
            "chromosome": ["R"],
            "description": "reduz Manhattan sem resolver",
        },
        {
            "id": "manhattan_increase",
            "initial_state": [1, 2, 3, 4, 5, 6, 7, 0, 8],
            "chromosome": ["U", "L"],
            "description": "aumenta a distância de Manhattan",
        },
        {
            "id": "same_initial_distance",
            "initial_state": [1, 2, 3, 4, 0, 6, 7, 5, 8],
            "chromosome": ["L", "L"],
            "description": "mesma distância inicial e estado final diferente",
        },
        {
            "id": "invalid_moves",
            "initial_state": [1, 2, 3, 4, 5, 6, 7, 0, 8],
            "chromosome": ["U", "D"],
            "description": "movimentos inválidos",
        },
        {
            "id": "same_state_different_lengths_a",
            "initial_state": [1, 2, 3, 4, 5, 6, 7, 0, 8],
            "chromosome": ["L", "L"],
            "description": "estado final repetido com sequência mais curta",
        },
        {
            "id": "same_state_different_lengths_b",
            "initial_state": [1, 2, 3, 4, 5, 6, 7, 0, 8],
            "chromosome": ["L", "L", "R"],
            "description": "mesmo estado final com sequência mais longa",
        },
        {
            "id": "different_states_same_length",
            "initial_state": [1, 2, 3, 4, 0, 6, 7, 5, 8],
            "chromosome": ["R", "R"],
            "description": "estados finais diferentes com mesmo comprimento",
        },
        {
            "id": "mixed_penalties",
            "initial_state": [1, 2, 3, 4, 5, 6, 0, 8, 7],
            "chromosome": ["R", "U", "R"],
            "description": "combinação de distância, comprimento e movimentos inválidos",
        },
    ]

    all_records: List[Dict[str, Any]] = []
    for case in cases:
        board = Board(3, case["initial_state"])
        individual = Individual(chromosome=case["chromosome"], initial_board=board)
        simulation = individual.simulate()
        initial_manhattan = Board(3, case["initial_state"]).manhattan_distance()
        final_manhattan = simulation["manhattan_distance"]
        score = Fitness().evaluate(individual)
        all_records.append(
            {
                "case_id": case["id"],
                "initial_state": case["initial_state"],
                "chromosome": case["chromosome"],
                "final_state": simulation["final_state"],
                "goal_reached": bool(simulation["solved"]),
                "initial_manhattan": initial_manhattan,
                "final_manhattan": final_manhattan,
                "invalid_moves": simulation["invalid_moves"],
                "chromosome_length": len(case["chromosome"]),
                "fitness": float(score),
                "description": case["description"],
            }
        )

    ordered = sorted(all_records, key=lambda row: row["fitness"], reverse=True)
    for position, row in enumerate(ordered, start=1):
        row["ranking_by_fitness"] = position

    return all_records


def _scenario_parameters() -> Dict[str, Any]:
    return {
        "population_size": 10,
        "initial_chromosome_length": 6,
        "max_generations": 12,
        "crossover_rate": 0.7,
        "mutation_rate": 0.2,
        "tournament_size": 2,
        "elites_count": 1,
        "max_chromosome_length": 20,
        "time_limit": 3.0,
    }


def _scenario_configs() -> List[Dict[str, Any]]:
    return [
        {
            "id": "3x3_easy",
            "size": 3,
            "initial_state": [1, 2, 3, 4, 5, 6, 7, 8, 0],
            "description": "estado objetivo",
            "params": _scenario_parameters(),
        },
        {
            "id": "3x3_medium",
            "size": 3,
            "initial_state": [1, 2, 3, 4, 0, 6, 7, 5, 8],
            "description": "estado médio",
            "params": _scenario_parameters(),
        },
        {
            "id": "3x3_hard",
            "size": 3,
            "initial_state": [8, 6, 7, 2, 5, 4, 3, 0, 1],
            "description": "estado difícil",
            "params": _scenario_parameters(),
        },
        {
            "id": "4x4_seed_100",
            "size": 4,
            "initial_state": [1, 2, 3, 4, 5, 6, 7, 8, 10, 15, 0, 11, 9, 13, 14, 12],
            "description": "estado 4x4 gerado com seed 100",
            "params": _scenario_parameters(),
        },
    ]


def _diversity_metrics(population: Sequence[Individual]) -> Dict[str, Any]:
    if not population:
        return {
            "distinct_chromosomes": 0,
            "distinct_final_states": 0,
            "duplicate_ratio": 0.0,
            "best_manhattan_achieved": 0,
            "best_fitness": 0.0,
            "average_fitness": 0.0,
            "max_manhattan_achieved": 0,
        }

    fitness = Fitness()
    scored = [(individual, fitness.evaluate(individual)) for individual in population]
    best_individual, best_fitness = max(scored, key=lambda item: item[1])
    best_result = best_individual.simulate()
    final_states = [tuple(individual.simulate()["final_state"]) for individual in population]
    distinct_states = len(set(final_states))
    distinct_chromosomes = len({tuple(individual.chromosome) for individual in population})
    duplicate_ratio = 1.0 - (distinct_chromosomes / len(population)) if population else 0.0
    manhattan_values = [individual.simulate()["manhattan_distance"] for individual in population]
    average_fitness = sum(score for _, score in scored) / len(scored)

    return {
        "distinct_chromosomes": distinct_chromosomes,
        "distinct_final_states": distinct_states,
        "duplicate_ratio": duplicate_ratio,
        "best_manhattan_achieved": min(manhattan_values),
        "max_manhattan_achieved": max(manhattan_values),
        "best_fitness": best_fitness,
        "average_fitness": average_fitness,
        "best_chromosome_length": len(best_individual.chromosome),
        "best_manhattan_result": best_result["manhattan_distance"],
    }


class EvaluationProbe:
    def __init__(self) -> None:
        self.current_generation = 0
        self.evaluate_calls = 0
        self.simulate_calls = 0
        self.calls_by_generation: Dict[int, Dict[str, int]] = {}
        self.generation_records: List[Dict[str, Any]] = []
        self.original_evaluate = Individual.evaluate
        self.original_simulate = Individual.simulate

    def install(self) -> None:
        def counted_evaluate(self_obj: Individual, *args: Any, **kwargs: Any) -> Dict[str, Any]:
            self.evaluate_calls += 1
            self.calls_by_generation.setdefault(self.current_generation, {"evaluate": 0, "simulate": 0})["evaluate"] += 1
            return self.original_evaluate(self_obj, *args, **kwargs)

        def counted_simulate(self_obj: Individual, *args: Any, **kwargs: Any) -> Dict[str, Any]:
            self.simulate_calls += 1
            self.calls_by_generation.setdefault(self.current_generation, {"evaluate": 0, "simulate": 0})["simulate"] += 1
            return self.original_simulate(self_obj, *args, **kwargs)

        Individual.evaluate = counted_evaluate
        Individual.simulate = counted_simulate

    def uninstall(self) -> None:
        Individual.evaluate = self.original_evaluate
        Individual.simulate = self.original_simulate

    def observe_generation(self, population: Sequence[Individual], generation: int) -> Dict[str, Any]:
        metrics = _diversity_metrics(population)
        metrics["generation"] = generation
        metrics["distinct_chromosomes"] = metrics["distinct_chromosomes"]
        metrics["distinct_final_states"] = metrics["distinct_final_states"]
        metrics["duplicate_ratio"] = metrics["duplicate_ratio"]
        metrics["calls_evaluate_generation"] = self.calls_by_generation.get(generation, {}).get("evaluate", 0)
        metrics["calls_simulate_generation"] = self.calls_by_generation.get(generation, {}).get("simulate", 0)
        self.generation_records.append(metrics)
        return metrics


def _run_single_scenario(case: Dict[str, Any], seed: int) -> Dict[str, Any]:
    board = Board(case["size"], case["initial_state"])
    solver = GeneticAlgorithmSolver(initial_board=board, random_seed=seed, **case["params"])
    probe = EvaluationProbe()
    probe.install()

    generation_counter = 0
    previous_best = None
    stagnation_count = 0
    original_eval = solver._evaluate_population

    def wrapped_eval(population: Sequence[Individual], start_time: float | None = None) -> List[tuple[Individual, float]]:
        nonlocal generation_counter, previous_best, stagnation_count
        probe.current_generation = generation_counter
        result = original_eval(population, start_time=start_time)
        generation_metrics = probe.observe_generation(population, generation_counter)
        if previous_best is None:
            previous_best = generation_metrics["best_fitness"]
        else:
            if generation_metrics["best_fitness"] > previous_best:
                previous_best = generation_metrics["best_fitness"]
                stagnation_count = 0
            else:
                stagnation_count += 1
        generation_metrics["stagnation_count"] = stagnation_count
        generation_metrics["improved_since_previous"] = generation_metrics["best_fitness"] > previous_best if previous_best is not None and generation_counter > 0 else True
        generation_counter += 1
        return result

    solver._evaluate_population = wrapped_eval
    start_time = time.perf_counter()
    try:
        result = solver.solve()
    finally:
        probe.uninstall()
    elapsed = time.perf_counter() - start_time

    run_row = {
        "scenario_id": case["id"],
        "seed": seed,
        "size": case["size"],
        "initial_state": case["initial_state"],
        "params": json.dumps(case["params"], separators=(",", ":")),
        "solved": bool(result.get("solved", False)),
        "stop_reason": result.get("stop_reason", "unknown"),
        "total_time_seconds": round(elapsed, 6),
        "generations_run": int(result.get("generations_run", 0)),
        "best_sequence": result.get("best_sequence", []),
        "best_sequence_length": len(result.get("best_sequence", [])),
        "manhattan_final": Board(case["size"], result.get("final_state", case["initial_state"])).manhattan_distance(),
        "best_fitness": max((entry.get("best_fitness", 0.0) for entry in result.get("history", [])), default=0.0),
        "time_limit_partial": result.get("stop_reason", "") == "time_limit",
        "seed_reproducible": False,
        "description": case["description"],
    }

    return {
        "run": run_row,
        "generations": probe.generation_records,
        "evaluation_cost": {"evaluate_calls": probe.evaluate_calls, "simulate_calls": probe.simulate_calls, "by_generation": probe.calls_by_generation},
    }


def _run_experiments() -> None:
    scenarios = _scenario_configs()
    all_runs: List[Dict[str, Any]] = []
    all_generations: List[Dict[str, Any]] = []
    all_costs: List[Dict[str, Any]] = []

    for case in scenarios:
        for seed in (7, 13, 29):
            run_data = _run_single_scenario(case, seed)
            run_row = run_data["run"]
            all_runs.append(run_row)
            for record in run_data["generations"]:
                all_generations.append(
                    {
                        "scenario_id": case["id"],
                        "size": case["size"],
                        "seed": seed,
                        "generation": record["generation"],
                        "best_fitness": record["best_fitness"],
                        "average_fitness": record["average_fitness"],
                        "min_manhattan_distance": record["best_manhattan_achieved"],
                        "best_chromosome_length": record["best_chromosome_length"],
                        "distinct_chromosomes": record["distinct_chromosomes"],
                        "distinct_final_states": record["distinct_final_states"],
                        "duplicate_ratio": record["duplicate_ratio"],
                        "best_manhattan_achieved": record["best_manhattan_achieved"],
                        "stagnation_count": record.get("stagnation_count", 0),
                        "improved_since_previous": record.get("improved_since_previous", True),
                        "calls_evaluate_generation": record["calls_evaluate_generation"],
                        "calls_simulate_generation": record["calls_simulate_generation"],
                    }
                )
            cost = run_data["evaluation_cost"]
            all_costs.append(
                {
                    "scenario_id": case["id"],
                    "seed": seed,
                    "size": case["size"],
                    "evaluate_calls": cost["evaluate_calls"],
                    "simulate_calls": cost["simulate_calls"],
                    "calls_by_generation": json.dumps(cost["by_generation"], separators=(",", ":")),
                }
            )

    _write_csv(
        RESULTS_DIR / "fitness_diagnostics.csv",
        _fitness_cases(),
        [
            "case_id",
            "initial_state",
            "chromosome",
            "final_state",
            "goal_reached",
            "initial_manhattan",
            "final_manhattan",
            "invalid_moves",
            "chromosome_length",
            "fitness",
            "ranking_by_fitness",
            "description",
        ],
    )

    _write_csv(
        RESULTS_DIR / "diversity_by_generation.csv",
        all_generations,
        [
            "scenario_id",
            "size",
            "seed",
            "generation",
            "best_fitness",
            "average_fitness",
            "min_manhattan_distance",
            "best_chromosome_length",
            "distinct_chromosomes",
            "distinct_final_states",
            "duplicate_ratio",
            "best_manhattan_achieved",
            "stagnation_count",
            "improved_since_previous",
            "calls_evaluate_generation",
            "calls_simulate_generation",
        ],
    )

    _write_csv(
        RESULTS_DIR / "convergence_runs.csv",
        all_runs,
        [
            "scenario_id",
            "seed",
            "size",
            "initial_state",
            "params",
            "solved",
            "stop_reason",
            "total_time_seconds",
            "generations_run",
            "best_sequence",
            "best_sequence_length",
            "manhattan_final",
            "best_fitness",
            "time_limit_partial",
            "seed_reproducible",
            "description",
        ],
    )

    _write_csv(
        RESULTS_DIR / "evaluation_cost.csv",
        all_costs,
        [
            "scenario_id",
            "seed",
            "size",
            "evaluate_calls",
            "simulate_calls",
            "calls_by_generation",
        ],
    )


def main() -> None:
    _run_experiments()


if __name__ == "__main__":
    main()

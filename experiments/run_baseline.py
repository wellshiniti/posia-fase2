from __future__ import annotations

import csv
import json
import random
import statistics
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


def _reset_monitored_calls() -> Dict[str, int]:
    return {"evaluate": 0, "simulate": 0}


def _instrument_individual_calls() -> tuple[Any, Any, Dict[str, int]]:
    counts = _reset_monitored_calls()
    original_evaluate = Individual.evaluate
    original_simulate = Individual.simulate

    def counted_evaluate(self: Individual) -> Dict[str, Any]:
        counts["evaluate"] += 1
        return original_evaluate(self)

    def counted_simulate(self: Individual) -> Dict[str, Any]:
        counts["simulate"] += 1
        return original_simulate(self)

    Individual.evaluate = counted_evaluate
    Individual.simulate = counted_simulate
    return original_evaluate, original_simulate, counts


def _restore_individual_calls(
    original_evaluate: Any,
    original_simulate: Any,
) -> None:
    Individual.evaluate = original_evaluate
    Individual.simulate = original_simulate


def _serialize_board_state(board: Board) -> List[int]:
    return list(board.state)


def _collect_result_metrics(result: Dict[str, Any], solver: GeneticAlgorithmSolver) -> Dict[str, Any]:
    history = result.get("history", [])
    best_target = solver.best_individual
    best_result = best_target.simulate() if best_target is not None else {"final_state": list(solver.initial_board.state), "manhattan_distance": solver.initial_board.manhattan_distance(), "solved": False}
    return {
        "solved": bool(result.get("solved", False)),
        "stop_reason": result.get("stop_reason", "unknown"),
        "time_total_seconds": 0.0,
        "generations_run": int(result.get("generations_run", 0)),
        "history_entries": len(history),
        "complete_generations": sum(1 for entry in history if not entry.get("partial", False)),
        "partial_generations": sum(1 for entry in history if entry.get("partial", False)),
        "best_fitness": max((entry.get("best_fitness", 0.0) for entry in history), default=0.0),
        "best_manhattan_distance": int(best_result.get("manhattan_distance", 0)),
        "best_chromosome_length": len(best_target.chromosome) if best_target is not None else 0,
        "evaluated_count_from_history": sum(int(entry.get("evaluated_count", 0)) for entry in history),
        "best_sequence": list(result.get("best_sequence", [])),
        "final_state": list(result.get("final_state", solver.initial_board.state)),
    }


def _write_csv(path: Path, rows: Sequence[Dict[str, Any]], fieldnames: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _build_scenarios() -> List[Dict[str, Any]]:
    scenarios: List[Dict[str, Any]] = [
        {
            "id": "3x3_goal",
            "size": 3,
            "state": [1, 2, 3, 4, 5, 6, 7, 8, 0],
            "notes": "tabuleiro resolvido",
        },
        {
            "id": "3x3_one_move",
            "size": 3,
            "state": [1, 2, 3, 4, 5, 6, 7, 0, 8],
            "notes": "um movimento do objetivo",
        },
        {
            "id": "3x3_medium",
            "size": 3,
            "state": [1, 2, 3, 4, 0, 6, 7, 5, 8],
            "notes": "estado médio, sem solução explícita",
        },
        {
            "id": "3x3_hard_seed_21",
            "size": 3,
            "state": [8, 6, 7, 2, 5, 4, 3, 0, 1],
            "notes": "estado mais difícil, configurado manualmente",
        },
    ]

    for idx in range(3):
        random.seed(100 + idx)
        board = Board.random_solvable(size=4, shuffle_moves=8 + idx * 4)
        scenarios.append(
            {
                "id": f"4x4_seed_{100 + idx}",
                "size": 4,
                "state": list(board.state),
                "notes": f"4x4 gerado com seed {100 + idx}",
            }
        )

    return scenarios


def _run_solver_case(case: Dict[str, Any], params: Dict[str, Any], seed: int) -> Dict[str, Any]:
    board = Board(case["size"], case["state"])
    solver = GeneticAlgorithmSolver(initial_board=board, random_seed=seed, **params)

    original_evaluate, original_simulate, counts = _instrument_individual_calls()
    start = time.perf_counter()
    try:
        result = solver.solve()
    finally:
        _restore_individual_calls(original_evaluate, original_simulate)
    elapsed = time.perf_counter() - start

    summary = _collect_result_metrics(result, solver)
    summary.update(
        {
            "experiment_id": case["id"],
            "seed": seed,
            "size": case["size"],
            "initial_state": list(case["state"]),
            "params": json.dumps(params, separators=(",", ":")),
            "time_total_seconds": round(elapsed, 6),
            "evaluate_calls_observed": counts["evaluate"],
            "simulate_calls_observed": counts["simulate"],
            "observed_individuals_evaluated": counts["evaluate"],
            "history_entries": len(result.get("history", [])),
            "final_best_sequence": list(result.get("best_sequence", [])),
            "stop_reason": result.get("stop_reason", "unknown"),
            "notes": case.get("notes", ""),
        }
    )
    return summary


def _run_reproducibility_check() -> List[Dict[str, Any]]:
    case = {
        "id": "3x3_reproducibility",
        "size": 3,
        "state": [1, 2, 3, 4, 5, 6, 7, 0, 8],
        "notes": "verifica a reprodutibilidade com a mesma semente e estado inicial",
    }
    params = {
        "population_size": 10,
        "initial_chromosome_length": 4,
        "max_generations": 8,
        "crossover_rate": 0.7,
        "mutation_rate": 0.2,
        "tournament_size": 2,
        "elites_count": 1,
        "max_chromosome_length": 20,
        "time_limit": 5.0,
    }
    run_a = _run_solver_case(case, params, seed=42)
    run_b = _run_solver_case(case, params, seed=42)
    return [
        {**run_a, "reproducibility_label": "first_run"},
        {**run_b, "reproducibility_label": "second_run"},
    ]


def _fitness_cases() -> List[Dict[str, Any]]:
    samples: List[Dict[str, Any]] = []

    cases = [
        {
            "id": "solved_sequence",
            "initial_state": [1, 2, 3, 4, 5, 6, 7, 8, 0],
            "chromosome": ["R"],
            "note": "sequência que resolve o tabuleiro em um único passo",
        },
        {
            "id": "distance_reduction",
            "initial_state": [1, 2, 3, 4, 5, 6, 0, 8, 7],
            "chromosome": ["R"],
            "note": "reduz a distância Manhattan sem resolver",
        },
        {
            "id": "no_progress",
            "initial_state": [1, 2, 3, 4, 5, 6, 7, 0, 8],
            "chromosome": ["U", "U"],
            "note": "movimentos inválidos que não produzem progresso útil",
        },
        {
            "id": "invalid_move_penalty",
            "initial_state": [1, 2, 3, 4, 5, 6, 7, 0, 8],
            "chromosome": ["U", "D"],
            "note": "movimentos inválidos e sequência curta",
        },
        {
            "id": "different_lengths",
            "initial_state": [1, 2, 3, 4, 0, 6, 7, 5, 8],
            "chromosome": ["R", "R"],
            "note": "duas sequências de comprimentos distintos terminam em estados diferentes",
        },
    ]

    for case in cases:
        board = Board(3, case["initial_state"])
        individual = Individual(chromosome=case["chromosome"], initial_board=board)
        result = individual.simulate()
        fitness = Fitness().evaluate(individual)
        samples.append(
            {
                "id": case["id"],
                "initial_state": case["initial_state"],
                "chromosome": list(case["chromosome"]),
                "final_state": list(result["final_state"]),
                "manhattan_distance": int(result["manhattan_distance"]),
                "invalid_moves": int(result["invalid_moves"]),
                "chromosome_length": len(case["chromosome"]),
                "fitness": float(fitness),
                "note": case["note"],
            }
        )

    return samples


def _write_results() -> None:
    scenarios = _build_scenarios()
    params = {
        "population_size": 10,
        "initial_chromosome_length": 6,
        "max_generations": 10,
        "crossover_rate": 0.7,
        "mutation_rate": 0.2,
        "tournament_size": 2,
        "elites_count": 1,
        "max_chromosome_length": 20,
        "time_limit": 3.0,
    }

    baseline_rows = []
    for case in scenarios:
        for seed in (7, 13, 29):
            row = _run_solver_case(case, params, seed)
            baseline_rows.append(row)

    _write_csv(
        RESULTS_DIR / "baseline_runs.csv",
        baseline_rows,
        [
            "experiment_id",
            "seed",
            "size",
            "initial_state",
            "params",
            "solved",
            "stop_reason",
            "time_total_seconds",
            "generations_run",
            "history_entries",
            "complete_generations",
            "partial_generations",
            "best_fitness",
            "best_manhattan_distance",
            "best_chromosome_length",
            "observed_individuals_evaluated",
            "evaluate_calls_observed",
            "simulate_calls_observed",
            "evaluated_count_from_history",
            "final_state",
            "final_best_sequence",
            "best_sequence",
            "notes",
        ],
    )

    reproducibility_rows = _run_reproducibility_check()
    _write_csv(
        RESULTS_DIR / "reproducibility_check.csv",
        reproducibility_rows,
        [
            "experiment_id",
            "seed",
            "size",
            "initial_state",
            "params",
            "solved",
            "stop_reason",
            "time_total_seconds",
            "generations_run",
            "history_entries",
            "complete_generations",
            "partial_generations",
            "best_fitness",
            "best_manhattan_distance",
            "best_chromosome_length",
            "evaluated_count_from_history",
            "observed_individuals_evaluated",
            "evaluate_calls_observed",
            "simulate_calls_observed",
            "final_state",
            "final_best_sequence",
            "best_sequence",
            "notes",
            "reproducibility_label",
        ],
    )

    fitness_rows = _fitness_cases()
    _write_csv(
        RESULTS_DIR / "fitness_cases.csv",
        fitness_rows,
        [
            "id",
            "initial_state",
            "chromosome",
            "final_state",
            "manhattan_distance",
            "invalid_moves",
            "chromosome_length",
            "fitness",
            "note",
        ],
    )


def _summarize_results() -> None:
    baseline_path = RESULTS_DIR / "baseline_runs.csv"
    if not baseline_path.exists():
        return

    with baseline_path.open("r", newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    if not rows:
        return

    print("=== Baseline experimental summary ===")
    print(f"linhas: {len(rows)}")
    print(f"solvidos: {sum(1 for row in rows if row['solved'] == 'True')}")
    print(f"taxa de sucesso: {sum(1 for row in rows if row['solved'] == 'True') / len(rows):.2%}")
    print(f"tempo médio: {statistics.mean(float(row['time_total_seconds']) for row in rows):.6f}s")
    print(f"mediana de gerações: {statistics.median(float(row['generations_run']) for row in rows)}")

    for row in rows[:3]:
        print(row)


def main() -> None:
    _write_results()
    _summarize_results()


if __name__ == "__main__":
    main()

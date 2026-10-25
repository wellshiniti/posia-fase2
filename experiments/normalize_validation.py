from __future__ import annotations

import ast
import csv
import json
import time
from pathlib import Path

from genetic_algorithm.individual import Individual
from genetic_algorithm.solver import GeneticAlgorithmSolver
from puzzle.board import Board

ROOT = Path(__file__).resolve().parent.parent
BASE_CSV = ROOT / "experiments" / "results" / "baseline_runs.csv"
OUT_CSV = ROOT / "experiments" / "results" / "normalize_validation_runs.csv"

with BASE_CSV.open("r", newline="", encoding="utf-8") as handle:
    baseline_rows = list(csv.DictReader(handle))

current_rows: list[dict[str, object]] = []
seen: set[tuple[str, str]] = set()
for row in baseline_rows:
    key = (row["experiment_id"], row["seed"])
    if key in seen:
        continue
    seen.add(key)

    initial_state = ast.literal_eval(row["initial_state"])
    size = int(row["size"])
    params = json.loads(row["params"])
    solver_params = {
        "population_size": int(params["population_size"]),
        "initial_chromosome_length": int(params["initial_chromosome_length"]),
        "max_generations": int(params["max_generations"]),
        "crossover_rate": float(params["crossover_rate"]),
        "mutation_rate": float(params["mutation_rate"]),
        "tournament_size": int(params["tournament_size"]),
        "elites_count": int(params["elites_count"]),
        "max_chromosome_length": int(params["max_chromosome_length"]),
        "time_limit": float(params["time_limit"]),
        "random_seed": int(row["seed"]),
        "mutation_adaptation_enabled": False,
    }

    board = Board(size, initial_state)
    start = time.perf_counter()
    solver = GeneticAlgorithmSolver(initial_board=board, **solver_params)
    result = solver.solve()
    elapsed = time.perf_counter() - start

    best_sequence = list(result.get("best_sequence", []))
    best_individual = Individual(chromosome=best_sequence, initial_board=board)
    simulation = best_individual.simulate()
    best_fitness = max(
        (entry.get("best_fitness", 0.0) for entry in result.get("history", [])),
        default=0.0,
    )

    current_rows.append(
        {
            "scenario": row["experiment_id"],
            "seed": int(row["seed"]),
            "size": size,
            "initial_state": json.dumps(initial_state),
            "solved": bool(result.get("solved", False)),
            "stop_reason": result.get("stop_reason", "unknown"),
            "generations_run": int(result.get("generations_run", 0)),
            "time_total_seconds": round(elapsed, 6),
            "best_fitness": round(float(best_fitness), 12),
            "best_manhattan_distance": int(simulation.get("manhattan_distance", 0)),
            "best_chromosome_length": len(best_sequence),
            "invalid_moves": int(simulation.get("invalid_moves", 0)),
            "best_sequence": json.dumps(best_sequence),
            "notes": row.get("notes", ""),
            "version": "normalize_validation_mutation_disabled",
            "params": json.dumps(params, separators=(",", ":")),
        }
    )

with OUT_CSV.open("w", newline="", encoding="utf-8") as handle:
    fieldnames = [
        "scenario",
        "seed",
        "size",
        "initial_state",
        "solved",
        "stop_reason",
        "generations_run",
        "time_total_seconds",
        "best_fitness",
        "best_manhattan_distance",
        "best_chromosome_length",
        "invalid_moves",
        "best_sequence",
        "notes",
        "version",
        "params",
    ]
    writer = csv.DictWriter(handle, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(current_rows)

baseline_success = sum(1 for row in baseline_rows if row["solved"] == "True")
current_success = sum(1 for row in current_rows if row["solved"] is True)
print(f"Baseline success: {baseline_success}/{len(baseline_rows)} = {baseline_success / len(baseline_rows):.2%}")
print(f"Current success: {current_success}/{len(current_rows)} = {current_success / len(current_rows):.2%}")
print(f"CSV generated: {OUT_CSV}")

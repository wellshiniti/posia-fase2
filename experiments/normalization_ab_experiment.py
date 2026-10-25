from __future__ import annotations

import ast
import csv
import importlib
import json
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
BASE_CSV = ROOT / "experiments" / "results" / "baseline_runs.csv"
OUT_CSV = ROOT / "experiments" / "results" / "normalization_ab_experiment.csv"
TEMP_ROOT = ROOT / "experiments" / "_ab_variant"


def build_variant(disable_normalization: bool) -> Path:
    """Cria uma cópia experimental isolada, sem alterar os arquivos do projeto principal."""
    if TEMP_ROOT.exists():
        shutil.rmtree(TEMP_ROOT)
    TEMP_ROOT.mkdir(parents=True, exist_ok=True)

    for package_name in ("genetic_algorithm", "puzzle"):
        src = ROOT / package_name
        dst = TEMP_ROOT / package_name
        shutil.copytree(src, dst)

    if disable_normalization:
        ops_path = TEMP_ROOT / "genetic_algorithm" / "operators.py"
        text = ops_path.read_text(encoding="utf-8")
        old = "    mutated.chromosome = normalize_chromosome(mutated.chromosome, max_length=max_length)\n"
        if old in text:
            text = text.replace(old, "    # normalization intentionally disabled in this experimental variant\n")
            ops_path.write_text(text, encoding="utf-8")

    return TEMP_ROOT


def run_one_case(version: str, case_id: str, seed: int, size: int, initial_state: list[int], params: dict[str, Any]) -> dict[str, Any]:
    package_root = TEMP_ROOT if version == "no_normalization" else ROOT
    sys.path.insert(0, str(package_root))
    try:
        importlib.invalidate_caches()
        from genetic_algorithm.individual import Individual
        from genetic_algorithm.solver import GeneticAlgorithmSolver
        from puzzle.board import Board

        board = Board(size, initial_state)
        solver = GeneticAlgorithmSolver(initial_board=board, random_seed=seed, **params)
        start = time.perf_counter()
        result = solver.solve()
        elapsed = time.perf_counter() - start

        best_sequence = list(result.get("best_sequence", []))
        best_individual = Individual(chromosome=best_sequence, initial_board=board) if best_sequence else Individual(chromosome=[], initial_board=board)
        sim = best_individual.simulate()
        best_fitness = max((entry.get("best_fitness", 0.0) for entry in result.get("history", [])), default=0.0)

        return {
            "version": version,
            "scenario": case_id,
            "seed": int(seed),
            "size": int(size),
            "initial_state": json.dumps(initial_state),
            "solved": bool(result.get("solved", False)),
            "stop_reason": result.get("stop_reason", "unknown"),
            "generations_run": int(result.get("generations_run", 0)),
            "time_total_seconds": round(elapsed, 6),
            "best_fitness": round(float(best_fitness), 12),
            "best_manhattan_distance": int(sim.get("manhattan_distance", 0)),
            "best_chromosome_length": len(best_sequence),
            "invalid_moves": int(sim.get("invalid_moves", 0)),
            "notes": "",
            "params": json.dumps(params, separators=(",", ":")),
        }
    finally:
        # leave the root path first for later imports; remove the inserted temp entry if present
        try:
            sys.path.remove(str(package_root))
        except ValueError:
            pass


def smoke_test() -> None:
    baseline_rows = list(csv.DictReader(BASE_CSV.open("r", newline="", encoding="utf-8")))
    sample = baseline_rows[0]
    params = json.loads(sample["params"])
    case = {
        "scenario": sample["experiment_id"],
        "seed": int(sample["seed"]),
        "size": int(sample["size"]),
        "initial_state": ast.literal_eval(sample["initial_state"]),
    }
    result_a = run_one_case("normalized", case["scenario"], case["seed"], case["size"], case["initial_state"], params)
    result_b = run_one_case("no_normalization", case["scenario"], case["seed"], case["size"], case["initial_state"], params)
    print("SMOKE_TEST", result_a["version"], result_a["solved"], result_b["version"], result_b["solved"])


def main() -> None:
    if not BASE_CSV.exists():
        raise FileNotFoundError(f"Baseline file not found: {BASE_CSV}")

    baseline_rows = list(csv.DictReader(BASE_CSV.open("r", newline="", encoding="utf-8")))
    if not baseline_rows:
        raise ValueError("Baseline CSV is empty")

    smoke_test()

    current_dir = build_variant(disable_normalization=False)
    no_norm_dir = build_variant(disable_normalization=True)

    rows: list[dict[str, Any]] = []
    for row in baseline_rows:
        params = json.loads(row["params"])
        case_id = row["experiment_id"]
        seed = int(row["seed"])
        size = int(row["size"])
        initial_state = ast.literal_eval(row["initial_state"])

        for version, variant_root in (("normalized", current_dir), ("no_normalization", no_norm_dir)):
            sys.path.insert(0, str(variant_root))
            try:
                importlib.invalidate_caches()
                from genetic_algorithm.individual import Individual
                from genetic_algorithm.solver import GeneticAlgorithmSolver
                from puzzle.board import Board

                board = Board(size, initial_state)
                solver = GeneticAlgorithmSolver(initial_board=board, random_seed=seed, **params)
                start = time.perf_counter()
                result = solver.solve()
                elapsed = time.perf_counter() - start

                best_sequence = list(result.get("best_sequence", []))
                best_individual = Individual(chromosome=best_sequence, initial_board=board) if best_sequence else Individual(chromosome=[], initial_board=board)
                sim = best_individual.simulate()
                best_fitness = max((entry.get("best_fitness", 0.0) for entry in result.get("history", [])), default=0.0)

                rows.append({
                    "version": version,
                    "scenario": case_id,
                    "seed": seed,
                    "size": size,
                    "initial_state": json.dumps(initial_state),
                    "solved": bool(result.get("solved", False)),
                    "stop_reason": result.get("stop_reason", "unknown"),
                    "generations_run": int(result.get("generations_run", 0)),
                    "time_total_seconds": round(elapsed, 6),
                    "best_fitness": round(float(best_fitness), 12),
                    "best_manhattan_distance": int(sim.get("manhattan_distance", 0)),
                    "best_chromosome_length": len(best_sequence),
                    "invalid_moves": int(sim.get("invalid_moves", 0)),
                    "params": json.dumps(params, separators=(",", ":")),
                    "notes": row.get("notes", ""),
                })
            finally:
                try:
                    sys.path.remove(str(variant_root))
                except ValueError:
                    pass

    fieldnames = [
        "version",
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
        "params",
        "notes",
    ]
    with OUT_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    summary = {}
    for version in ("normalized", "no_normalization"):
        subset = [row for row in rows if row["version"] == version]
        success = sum(1 for row in subset if row["solved"])
        summary[version] = {
            "runs": len(subset),
            "success": success,
            "rate": success / len(subset) if subset else 0.0,
            "avg_time": sum(float(row["time_total_seconds"]) for row in subset) / len(subset) if subset else 0.0,
            "avg_generations": sum(int(row["generations_run"]) for row in subset) / len(subset) if subset else 0.0,
        }

    print("RESULT_SUMMARY")
    for version in ("normalized", "no_normalization"):
        print(version, summary[version])
    print(f"CSV written to {OUT_CSV}")


if __name__ == "__main__":
    main()

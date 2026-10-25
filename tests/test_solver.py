import json
import math
import subprocess
import sys

import pytest

from genetic_algorithm.individual import Individual
from genetic_algorithm.solver import GeneticAlgorithmSolver
from puzzle.board import Board


def test_solver_resolved_board() -> None:
    board = Board(3)
    solver = GeneticAlgorithmSolver(
        initial_board=board,
        population_size=10,
        initial_chromosome_length=2,
        max_generations=5,
        crossover_rate=0.5,
        mutation_rate=0.1,
        tournament_size=2,
        elites_count=1,
        max_chromosome_length=10,
        random_seed=1,
    )

    result = solver.solve()

    assert result["solved"] is True
    assert result["solution"] == []
    assert result["final_state"] == board.goal_state()
    assert result["stop_reason"] == "solved"


def test_solver_respects_generation_limit() -> None:
    board = Board(3, [1, 2, 3, 4, 5, 6, 7, 0, 8])
    solver = GeneticAlgorithmSolver(
        initial_board=board,
        population_size=8,
        initial_chromosome_length=3,
        max_generations=3,
        crossover_rate=0.7,
        mutation_rate=0.2,
        tournament_size=2,
        elites_count=1,
        max_chromosome_length=10,
        random_seed=5,
    )

    result = solver.solve()

    assert result["generations_run"] <= 3
    assert result["stop_reason"] in {"max_generations", "solved"}
    assert isinstance(result["history"], list)
    assert result["history"]


def test_solver_returns_structured_result_when_not_solved() -> None:
    board = Board(3, [1, 2, 3, 4, 5, 6, 7, 0, 8])
    solver = GeneticAlgorithmSolver(
        initial_board=board,
        population_size=4,
        initial_chromosome_length=0,
        max_generations=2,
        crossover_rate=0.0,
        mutation_rate=0.0,
        tournament_size=2,
        elites_count=1,
        max_chromosome_length=0,
        random_seed=9,
    )

    result = solver.solve()

    assert result["solved"] is False
    assert isinstance(result["best_sequence"], list)
    assert result["final_state"] == [1, 2, 3, 4, 5, 6, 7, 0, 8]
    assert result["stop_reason"] in {"max_generations", "solved", "time_limit"}


def test_solver_preserves_original_board() -> None:
    board = Board(3, [1, 2, 3, 4, 0, 6, 7, 5, 8])
    original = board.state[:]
    solver = GeneticAlgorithmSolver(
        initial_board=board,
        population_size=4,
        initial_chromosome_length=2,
        max_generations=2,
        crossover_rate=0.5,
        mutation_rate=0.1,
        tournament_size=2,
        elites_count=1,
        max_chromosome_length=5,
        random_seed=3,
    )

    solver.solve()

    assert board.state == original


def test_solver_parameter_validation() -> None:
    board = Board(3)

    with pytest.raises(ValueError):
        GeneticAlgorithmSolver(board, population_size=0)

    with pytest.raises(ValueError):
        GeneticAlgorithmSolver(board, crossover_rate=1.5)

    with pytest.raises(ValueError):
        GeneticAlgorithmSolver(board, mutation_rate=float("nan"))

    with pytest.raises(ValueError):
        GeneticAlgorithmSolver(board, time_limit=0)

    with pytest.raises(ValueError):
        GeneticAlgorithmSolver(board, tournament_size=0)


def test_solver_reproducibility_same_seed() -> None:
    board = Board(3, [1, 2, 3, 4, 5, 6, 7, 0, 8])
    solver_a = GeneticAlgorithmSolver(
        initial_board=board,
        population_size=10,
        initial_chromosome_length=4,
        max_generations=4,
        crossover_rate=0.8,
        mutation_rate=0.3,
        tournament_size=2,
        elites_count=1,
        max_chromosome_length=8,
        random_seed=42,
    )
    solver_b = GeneticAlgorithmSolver(
        initial_board=board,
        population_size=10,
        initial_chromosome_length=4,
        max_generations=4,
        crossover_rate=0.8,
        mutation_rate=0.3,
        tournament_size=2,
        elites_count=1,
        max_chromosome_length=8,
        random_seed=42,
    )

    result_a = solver_a.solve()
    result_b = solver_b.solve()

    assert result_a == result_b


def test_solver_history_metrics() -> None:
    board = Board(3)
    solver = GeneticAlgorithmSolver(
        initial_board=board,
        population_size=6,
        initial_chromosome_length=2,
        max_generations=2,
        crossover_rate=0.5,
        mutation_rate=0.1,
        tournament_size=2,
        elites_count=1,
        max_chromosome_length=5,
        random_seed=7,
    )

    result = solver.solve()

    assert result["history"]
    entry = result["history"][0]
    assert "best_fitness" in entry
    assert "average_fitness" in entry
    assert "min_manhattan_distance" in entry
    assert "best_chromosome_length" in entry
    assert "distinct_individuals" in entry


def test_solver_reproducible_after_dedup_fill() -> None:
    board = Board(3, [1, 2, 3, 4, 5, 6, 7, 0, 8])
    population = [
        Individual(chromosome=["U"], initial_board=board),
        Individual(chromosome=["U"], initial_board=board),
        Individual(chromosome=["D"], initial_board=board),
        Individual(chromosome=["D"], initial_board=board),
    ]
    solver_a = GeneticAlgorithmSolver(
        initial_board=board,
        population_size=4,
        initial_chromosome_length=1,
        max_generations=2,
        crossover_rate=0.9,
        mutation_rate=0.5,
        tournament_size=2,
        elites_count=1,
        max_chromosome_length=3,
        random_seed=123,
    )
    solver_b = GeneticAlgorithmSolver(
        initial_board=board,
        population_size=4,
        initial_chromosome_length=1,
        max_generations=2,
        crossover_rate=0.9,
        mutation_rate=0.5,
        tournament_size=2,
        elites_count=1,
        max_chromosome_length=3,
        random_seed=123,
    )

    evolved_a = solver_a._evolve_population(population, start_time=0.0)
    evolved_b = solver_b._evolve_population(population, start_time=0.0)

    assert [tuple(individual.chromosome) for individual in evolved_a] == [
        tuple(individual.chromosome) for individual in evolved_b
    ]
    assert len(evolved_a) == 4
    assert all(isinstance(individual, Individual) for individual in evolved_a)


def test_solver_reproducibility_across_process_same_seed() -> None:
    script = """
import json
from puzzle.board import Board
from genetic_algorithm.solver import GeneticAlgorithmSolver

board = Board(3, [1, 2, 3, 4, 5, 6, 7, 0, 8])
solver = GeneticAlgorithmSolver(
    initial_board=board,
    population_size=8,
    initial_chromosome_length=4,
    max_generations=4,
    crossover_rate=0.8,
    mutation_rate=0.3,
    tournament_size=2,
    elites_count=1,
    max_chromosome_length=8,
    random_seed=42,
)
print(json.dumps(solver.solve(), sort_keys=True))
"""
    first = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        check=True,
        cwd=str(__import__("pathlib").Path(__file__).resolve().parent.parent),
    )
    second = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        check=True,
        cwd=str(__import__("pathlib").Path(__file__).resolve().parent.parent),
    )

    assert json.loads(first.stdout) == json.loads(second.stdout)


def test_solver_time_limit_stops_without_real_wait(monkeypatch) -> None:
    board = Board(3, [1, 2, 3, 4, 5, 6, 7, 0, 8])
    solver = GeneticAlgorithmSolver(
        initial_board=board,
        population_size=6,
        initial_chromosome_length=0,
        max_generations=50,
        crossover_rate=0.0,
        mutation_rate=0.0,
        tournament_size=2,
        elites_count=1,
        max_chromosome_length=0,
        time_limit=0.01,
        random_seed=7,
    )

    clock = iter([0.0, 0.02, 0.02, 0.02, 0.02, 0.02])

    def fake_perf_counter() -> float:
        return next(clock)

    monkeypatch.setattr("genetic_algorithm.solver.time.perf_counter", fake_perf_counter)

    result = solver.solve()

    assert result["stop_reason"] == "time_limit"
    assert result["best_sequence"] == []


def test_solver_time_limit_preserves_best_individual_during_evaluation(monkeypatch) -> None:
    board = Board(3, [1, 2, 3, 4, 5, 6, 7, 0, 8])
    solver = GeneticAlgorithmSolver(
        initial_board=board,
        population_size=4,
        initial_chromosome_length=1,
        max_generations=10,
        crossover_rate=0.5,
        mutation_rate=0.0,
        tournament_size=2,
        elites_count=1,
        max_chromosome_length=2,
        time_limit=0.01,
        random_seed=1,
    )
    best = Individual(chromosome=["R"], initial_board=board)
    solver.best_individual = best

    clock = iter([0.0, 0.02])

    def fake_perf_counter() -> float:
        return next(clock)

    monkeypatch.setattr("genetic_algorithm.solver.time.perf_counter", fake_perf_counter)

    population = [best, Individual(chromosome=["L"], initial_board=board)]
    evaluations = solver._evaluate_population(population, start_time=0.0)

    assert len(evaluations) == 1
    assert solver.best_individual == best
    assert evaluations[0][0] == best


def test_solver_time_limit_preserves_best_individual_during_evolution(monkeypatch) -> None:
    board = Board(3, [1, 2, 3, 4, 5, 6, 7, 0, 8])
    solver = GeneticAlgorithmSolver(
        initial_board=board,
        population_size=4,
        initial_chromosome_length=1,
        max_generations=10,
        crossover_rate=0.7,
        mutation_rate=0.2,
        tournament_size=2,
        elites_count=1,
        max_chromosome_length=3,
        time_limit=0.01,
        random_seed=3,
    )
    best = Individual(chromosome=["R"], initial_board=board)
    solver.best_individual = best
    population = [best, Individual(chromosome=["L"], initial_board=board)]

    clock = iter([0.0, 0.0, 0.02, 0.02, 0.02])

    def fake_perf_counter() -> float:
        return next(clock)

    monkeypatch.setattr("genetic_algorithm.solver.time.perf_counter", fake_perf_counter)

    evolved = solver._evolve_population(population, start_time=0.0)

    assert solver.best_individual == best
    assert len(evolved) <= solver.population_size


def test_solver_recognizes_deterministic_solution_sequence() -> None:
    board = Board(3, [1, 2, 3, 4, 5, 6, 7, 0, 8])
    individual = Individual(chromosome=["R"], initial_board=board)

    simulation = individual.simulate()

    assert simulation["solved"] is True
    assert simulation["final_state"] == board.goal_state()
    assert simulation["invalid_moves"] == 0


def test_solver_recognizes_solution_found() -> None:
    board = Board(3)
    solver = GeneticAlgorithmSolver(
        initial_board=board,
        population_size=5,
        initial_chromosome_length=0,
        max_generations=1,
        crossover_rate=0.0,
        mutation_rate=0.0,
        tournament_size=2,
        elites_count=1,
        max_chromosome_length=0,
        random_seed=11,
    )

    result = solver.solve()

    assert result["solved"] is True
    assert result["solution"] == []
    assert result["stop_reason"] == "solved"

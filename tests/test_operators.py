import random

import pytest

from genetic_algorithm.fitness import Fitness
from genetic_algorithm.individual import Individual
from genetic_algorithm.operators import (
    crossover,
    elitism,
    mutate,
    tournament_selection,
)
from puzzle.board import Board


def make_population() -> list[Individual]:
    board = Board(3)
    return [
        Individual([], board),
        Individual(["R"], board),
        Individual(["R", "U"], board),
        Individual(["L", "D"], board),
    ]


def test_tournament_selection_with_valid_population() -> None:
    population = make_population()
    evaluator = Fitness()
    rng = random.Random(7)

    winner = tournament_selection(population, evaluator, tournament_size=3, rng=rng)

    assert isinstance(winner, Individual)
    assert winner.chromosome in [
        individual.chromosome for individual in population
    ]
    assert winner is not population[0]


def test_tournament_selection_rejects_empty_population() -> None:
    with pytest.raises(ValueError):
        tournament_selection([], Fitness())


def test_tournament_selection_rejects_invalid_tournament_size() -> None:
    population = make_population()
    with pytest.raises(ValueError):
        tournament_selection(population, Fitness(), tournament_size=0)

    with pytest.raises(ValueError):
        tournament_selection(population, Fitness(), tournament_size=len(population) + 1)


def test_crossover_same_length_keeps_parents_untouched() -> None:
    board = Board(3)
    parent_a = Individual(["U", "L", "R"], board)
    parent_b = Individual(["D", "R", "U"], board)
    original_a = parent_a.chromosome[:]
    original_b = parent_b.chromosome[:]

    child_a, child_b = crossover(parent_a, parent_b, rng=random.Random(10))

    assert parent_a.chromosome == original_a
    assert parent_b.chromosome == original_b
    assert all(move in {"U", "D", "L", "R"} for move in child_a.chromosome)
    assert all(move in {"U", "D", "L", "R"} for move in child_b.chromosome)
    assert child_a.initial_board.state == board.state
    assert child_b.initial_board.state == board.state


def test_crossover_different_lengths() -> None:
    board = Board(3)
    parent_a = Individual(["U", "L"], board)
    parent_b = Individual(["D", "R", "U", "L"], board)

    child_a, child_b = crossover(parent_a, parent_b, rng=random.Random(3))

    assert len(child_a.chromosome) >= 0
    assert len(child_b.chromosome) >= 0
    assert all(move in {"U", "D", "L", "R"} for move in child_a.chromosome)
    assert all(move in {"U", "D", "L", "R"} for move in child_b.chromosome)
    assert parent_a.chromosome == ["U", "L"]
    assert parent_b.chromosome == ["D", "R", "U", "L"]


def test_crossover_handles_empty_or_short_chromosomes() -> None:
    board = Board(3)
    empty_parent = Individual([], board)
    short_parent = Individual(["U"], board)

    child_a, child_b = crossover(empty_parent, short_parent, rng=random.Random(0))

    assert isinstance(child_a, Individual)
    assert isinstance(child_b, Individual)
    assert all(move in {"U", "D", "L", "R"} for move in child_a.chromosome)
    assert all(move in {"U", "D", "L", "R"} for move in child_b.chromosome)


def test_mutation_substitution_keeps_original_unchanged() -> None:
    board = Board(3)
    original = Individual(["U", "L", "R"], board)
    mutated = mutate(original, mutation_rate=1.0, rng=random.Random(0), mutation_type="substitution")

    assert original.chromosome == ["U", "L", "R"]
    assert mutated.chromosome != original.chromosome
    assert all(move in {"U", "D", "L", "R"} for move in mutated.chromosome)


def test_mutation_insertion_and_removal() -> None:
    board = Board(3)
    original = Individual(["U", "L"], board)

    inserted = mutate(original, mutation_rate=1.0, rng=random.Random(1), mutation_type="insertion")
    removed = mutate(original, mutation_rate=1.0, rng=random.Random(2), mutation_type="removal")

    assert len(inserted.chromosome) == len(original.chromosome) + 1
    assert len(removed.chromosome) == len(original.chromosome) - 1
    assert original.chromosome == ["U", "L"]
    assert all(move in {"U", "D", "L", "R"} for move in inserted.chromosome)
    assert all(move in {"U", "D", "L", "R"} for move in removed.chromosome)


def test_mutation_validates_probability_and_max_length() -> None:
    board = Board(3)
    individual = Individual(["U"], board)

    with pytest.raises(ValueError):
        mutate(individual, mutation_rate=-0.1)

    with pytest.raises(ValueError):
        mutate(individual, mutation_rate=1.5)

    with pytest.raises(ValueError):
        mutate(individual, mutation_rate=float("nan"))

    with pytest.raises(ValueError):
        mutate(individual, mutation_rate=float("inf"))

    with pytest.raises(ValueError):
        mutate(individual, mutation_rate=0.0, mutation_type="invalid")

    with pytest.raises(ValueError):
        mutate(individual, mutation_rate=1.0, max_length=-1)


def test_mutation_handles_empty_and_max_length() -> None:
    board = Board(3)
    empty = Individual([], board)
    long = Individual(["U", "D", "L", "R"], board)

    mutated_empty = mutate(empty, mutation_rate=1.0, rng=random.Random(0), mutation_type="insertion")
    mutated_long = mutate(long, mutation_rate=1.0, max_length=2, rng=random.Random(0), mutation_type="insertion")

    assert mutated_empty.chromosome == ["U"] or len(mutated_empty.chromosome) == 1
    assert len(mutated_long.chromosome) <= 2


def test_elitism_selects_best_individuals() -> None:
    board = Board(3)
    best = Individual(["R"], board)
    middle = Individual(["L"], board)
    worst = Individual(["U", "U"], board)

    population = [middle, best, worst]
    selected = elitism(population, evaluator=Fitness(), keep_count=2)

    assert len(selected) == 2
    assert selected[0].chromosome == best.chromosome
    assert population[0].chromosome == middle.chromosome
    assert selected[0] is not best
    assert selected[1] is not middle


def test_elitism_preserves_independence() -> None:
    board = Board(3)
    first = Individual(["R"], board)
    second = Individual(["L"], board)

    selected = elitism([first, second], evaluator=Fitness(), keep_count=2)
    selected[0].chromosome[0] = "U"

    assert first.chromosome == ["R"]
    assert second.chromosome == ["L"]


def test_tournament_selection_reproducible_with_rng() -> None:
    board = Board(3)
    population = [
        Individual(["R"], board),
        Individual(["L"], board),
        Individual(["U"], board),
    ]

    first = tournament_selection(population, Fitness(), tournament_size=2, rng=random.Random(1))
    second = tournament_selection(population, Fitness(), tournament_size=2, rng=random.Random(1))

    assert first.chromosome == second.chromosome

import itertools

import pytest

from genetic_algorithm.fitness import Fitness, calculate_fitness
from genetic_algorithm.individual import Individual
from puzzle.board import Board


def _find_unsolved_case(board: Board, predicate):
    for length in range(1, 6):
        for sequence in itertools.product(("U", "D", "L", "R"), repeat=length):
            individual = Individual(list(sequence), board)
            if not individual.simulate()["solved"] and predicate(individual):
                return individual
    raise AssertionError("Nenhum caso válido foi encontrado para o critério solicitado.")


def _find_pair_with_same_distance(board: Board, comparator):
    evaluated: list[tuple[Individual, dict]] = []
    for length in range(1, 6):
        for sequence in itertools.product(("U", "D", "L", "R"), repeat=length):
            individual = Individual(list(sequence), board)
            result = individual.simulate()
            if not result["solved"]:
                evaluated.append((individual, result))

    for index, (individual_a, result_a) in enumerate(evaluated):
        for individual_b, result_b in evaluated[index + 1 :]:
            if comparator(result_a, result_b):
                return individual_a, individual_b
    raise AssertionError("Nenhum par válido foi encontrado para o critério solicitado.")


def _find_pair_same_distance_and_invalid(board: Board):
    evaluated: list[tuple[Individual, dict]] = []
    for length in range(1, 6):
        for sequence in itertools.product(("U", "D", "L", "R"), repeat=length):
            individual = Individual(list(sequence), board)
            result = individual.simulate()
            if not result["solved"]:
                evaluated.append((individual, result))

    for index, (individual_a, result_a) in enumerate(evaluated):
        for individual_b, result_b in evaluated[index + 1 :]:
            if (
                result_a["manhattan_distance"] == result_b["manhattan_distance"]
                and result_a["invalid_moves"] == result_b["invalid_moves"]
                and len(individual_a) != len(individual_b)
            ):
                return individual_a, individual_b
    raise AssertionError("Nenhum par válido foi encontrado para o critério de comprimento.")


def test_individual_empty_sequence() -> None:
    board = Board(3)
    individual = Individual([], board)

    assert individual.chromosome == []
    result = individual.simulate()
    assert result["final_state"] == board.goal_state()
    assert result["invalid_moves"] == 0
    assert result["solved"] is True


def test_individual_valid_sequence() -> None:
    board = Board(3, [1, 2, 3, 4, 5, 6, 0, 7, 8])
    individual = Individual(["R", "R"], board)

    assert individual.chromosome == ["R", "R"]
    assert board.state == [1, 2, 3, 4, 5, 6, 0, 7, 8]


def test_reject_invalid_moves_in_chromosome() -> None:
    board = Board(3)
    with pytest.raises(ValueError):
        Individual(["X"], board)

    individual = Individual(["u", "r"], board)
    assert individual.chromosome == ["U", "R"]


def test_simulate_sequence() -> None:
    board = Board(3, [1, 2, 3, 4, 5, 6, 0, 7, 8])
    individual = Individual(["R", "R"], board)

    result = individual.simulate()
    assert result["final_state"] == [1, 2, 3, 4, 5, 6, 7, 8, 0]
    assert result["invalid_moves"] == 0
    assert result["solved"] is True


def test_invalid_moves_are_counted_and_board_is_not_modified() -> None:
    board = Board(3, [1, 2, 3, 4, 5, 6, 0, 7, 8])
    initial_state = board.state[:]
    individual = Individual(["L", "R", "U"], board)

    result = individual.simulate()
    assert result["invalid_moves"] == 1
    assert result["final_state"] == [1, 2, 3, 4, 0, 6, 7, 5, 8]
    assert board.state == initial_state


def test_repeated_evaluation_is_deterministic() -> None:
    board = Board(3, [1, 2, 3, 4, 5, 6, 7, 0, 8])
    individual = Individual(["R", "R"], board)

    result_1 = individual.evaluate()
    result_2 = individual.evaluate()

    assert result_1 == result_2
    assert board.state == [1, 2, 3, 4, 5, 6, 7, 0, 8]


def test_manhattan_distance_after_sequence() -> None:
    board = Board(3, [1, 2, 3, 4, 5, 6, 7, 0, 8])
    individual = Individual(["R"], board)

    result = individual.simulate()
    assert result["manhattan_distance"] == 0


def test_fitness_is_higher_for_closer_state() -> None:
    board = Board(3, [1, 2, 3, 4, 5, 6, 7, 0, 8])

    closer = Individual(["R"], board)
    farther = Individual(["L"], board)

    fitness = Fitness()
    assert fitness.evaluate(closer) > fitness.evaluate(farther)


def test_invalid_moves_penalize_fitness() -> None:
    board = Board(3, [1, 2, 3, 4, 5, 6, 0, 7, 8])

    valid = Individual(["R"], board)
    invalid = Individual(["L", "R"], board)

    fitness = Fitness()
    assert fitness.evaluate(valid) > fitness.evaluate(invalid)


def test_different_chromosome_lengths_are_handled() -> None:
    board = Board(3)

    short = Individual([], board)
    long = Individual(["U", "L", "D"], board)

    fitness = Fitness(alpha=1.0, beta=0.1)
    assert fitness.evaluate(short) > fitness.evaluate(long)


def test_completed_solution_has_explicit_priority() -> None:
    board = Board(3, [1, 2, 3, 4, 5, 6, 7, 0, 8])

    solved = Individual(["R"], board)
    unsolved = Individual(["L"], board)

    fitness = Fitness()
    assert fitness.evaluate(solved) > fitness.evaluate(unsolved)
    assert fitness.evaluate(solved) > 1.0


def test_fitness_prefers_lower_distance_before_invalid_moves_and_length() -> None:
    board = Board(3, [1, 2, 3, 4, 5, 6, 7, 0, 8])

    closer = _find_unsolved_case(board, lambda individual: individual.simulate()["manhattan_distance"] == 1)
    farther = _find_unsolved_case(board, lambda individual: individual.simulate()["manhattan_distance"] == 2)

    fitness = Fitness()
    assert fitness.evaluate(closer) > fitness.evaluate(farther)


def test_fitness_considers_invalid_moves_when_distance_is_equal() -> None:
    board = Board(3, [1, 2, 3, 4, 5, 6, 7, 0, 8])

    lower_invalid, higher_invalid = _find_pair_with_same_distance(
        board,
        lambda result_a, result_b: (
            result_a["manhattan_distance"] == result_b["manhattan_distance"]
            and result_a["invalid_moves"] != result_b["invalid_moves"]
        ),
    )

    fitness = Fitness()
    assert lower_invalid.simulate()["invalid_moves"] < higher_invalid.simulate()["invalid_moves"]
    assert fitness.evaluate(lower_invalid) > fitness.evaluate(higher_invalid)


def test_fitness_considers_length_when_previous_criteria_are_equal() -> None:
    board = Board(3, [1, 2, 3, 4, 5, 6, 7, 0, 8])

    shorter, longer = _find_pair_same_distance_and_invalid(board)

    fitness = Fitness()
    assert len(shorter) < len(longer)
    assert fitness.evaluate(shorter) > fitness.evaluate(longer)


def test_compatibility_with_selection_and_elitism() -> None:
    board = Board(3, [1, 2, 3, 4, 5, 6, 7, 0, 8])
    solved = Individual(["R"], board)
    unsolved = Individual(["L", "L"], board)
    population = [unsolved, solved]

    assert max(population, key=Fitness()) is solved
    elites = sorted(population, key=Fitness(), reverse=True)
    assert elites[0] is solved


def test_fitness_weight_validation() -> None:
    with pytest.raises(ValueError):
        Fitness(alpha=-0.1)

    with pytest.raises(ValueError):
        Fitness(beta=-0.1)

    with pytest.raises(ValueError):
        Fitness(alpha="bad")

    with pytest.raises(ValueError):
        Fitness(alpha=float("nan"))

    with pytest.raises(ValueError):
        Fitness(beta=float("inf"))

    with pytest.raises(ValueError):
        calculate_fitness("x")

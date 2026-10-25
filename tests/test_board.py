import pytest

from puzzle.board import Board


def test_goal_state_3x3() -> None:
    board = Board(3)
    assert board.goal_state() == [1, 2, 3, 4, 5, 6, 7, 8, 0]


def test_goal_state_4x4() -> None:
    board = Board(4)
    assert board.goal_state() == list(range(1, 16)) + [0]


def test_size_and_initial_state_validation() -> None:
    with pytest.raises(ValueError):
        Board(1)

    with pytest.raises(ValueError):
        Board(3, [1, 2, 3, 4, 5, 6, 7, 8])

    with pytest.raises(ValueError):
        Board(3, [1, 2, 3, 4, 5, 6, 7, 8, 8])

    with pytest.raises(ValueError):
        Board(3, [1, 2, 3, 4, 5, 6, 7, 0, 0])


def test_get_valid_moves() -> None:
    board = Board(3)
    assert board.get_valid_moves() == ["U", "L"]

    board = Board(3, [1, 2, 3, 4, 5, 6, 7, 0, 8])
    assert board.get_valid_moves() == ["U", "L", "R"]


def test_invalid_moves_do_not_change_state() -> None:
    board = Board(3, [1, 2, 3, 4, 5, 6, 0, 7, 8])
    original_state = board.state[:]

    assert board.move("L") is False
    assert board.state == original_state

    assert board.move("X") is False
    assert board.state == original_state

    assert board.move("R") is True
    assert board.state == [1, 2, 3, 4, 5, 6, 7, 0, 8]


def test_manhattan_distance_goal_and_after_move() -> None:
    board = Board(3)
    assert board.manhattan_distance() == 0

    board = Board(3, [1, 2, 3, 4, 5, 6, 7, 0, 8])
    assert board.manhattan_distance() == 1


def test_is_solved() -> None:
    assert Board(3).is_solved() is True
    assert Board(3, [1, 2, 3, 4, 5, 6, 7, 0, 8]).is_solved() is False


def test_copy_is_independent() -> None:
    original = Board(3, [1, 2, 3, 4, 5, 6, 7, 0, 8])
    copy_board = original.copy()

    copy_board.state[0] = 99

    assert original.state[0] == 1
    assert copy_board.state[0] == 99
    assert original.state == [1, 2, 3, 4, 5, 6, 7, 0, 8]


def test_random_solvable_zero_moves() -> None:
    board = Board.random_solvable(size=3, shuffle_moves=0)
    assert board.state == [1, 2, 3, 4, 5, 6, 7, 8, 0]
    assert board.is_solved() is True


def test_random_solvable_positive_moves() -> None:
    board = Board.random_solvable(size=3, shuffle_moves=1)
    assert len(board.state) == 9
    assert set(board.state) == set(range(9))
    assert board.is_solved() is False


def test_random_solvable_parameter_validation() -> None:
    with pytest.raises(ValueError):
        Board.random_solvable(size=1)

    with pytest.raises(ValueError):
        Board.random_solvable(size=3, shuffle_moves=-1)

    with pytest.raises(ValueError):
        Board.random_solvable(size="3")

    with pytest.raises(ValueError):
        Board.random_solvable(size=3, shuffle_moves=True)

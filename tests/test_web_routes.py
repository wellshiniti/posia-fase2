import json

from app import app
from puzzle.board import Board


def test_index_route_returns_html() -> None:
    client = app.test_client()
    response = client.get('/')

    assert response.status_code == 200
    assert b'html' in response.data.lower()


def test_random_route_returns_valid_board() -> None:
    client = app.test_client()
    response = client.get('/random?size=3')

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['size'] == 3
    assert len(payload['state']) == 9
    assert sorted(payload['state']) == list(range(9))


def test_random_route_rejects_invalid_size() -> None:
    client = app.test_client()
    response = client.get('/random?size=2')

    assert response.status_code == 400
    assert 'size' in response.get_json()['error'].lower()


def test_random_route_rejects_non_integer_text_size() -> None:
    client = app.test_client()
    response = client.get('/random?size=abc')

    assert response.status_code == 400
    assert 'size' in response.get_json()['error'].lower()


def test_solve_route_accepts_valid_state() -> None:
    client = app.test_client()
    payload = {
        'size': 3,
        'state': [1, 2, 3, 4, 5, 6, 7, 0, 8],
    }
    response = client.post('/solve', json=payload)

    assert response.status_code == 200
    result = response.get_json()
    assert 'solved' in result
    assert 'stop_reason' in result
    assert 'best_sequence' in result


def test_solve_route_rejects_invalid_state() -> None:
    client = app.test_client()
    payload = {
        'size': 3,
        'state': [1, 2, 3, 4, 5, 6, 7, 8],
    }
    response = client.post('/solve', json=payload)

    assert response.status_code == 400
    assert 'error' in response.get_json()


def test_solve_route_rejects_missing_size() -> None:
    client = app.test_client()
    response = client.post('/solve', json={'state': [1, 2, 3, 4, 5, 6, 7, 0, 8]})

    assert response.status_code == 400
    assert 'size' in response.get_json()['error'].lower()


def test_solve_route_rejects_fractional_size() -> None:
    client = app.test_client()
    payload = {
        'size': 3.5,
        'state': [1, 2, 3, 4, 5, 6, 7, 0, 8],
    }
    response = client.post('/solve', json=payload)

    assert response.status_code == 400
    assert 'size' in response.get_json()['error'].lower()


def test_solve_route_rejects_fractional_piece_values() -> None:
    client = app.test_client()
    payload = {
        'size': 3,
        'state': [1, 2, 3, 4, 5, 6, 7, 1.2, 8],
    }
    response = client.post('/solve', json=payload)

    assert response.status_code == 400
    assert 'inteiro' in response.get_json()['error'].lower() or 'número' in response.get_json()['error'].lower()


def test_solve_route_rejects_boolean_values() -> None:
    client = app.test_client()
    payload = {
        'size': 3,
        'state': [1, 2, 3, 4, 5, 6, True, 0, 8],
    }
    response = client.post('/solve', json=payload)

    assert response.status_code == 400
    assert 'boolean' in response.get_json()['error'].lower() or 'inteiro' in response.get_json()['error'].lower()


def test_solve_route_accepts_valid_solver_parameters() -> None:
    client = app.test_client()
    payload = {
        'size': 3,
        'state': [1, 2, 3, 4, 5, 6, 7, 0, 8],
        'population_size': 16,
        'initial_chromosome_length': 8,
        'crossover_rate': 0.75,
        'mutation_rate': 0.2,
        'tournament_size': 4,
        'elites_count': 2,
        'max_chromosome_length': 40,
        'max_generations': 50,
        'time_limit': 5.0,
        'random_seed': 123,
    }
    response = client.post('/solve', json=payload)

    assert response.status_code == 200
    result = response.get_json()
    assert 'solved' in result
    assert 'stop_reason' in result


def test_solve_route_rejects_incompatible_solver_parameters() -> None:
    client = app.test_client()
    payload = {
        'size': 3,
        'state': [1, 2, 3, 4, 5, 6, 7, 0, 8],
        'population_size': 5,
        'tournament_size': 8,
        'elites_count': 5,
    }
    response = client.post('/solve', json=payload)

    assert response.status_code == 400
    assert 'population_size' in response.get_json()['error'].lower() or 'tournament_size' in response.get_json()['error'].lower() or 'elites_count' in response.get_json()['error'].lower()


def test_solve_route_rejects_out_of_range_probability_values() -> None:
    client = app.test_client()
    payload = {
        'size': 3,
        'state': [1, 2, 3, 4, 5, 6, 7, 0, 8],
        'crossover_rate': 1.5,
        'mutation_rate': float('nan'),
    }
    response = client.post('/solve', json=payload)

    assert response.status_code == 400
    assert 'crossover_rate' in response.get_json()['error'].lower() or 'mutation_rate' in response.get_json()['error'].lower()


def test_board_move_sequence_reproduces_solution_without_mutating_original_board() -> None:
    original = [1, 2, 3, 4, 5, 6, 7, 0, 8]
    board = Board(3, original)
    replay_board = board.copy()

    for move in ['R']:
        assert replay_board.move(move) is True

    assert board.state == original
    assert replay_board.state == [1, 2, 3, 4, 5, 6, 7, 8, 0]
    assert replay_board.is_solved() is True


def test_board_replay_with_empty_sequence_keeps_state() -> None:
    original = [1, 2, 3, 4, 5, 6, 7, 0, 8]
    board = Board(3, original)
    replay_board = board.copy()

    for _ in []:
        replay_board.move('R')

    assert replay_board.state == original

from __future__ import annotations

import math
from typing import Any

from flask import Flask, jsonify, render_template, request

from genetic_algorithm.solver import GeneticAlgorithmSolver
from puzzle.board import Board

app = Flask(__name__)

VALID_SIZES = {3, 4}
DEFAULT_SOLVER_PARAMS = {
    "population_size": 20,
    "initial_chromosome_length": 10,
    "crossover_rate": 0.8,
    "mutation_rate": 0.1,
    "tournament_size": 3,
    "elites_count": 2,
    "max_chromosome_length": 50,
    "max_generations": 100,
    "time_limit": None,
    "random_seed": None,
}


def _normalize_state(raw_state: Any, size: int) -> list[int]:
    """Normaliza um estado em lista de inteiros para o tabuleiro informado."""
    def validate_piece(piece: Any) -> int:
        if isinstance(piece, bool):
            raise ValueError("Peças booleanas não são válidas.")
        if isinstance(piece, int):
            return piece
        if isinstance(piece, float):
            if not piece.is_integer():
                raise ValueError("state deve conter apenas inteiros válidos.")
            return int(piece)
        if isinstance(piece, str):
            text = piece.strip()
            if not text:
                raise ValueError("state deve conter apenas inteiros válidos.")
            try:
                number = float(text)
            except ValueError as exc:
                raise ValueError("state deve conter apenas inteiros válidos.") from exc
            if not number.is_integer():
                raise ValueError("state deve conter apenas inteiros válidos.")
            return int(number)
        raise ValueError("state deve conter apenas inteiros válidos.")

    if isinstance(raw_state, str):
        values = [piece.strip() for piece in raw_state.replace(";", ",").split(",")]
        values = [piece for piece in values if piece]
        normalized = [validate_piece(piece) for piece in values]
    elif isinstance(raw_state, list):
        normalized = [validate_piece(piece) for piece in raw_state]
    else:
        raise ValueError("state deve ser uma lista ou texto de números inteiros.")

    if len(normalized) != size * size:
        raise ValueError(
            f"state deve conter exatamente {size * size} peças para um tabuleiro {size}x{size}."
        )

    if sorted(normalized) != list(range(size * size)):
        raise ValueError(
            "state deve conter todas as peças de 0 até "
            f"{size * size - 1} exatamente uma vez."
        )

    return normalized


def _parse_int(value: Any, name: str, *, minimum: int) -> int:
    if value is None:
        raise ValueError(f"{name} é obrigatório.")
    if isinstance(value, bool):
        raise ValueError(f"{name} deve ser um inteiro.")
    if isinstance(value, float) and not value.is_integer():
        raise ValueError(f"{name} deve ser um inteiro.")
    try:
        integer_value = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} deve ser um inteiro.") from None

    if integer_value < minimum:
        raise ValueError(f"{name} deve ser maior ou igual a {minimum}.")
    return integer_value


def _parse_probability(value: Any, name: str) -> float:
    if value is None:
        raise ValueError(f"{name} é obrigatório.")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} deve ser um número real.")
    numeric_value = float(value)
    if not math.isfinite(numeric_value):
        raise ValueError(f"{name} deve ser finito.")
    if not 0.0 <= numeric_value <= 1.0:
        raise ValueError(f"{name} deve estar entre 0 e 1.")
    return numeric_value


def _parse_time_limit(value: Any) -> float | None:
    if value in (None, "", "null"):
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("time_limit deve ser um número real ou vazio.")
    numeric_value = float(value)
    if not math.isfinite(numeric_value) or numeric_value <= 0:
        raise ValueError("time_limit deve ser finito e maior que zero.")
    return numeric_value


def _parse_random_seed(value: Any) -> int | None:
    if value in (None, "", "null"):
        return None
    return _parse_int(value, "random_seed", minimum=0)


def _validate_solver_config(payload: dict[str, Any]) -> dict[str, Any]:
    config: dict[str, Any] = {}
    config["population_size"] = _parse_int(
        payload.get("population_size", DEFAULT_SOLVER_PARAMS["population_size"]),
        "population_size",
        minimum=1,
    )
    config["initial_chromosome_length"] = _parse_int(
        payload.get("initial_chromosome_length", DEFAULT_SOLVER_PARAMS["initial_chromosome_length"]),
        "initial_chromosome_length",
        minimum=0,
    )
    config["crossover_rate"] = _parse_probability(
        payload.get("crossover_rate", DEFAULT_SOLVER_PARAMS["crossover_rate"]),
        "crossover_rate",
    )
    config["mutation_rate"] = _parse_probability(
        payload.get("mutation_rate", DEFAULT_SOLVER_PARAMS["mutation_rate"]),
        "mutation_rate",
    )
    config["tournament_size"] = _parse_int(
        payload.get("tournament_size", DEFAULT_SOLVER_PARAMS["tournament_size"]),
        "tournament_size",
        minimum=1,
    )
    config["elites_count"] = _parse_int(
        payload.get("elites_count", DEFAULT_SOLVER_PARAMS["elites_count"]),
        "elites_count",
        minimum=1,
    )
    config["max_chromosome_length"] = _parse_int(
        payload.get("max_chromosome_length", DEFAULT_SOLVER_PARAMS["max_chromosome_length"]),
        "max_chromosome_length",
        minimum=0,
    )
    config["max_generations"] = _parse_int(
        payload.get("max_generations", DEFAULT_SOLVER_PARAMS["max_generations"]),
        "max_generations",
        minimum=1,
    )
    config["time_limit"] = _parse_time_limit(payload.get("time_limit", DEFAULT_SOLVER_PARAMS["time_limit"]))
    config["random_seed"] = _parse_random_seed(payload.get("random_seed", DEFAULT_SOLVER_PARAMS["random_seed"]))

    if config["tournament_size"] > config["population_size"]:
        raise ValueError("tournament_size não pode ser maior que population_size.")
    if config["elites_count"] >= config["population_size"]:
        raise ValueError("elites_count deve ser menor que population_size.")
    if config["initial_chromosome_length"] > config["max_chromosome_length"]:
        raise ValueError("initial_chromosome_length não pode ser maior que max_chromosome_length.")

    return config


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/random")
def random_board():
    size_raw = request.args.get("size")
    try:
        size = int(size_raw) if size_raw is not None else 3
    except (TypeError, ValueError):
        return jsonify({"error": "size deve ser um inteiro válido (3 ou 4)."}), 400

    if size not in VALID_SIZES:
        return jsonify({"error": "size deve ser 3 ou 4."}), 400

    board = Board.random_solvable(size=size)
    return jsonify({"size": board.size, "state": board.state})


@app.post("/solve")
def solve():
    payload = request.get_json(silent=True) or {}
    size = payload.get("size")

    if size is None:
        return jsonify({"error": "size é obrigatório."}), 400

    if isinstance(size, bool):
        return jsonify({"error": "size deve ser um inteiro válido (3 ou 4)."}), 400
    if isinstance(size, int):
        size_value = size
    elif isinstance(size, float):
        if not size.is_integer():
            return jsonify({"error": "size deve ser um inteiro válido (3 ou 4)."}), 400
        size_value = int(size)
    else:
        try:
            size_value = int(size)
        except (TypeError, ValueError):
            return jsonify({"error": "size deve ser um inteiro válido (3 ou 4)."}), 400
        if str(size).strip() != str(size_value):
            return jsonify({"error": "size deve ser um inteiro válido (3 ou 4)."}), 400

    size = size_value
    if size not in VALID_SIZES:
        return jsonify({"error": "size deve ser 3 ou 4."}), 400

    raw_state = payload.get("state")
    if raw_state is None:
        return jsonify({"error": "state é obrigatório."}), 400

    try:
        state = _normalize_state(raw_state, size)
        board = Board(size, state)
    except (TypeError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 400

    try:
        solver_config = _validate_solver_config(payload)
        solver = GeneticAlgorithmSolver(initial_board=board, **solver_config)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    result = solver.solve()
    return jsonify(result)


if __name__ == "__main__":
    app.run(debug=True)

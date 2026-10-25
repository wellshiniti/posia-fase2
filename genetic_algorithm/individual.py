from __future__ import annotations

import random
from typing import Any, Dict, List, Optional, Sequence

from puzzle.board import Board

VALID_MOVES = {"U", "D", "L", "R"}
ORDERED_MOVES = ("U", "D", "L", "R")


class Individual:
    """Representa um cromossoma de movimentos para um tabuleiro N-Puzzle.

    O cromossoma é uma sequência de movimentos válidos (U, D, L, R). A
    avaliação do indivíduo é feita sobre uma cópia do tabuleiro inicial para
    garantir que o estado original não seja alterado.
    """

    def __init__(
        self,
        chromosome: Optional[Sequence[str]] = None,
        initial_board: Optional[Board] = None,
    ) -> None:
        """Cria um indivíduo.

        Args:
            chromosome: sequência de movimentos. Quando omitida, usa uma lista
                vazia.
            initial_board: estado inicial do tabuleiro usado para simulação.

        Raises:
            ValueError: quando a sequência contiver movimentos inválidos.
            ValueError: quando o tabuleiro inicial não for informado.
        """
        if initial_board is None:
            raise ValueError("initial_board deve ser informado.")
        if not isinstance(initial_board, Board):
            raise ValueError("initial_board deve ser uma instância de Board.")

        self.initial_board = initial_board.copy()
        self.chromosome = self._validate_chromosome(chromosome or [])

    @staticmethod
    def _validate_chromosome(chromosome: Sequence[str]) -> List[str]:
        """Valida e normaliza o cromossomo para letras maiúsculas."""
        if isinstance(chromosome, (str, bytes)):
            raise ValueError("chromosome deve ser uma sequência de movimentos.")

        normalized: List[str] = []
        for move in chromosome:
            if not isinstance(move, str):
                raise ValueError("Cada movimento deve ser um valor do tipo str.")
            normalized_move = move.upper()
            if normalized_move not in VALID_MOVES:
                raise ValueError(
                    "Movimentos inválidos no cromossomo. Use apenas U, D, L ou R."
                )
            normalized.append(normalized_move)
        return normalized

    @classmethod
    def random(
        cls,
        initial_board: Board,
        length: int,
        rng: Optional[random.Random] = None,
    ) -> "Individual":
        """Cria um indivíduo com cromossomo aleatório."""
        if not isinstance(length, int) or isinstance(length, bool) or length < 0:
            raise ValueError("length deve ser um inteiro maior ou igual a zero.")
        if not isinstance(initial_board, Board):
            raise ValueError("initial_board deve ser uma instância de Board.")

        generator = rng if rng is not None else random.Random()
        chromosome = [generator.choice(ORDERED_MOVES) for _ in range(length)]
        return cls(chromosome=chromosome, initial_board=initial_board)

    def copy(self) -> "Individual":
        """Retorna uma cópia do indivíduo com cromossomo independente."""
        return Individual(chromosome=self.chromosome[:], initial_board=self.initial_board)

    def simulate(self) -> Dict[str, Any]:
        """Simula a execução do cromossomo em uma cópia do tabuleiro inicial.

        Movimentos inválidos não alteram o tabuleiro e são registrados em
        `invalid_moves` para posterior penalização na aptidão.
        """
        board = self.initial_board.copy()
        invalid_moves = 0

        for move in self.chromosome:
            if not board.move(move):
                invalid_moves += 1

        return {
            "final_state": board.state[:],
            "invalid_moves": invalid_moves,
            "moves_attempted": len(self.chromosome),
            "solved": board.is_solved(),
            "manhattan_distance": board.manhattan_distance(),
        }

    def evaluate(self) -> Dict[str, Any]:
        """Avalia o indivíduo de forma determinística e sem modificar o estado inicial."""
        return self.simulate()

    def __len__(self) -> int:
        """Retorna o comprimento do cromossomo."""
        return len(self.chromosome)

    def __repr__(self) -> str:
        return f"Individual(chromosome={self.chromosome!r}, initial_board={self.initial_board!r})"

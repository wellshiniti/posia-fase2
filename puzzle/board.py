from __future__ import annotations

import random
from typing import List, Optional, Sequence


class Board:
    """Representa um tabuleiro N-Puzzle com dimensão configurável."""

    def __init__(self, size: int, initial_state: Optional[Sequence[int]] = None) -> None:
        """Inicializa o tabuleiro.

        Args:
            size: dimensão do tabuleiro, como 3 para 3x3.
            initial_state: sequência opcional de peças. Se omitida, usa o
                estado objetivo padrão.

        Raises:
            ValueError: quando o tamanho ou a configuração inicial são inválidos.
        """
        self.size = self._validate_size(size)

        if initial_state is None:
            self.state = self.goal_state()
        else:
            self.state = self._validate_and_normalize_state(initial_state)

    @staticmethod
    def _validate_size(size: int) -> int:
        """Valida a dimensão do tabuleiro."""
        if not isinstance(size, int) or isinstance(size, bool) or size <= 2:
            raise ValueError("size deve ser um inteiro maior ou igual a 2.")
        return size

    def goal_state(self) -> List[int]:
        """Retorna o estado objetivo para a dimensão atual do tabuleiro."""
        total = self.size * self.size
        return list(range(1, total)) + [0]

    def _validate_and_normalize_state(self, values: Sequence[int]) -> List[int]:
        """Valida uma sequência de peças e a converte para lista."""
        if not isinstance(values, Sequence):
            raise ValueError("initial_state deve ser uma sequência de inteiros.")

        state = list(values)
        expected_size = self.size * self.size

        if len(state) != expected_size:
            raise ValueError(
                f"A configuração inicial deve conter exatamente {expected_size} peças."
            )

        expected = list(range(expected_size))
        if sorted(state) != expected:
            raise ValueError(
                "A configuração inicial deve conter todas as peças de 0 até "
                f"{expected_size - 1} exatamente uma vez."
            )

        return state

    def get_valid_moves(self) -> List[str]:
        """Retorna os movimentos válidos para o espaço vazio."""
        zero_index = self.state.index(0)
        row, col = divmod(zero_index, self.size)
        moves: List[str] = []

        if row > 0:
            moves.append("U")
        if row < self.size - 1:
            moves.append("D")
        if col > 0:
            moves.append("L")
        if col < self.size - 1:
            moves.append("R")

        return moves

    def move(self, direction: str) -> bool:
        """Move o espaço vazio em uma direção válida.

        Args:
            direction: um dos caracteres 'U', 'D', 'L' ou 'R'.

        Returns:
            True se o movimento foi executado; False se for inválido.
        """
        if not isinstance(direction, str):
            return False

        direction = direction.upper()
        if direction not in {"U", "D", "L", "R"}:
            return False

        zero_index = self.state.index(0)
        row, col = divmod(zero_index, self.size)

        target_index = None
        if direction == "U":
            if row == 0:
                return False
            target_index = zero_index - self.size
        elif direction == "D":
            if row == self.size - 1:
                return False
            target_index = zero_index + self.size
        elif direction == "L":
            if col == 0:
                return False
            target_index = zero_index - 1
        elif direction == "R":
            if col == self.size - 1:
                return False
            target_index = zero_index + 1

        if target_index is None:
            return False

        self.state[zero_index], self.state[target_index] = (
            self.state[target_index],
            self.state[zero_index],
        )
        return True

    def manhattan_distance(self) -> int:
        """Calcula a soma de distâncias Manhattan das peças até o objetivo."""
        total = 0
        goal = self.goal_state()

        for index, value in enumerate(self.state):
            if value == 0:
                continue

            goal_index = value - 1
            current_row, current_col = divmod(index, self.size)
            goal_row, goal_col = divmod(goal_index, self.size)
            total += abs(current_row - goal_row) + abs(current_col - goal_col)

        return total

    def is_solved(self) -> bool:
        """Retorna True quando o estado atual coincide com o objetivo."""
        return self.state == self.goal_state()

    def copy(self) -> "Board":
        """Cria uma cópia independente do tabuleiro atual."""
        return Board(self.size, self.state[:])

    @classmethod
    def random_solvable(
        cls, size: int = 3, shuffle_moves: int = 100
    ) -> "Board":
        """Gera um tabuleiro legalmente solucionável por embaralhamento do objetivo.

        O método parte do estado objetivo e aplica uma sequência de movimentos
        válidos, evitando desfazer imediatamente o último movimento para reduzir
        embaralhamentos redundantes.
        """
        if not isinstance(size, int) or isinstance(size, bool) or size <= 2:
            raise ValueError("size deve ser um inteiro maior ou igual a 2.")
        if not isinstance(shuffle_moves, int) or isinstance(shuffle_moves, bool):
            raise ValueError("shuffle_moves deve ser um inteiro.")
        if shuffle_moves < 0:
            raise ValueError("shuffle_moves deve ser maior ou igual a zero.")

        board = cls(size)
        previous_move: Optional[str] = None
        opposite = {"U": "D", "D": "U", "L": "R", "R": "L"}

        for _ in range(shuffle_moves):
            valid_moves = board.get_valid_moves()
            if previous_move is not None:
                valid_moves = [
                    move for move in valid_moves if opposite[move] != previous_move
                ]

            if not valid_moves:
                break

            move = random.choice(valid_moves)
            board.move(move)
            previous_move = move

        if shuffle_moves > 0 and size > 1 and board.is_solved():
            valid_moves = board.get_valid_moves()
            if previous_move is not None:
                valid_moves = [
                    move for move in valid_moves if opposite[move] != previous_move
                ]
            if not valid_moves:
                valid_moves = board.get_valid_moves()
            board.move(random.choice(valid_moves))

        return board

    def __str__(self) -> str:
        """Retorna uma representação textual legível do tabuleiro."""
        rows: List[str] = []
        for row_index in range(0, len(self.state), self.size):
            row = self.state[row_index : row_index + self.size]
            rendered = [str(value) if value != 0 else "_" for value in row]
            rows.append(" ".join(rendered))
        return "\n".join(rows)

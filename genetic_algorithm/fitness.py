from __future__ import annotations

import math
from typing import Union

from genetic_algorithm.individual import Individual


class Fitness:
    """Calcula a aptidão de um indivíduo do N-Puzzle.

    A ordenação é feita em etapas, em vez de depender apenas de um único peso
    global: primeiro um tabuleiro resolvido, depois menor distância de Manhattan,
    depois menos movimentos inválidos e, por fim, menor comprimento do
    cromossomo. Essa estrutura preserva a prioridade explícita da solução e torna
    a classificação mais coerente com a noção de progresso real do estado.

    O valor retornado continua sendo um float para manter compatibilidade com as
    chamadas existentes em seleção, elitismo e métricas das gerações.
    """

    def __init__(self, alpha: float = 1.0, beta: float = 0.01) -> None:
        """Inicializa a classe de aptidão."""
        self.alpha = self._validate_weight(alpha, "alpha")
        self.beta = self._validate_weight(beta, "beta")

    @staticmethod
    def _validate_weight(value: Union[int, float], name: str) -> float:
        """Valida pesos da fórmula de fitness."""
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{name} deve ser um número real.")
        if not math.isfinite(value):
            raise ValueError(f"{name} deve ser finito.")
        if value < 0:
            raise ValueError(f"{name} deve ser maior ou igual a zero.")
        return float(value)

    def evaluate(self, individual: Individual) -> float:
        """Calcula a aptidão do indivíduo."""
        if not isinstance(individual, Individual):
            raise ValueError("individual deve ser uma instância de Individual.")

        result = individual.evaluate()
        distance = result["manhattan_distance"]
        invalid_moves = result["invalid_moves"]
        chromosome_length = len(individual)

        if result["solved"]:
            solved_bonus = 1_000_000_000.0
            return solved_bonus + 1.0 / (1.0 + self.alpha * invalid_moves + self.beta * chromosome_length)

        distance_term = 1_000_000.0 / (1.0 + distance)
        invalid_term = 10_000.0 / (1.0 + self.alpha * invalid_moves)
        length_term = 100.0 / (1.0 + self.beta * chromosome_length)
        return distance_term + invalid_term + length_term

    def __call__(self, individual: Individual) -> float:
        """Permite chamar a instância como função."""
        return self.evaluate(individual)


def calculate_fitness(
    individual: Individual,
    alpha: float = 1.0,
    beta: float = 0.01,
) -> float:
    """Função utilitária para calcular a aptidão de um indivíduo."""
    if not isinstance(individual, Individual):
        raise ValueError("individual deve ser uma instância de Individual.")
    return Fitness(alpha=alpha, beta=beta).evaluate(individual)

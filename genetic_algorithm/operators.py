from __future__ import annotations

import math
import random
from typing import Callable, Optional, Sequence, Tuple

from genetic_algorithm.individual import Individual, ORDERED_MOVES, VALID_MOVES


def tournament_selection(
    population: Sequence[Individual],
    evaluator: Callable[[Individual], float],
    tournament_size: int = 3,
    rng: Optional[random.Random] = None,
) -> Individual:
    """Seleciona um indivíduo via torneio.

    A população deve conter indivíduos válidos; o torneio aleatoriamente escolhe
    ``tournament_size`` candidatos e retorna o melhor deles segundo ``evaluator``.

    A decisão aqui foi rejeitar torneios maiores que a população, em vez de
    truncá-los, porque a regra explícita evita ambiguidades e facilita testes e
    depuração.
    """
    if not population:
        raise ValueError("population não pode ser vazia.")
    if not isinstance(tournament_size, int) or isinstance(tournament_size, bool):
        raise ValueError("tournament_size deve ser um inteiro.")
    if tournament_size <= 0:
        raise ValueError("tournament_size deve ser maior que zero.")
    if tournament_size > len(population):
        raise ValueError("tournament_size não pode ser maior que o tamanho da população.")
    if not callable(evaluator):
        raise ValueError("evaluator deve ser callable.")

    generator = rng if rng is not None else random.Random()
    candidates = [population[generator.randrange(len(population))] for _ in range(tournament_size)]
    winner = max(candidates, key=evaluator)
    return winner.copy()


def crossover(
    parent_a: Individual,
    parent_b: Individual,
    rng: Optional[random.Random] = None,
) -> Tuple[Individual, Individual]:
    """Cruza dois pais e retorna dois descendentes.

    Estratégia escolhida: crossover de um ponto por indivíduo. Para cada pai,
    gera um ponto de corte aleatório em seu próprio comprimento e monta o
    descendente com a parte antes do corte do pai atual e a parte após o corte
    do outro pai. Essa abordagem funciona para cromossomos de comprimentos
    diferentes, preserva o tabuleiro inicial e evita mutar os pais originais.

    Limitações: o método é positional e não aplica nenhum reparo semântico; ele
    apenas preserva a estrutura de movimentos válidos já presentes nos pais.
    """
    if not isinstance(parent_a, Individual):
        raise ValueError("parent_a deve ser um Individual.")
    if not isinstance(parent_b, Individual):
        raise ValueError("parent_b deve ser um Individual.")

    board_a = parent_a.initial_board
    board_b = parent_b.initial_board
    if board_a.size != board_b.size or board_a.state != board_b.state:
        raise ValueError("Os pais devem compartilhar o mesmo tabuleiro inicial.")

    generator = rng if rng is not None else random.Random()

    len_a = len(parent_a)
    len_b = len(parent_b)

    cut_a = generator.randint(0, len_a) if len_a > 0 else 0
    cut_b = generator.randint(0, len_b) if len_b > 0 else 0

    child_a = parent_a.chromosome[:cut_a] + parent_b.chromosome[cut_b:]
    child_b = parent_b.chromosome[:cut_b] + parent_a.chromosome[cut_a:]

    for chromosome in (child_a, child_b):
        for move in chromosome:
            if move not in VALID_MOVES:
                raise ValueError("Cromossomo inválido gerado durante o cruzamento.")

    return (
        Individual(chromosome=child_a, initial_board=board_a.copy()),
        Individual(chromosome=child_b, initial_board=board_b.copy()),
    )


def mutate(
    individual: Individual,
    mutation_rate: float = 0.1,
    max_length: Optional[int] = None,
    rng: Optional[random.Random] = None,
    mutation_type: Optional[str] = None,
) -> Individual:
    """Aplica mutação sobre uma cópia do indivíduo.

    A taxa é aplicada por indivíduo: se um número aleatório estiver acima da
    probabilidade configurada, o indivíduo é retornado intacto; caso contrário,
    uma operação escolhida entre substituição, inserção e remoção é aplicada.
    """
    if not isinstance(individual, Individual):
        raise ValueError("individual deve ser um Individual.")
    if not isinstance(mutation_rate, (int, float)) or isinstance(mutation_rate, bool):
        raise ValueError("mutation_rate deve ser um número real.")
    if not math.isfinite(float(mutation_rate)):
        raise ValueError("mutation_rate deve ser finito.")
    if mutation_rate < 0 or mutation_rate > 1:
        raise ValueError("mutation_rate deve estar entre 0 e 1.")
    if max_length is not None:
        if not isinstance(max_length, int) or isinstance(max_length, bool):
            raise ValueError("max_length deve ser um inteiro ou None.")
        if max_length < 0:
            raise ValueError("max_length deve ser maior ou igual a zero.")

    available_operations = ["substitution", "insertion", "removal"]
    if mutation_type is not None and mutation_type not in available_operations:
        raise ValueError("mutation_type deve ser substitution, insertion ou removal.")

    generator = rng if rng is not None else random.Random()
    mutated = individual.copy()

    if max_length is not None and len(mutated.chromosome) > max_length:
        del mutated.chromosome[max_length:]

    if mutation_rate == 0 or generator.random() > mutation_rate:
        return mutated

    operation = mutation_type or generator.choice(available_operations)

    if operation == "substitution":
        if not mutated.chromosome:
            return mutated
        index = generator.randrange(len(mutated.chromosome))
        alternatives = [move for move in ORDERED_MOVES if move != mutated.chromosome[index]]
        mutated.chromosome[index] = generator.choice(alternatives)
        return Individual(chromosome=mutated.chromosome, initial_board=individual.initial_board)

    if operation == "insertion":
        if max_length is not None and len(mutated.chromosome) >= max_length:
            return Individual(chromosome=mutated.chromosome[:max_length], initial_board=individual.initial_board)
        index = generator.randrange(len(mutated.chromosome) + 1)
        mutated.chromosome.insert(index, generator.choice(ORDERED_MOVES))
        if max_length is not None and len(mutated.chromosome) > max_length:
            del mutated.chromosome[max_length:]
        return Individual(chromosome=mutated.chromosome, initial_board=individual.initial_board)

    if operation == "removal":
        if not mutated.chromosome:
            return mutated
        index = generator.randrange(len(mutated.chromosome))
        del mutated.chromosome[index]
        return Individual(chromosome=mutated.chromosome, initial_board=individual.initial_board)

    return mutated


def elitism(
    population: Sequence[Individual],
    evaluator: Callable[[Individual], float],
    keep_count: int,
) -> list[Individual]:
    """Retorna cópias independentes dos melhores indivíduos da população.

    Os indivíduos são ordenados por fitness em ordem decrescente e os primeiros
    ``keep_count`` são preservados como cópias independentes.
    """
    if not population:
        raise ValueError("population não pode ser vazia.")
    if not callable(evaluator):
        raise ValueError("evaluator deve ser callable.")
    if not isinstance(keep_count, int) or isinstance(keep_count, bool):
        raise ValueError("keep_count deve ser um inteiro.")
    if keep_count <= 0:
        raise ValueError("keep_count deve ser maior que zero.")
    if keep_count > len(population):
        raise ValueError("keep_count não pode ser maior que o tamanho da população.")

    ordered = sorted(population, key=evaluator, reverse=True)
    return [individual.copy() for individual in ordered[:keep_count]]

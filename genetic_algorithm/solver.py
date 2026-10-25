from __future__ import annotations

import math
import random
import time
from typing import Any, Callable, Dict, List, Optional, Sequence

from genetic_algorithm.fitness import Fitness
from genetic_algorithm.individual import Individual
from genetic_algorithm.operators import (
    crossover,
    elitism,
    mutate,
    tournament_selection,
)
from puzzle.board import Board


class GeneticAlgorithmSolver:
    """Executa um algoritmo genético simples para resolver N-Puzzle.

    A implementação é uma heurística geral: gera uma população de cromossomos
    (sequências de movimentos), avalia cada indivíduo pela fitness existente,
    aplica seleção, cruzamento e mutação, preserva elites e encerra quando
    encontra uma solução, atinge o limite de gerações ou o limite de tempo.

    O algoritmo genético não garante encontrar uma solução em todas as execuções;
    ele serve como heurística para explorar sequências de movimentos.
    """

    def __init__(
        self,
        initial_board: Board,
        population_size: int = 20,
        initial_chromosome_length: int = 10,
        crossover_rate: float = 0.8,
        mutation_rate: float = 0.1,
        tournament_size: int = 3,
        elites_count: int = 2,
        max_chromosome_length: int = 50,
        max_generations: int = 100,
        time_limit: Optional[float] = None,
        random_seed: Optional[int] = None,
    ) -> None:
        """Inicializa o resolvedor genético."""
        self.initial_board = self._validate_board(initial_board)
        self.population_size = self._validate_positive_int(population_size, "population_size")
        self.initial_chromosome_length = self._validate_non_negative_int(
            initial_chromosome_length, "initial_chromosome_length"
        )
        self.crossover_rate = self._validate_probability(crossover_rate, "crossover_rate")
        self.mutation_rate = self._validate_probability(mutation_rate, "mutation_rate")
        self.tournament_size = self._validate_positive_int(tournament_size, "tournament_size")
        if self.tournament_size > self.population_size:
            raise ValueError("tournament_size não pode ser maior que population_size.")
        self.elites_count = self._validate_positive_int(elites_count, "elites_count")
        if self.elites_count >= self.population_size:
            raise ValueError("elites_count deve ser menor que population_size.")
        self.max_chromosome_length = self._validate_non_negative_int(
            max_chromosome_length, "max_chromosome_length"
        )
        if self.initial_chromosome_length > self.max_chromosome_length:
            raise ValueError(
                "initial_chromosome_length não pode ser maior que max_chromosome_length."
            )
        self.max_generations = self._validate_positive_int(max_generations, "max_generations")
        if time_limit is not None:
            if not isinstance(time_limit, (int, float)) or isinstance(time_limit, bool):
                raise ValueError("time_limit deve ser um número real ou None.")
            if not math.isfinite(float(time_limit)) or float(time_limit) <= 0:
                raise ValueError("time_limit deve ser finito e maior que zero.")
        self.time_limit = None if time_limit is None else float(time_limit)
        self.random_seed = random_seed
        self.rng = random.Random(random_seed)
        self.fitness = Fitness()
        self.best_individual: Optional[Individual] = None

    @staticmethod
    def _validate_board(board: Board) -> Board:
        if not isinstance(board, Board):
            raise ValueError("initial_board deve ser uma instância de Board.")
        return board.copy()

    @staticmethod
    def _validate_positive_int(value: int, name: str) -> int:
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError(f"{name} deve ser um inteiro.")
        if value <= 0:
            raise ValueError(f"{name} deve ser maior que zero.")
        return value

    @staticmethod
    def _validate_non_negative_int(value: int, name: str) -> int:
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError(f"{name} deve ser um inteiro.")
        if value < 0:
            raise ValueError(f"{name} deve ser maior ou igual a zero.")
        return value

    @staticmethod
    def _validate_probability(value: float, name: str) -> float:
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError(f"{name} deve ser um número real.")
        value = float(value)
        if not math.isfinite(value):
            raise ValueError(f"{name} deve ser finito.")
        if not 0.0 <= value <= 1.0:
            raise ValueError(f"{name} deve estar entre 0 e 1.")
        return value

    def _initialize_population(self) -> List[Individual]:
        """Cria uma população inicial compatível com o tabuleiro inicial."""
        population: List[Individual] = []
        for _ in range(self.population_size):
            chromosome = self.rng.choices(
                population=["U", "D", "L", "R"],
                weights=[1, 1, 1, 1],
                k=self.initial_chromosome_length,
            )
            population.append(Individual(chromosome=chromosome, initial_board=self.initial_board))
        return population

    def _time_limit_reached(self, start_time: float) -> bool:
        """Retorna True quando o tempo configurado foi excedido."""
        if self.time_limit is None:
            return False
        return time.perf_counter() - start_time >= self.time_limit

    def _evaluate_population(
        self,
        population: Sequence[Individual],
        start_time: Optional[float] = None,
    ) -> List[tuple[Individual, float]]:
        """Avalia cada indivíduo e atualiza o melhor já encontrado."""
        evaluated: List[tuple[Individual, float]] = []
        for individual in population:
            if self.time_limit is not None and start_time is not None:
                if time.perf_counter() - start_time >= self.time_limit:
                    break
            score = self.fitness.evaluate(individual)
            evaluated.append((individual, score))
            if self.best_individual is None or score > self.fitness.evaluate(self.best_individual):
                self.best_individual = individual.copy()
        return evaluated

    def _generation_metrics(
        self,
        population: Sequence[Individual],
        evaluations: Sequence[tuple[Individual, float]],
        partial: bool = False,
    ) -> Dict[str, Any]:
        """Produz métricas sumarizadas para uma geração.

        Quando ``partial`` é verdadeiro, as métricas refletem apenas os indivíduos
        já avaliados nessa geração. Isso evita apresentar uma população parcial
        como se tivesse sido completamente avaliada.
        """
        if not evaluations:
            return {
                "best_fitness": 0.0,
                "average_fitness": 0.0,
                "min_manhattan_distance": 0,
                "best_chromosome_length": 0,
                "distinct_individuals": 0,
                "evaluated_count": 0,
                "partial": partial,
            }

        best_individual, best_fitness = max(evaluations, key=lambda item: item[1])
        average_fitness = sum(score for _, score in evaluations) / len(evaluations)
        min_manhattan = min(individual.simulate()["manhattan_distance"] for individual, _ in evaluations)
        best_chromosome_length = len(best_individual)
        distinct_individuals = len({tuple(individual.chromosome) for individual, _ in evaluations})

        return {
            "best_fitness": best_fitness,
            "average_fitness": average_fitness,
            "min_manhattan_distance": min_manhattan,
            "best_chromosome_length": best_chromosome_length,
            "distinct_individuals": distinct_individuals,
            "evaluated_count": len(evaluations),
            "partial": partial,
        }

    def _evolve_population(
        self,
        population: Sequence[Individual],
        start_time: Optional[float] = None,
    ) -> List[Individual]:
        """Gera uma nova população usando seleção, cruzamento, mutação e elitismo."""
        if self.time_limit is not None and start_time is not None and self._time_limit_reached(start_time):
            return [individual.copy() for individual in elitism(population, self.fitness.evaluate, self.elites_count)][: self.population_size]

        elites = elitism(population, self.fitness.evaluate, self.elites_count)
        next_population: List[Individual] = elites[:]

        while len(next_population) < self.population_size:
            if self.time_limit is not None and start_time is not None and self._time_limit_reached(start_time):
                break

            parent_a = tournament_selection(
                population,
                self.fitness.evaluate,
                tournament_size=self.tournament_size,
                rng=self.rng,
            )
            if self.time_limit is not None and start_time is not None and self._time_limit_reached(start_time):
                break

            parent_b = tournament_selection(
                population,
                self.fitness.evaluate,
                tournament_size=self.tournament_size,
                rng=self.rng,
            )
            if self.time_limit is not None and start_time is not None and self._time_limit_reached(start_time):
                break

            if self.rng.random() < self.crossover_rate:
                child_a, child_b = crossover(parent_a, parent_b, rng=self.rng)
            else:
                child_a = parent_a.copy()
                child_b = parent_b.copy()

            if self.time_limit is not None and start_time is not None and self._time_limit_reached(start_time):
                break

            child_a = mutate(
                child_a,
                mutation_rate=self.mutation_rate,
                max_length=self.max_chromosome_length,
                rng=self.rng,
            )
            if self.time_limit is not None and start_time is not None and self._time_limit_reached(start_time):
                break

            child_b = mutate(
                child_b,
                mutation_rate=self.mutation_rate,
                max_length=self.max_chromosome_length,
                rng=self.rng,
            )
            if self.time_limit is not None and start_time is not None and self._time_limit_reached(start_time):
                break

            next_population.extend([child_a, child_b])

        next_population = next_population[: self.population_size]

        deduplicated: List[Individual] = []
        seen: set[tuple[str, ...]] = set()
        for individual in next_population:
            key = tuple(individual.chromosome)
            if key in seen:
                continue
            deduplicated.append(individual)
            seen.add(key)

        while len(deduplicated) < self.population_size:
            if self.time_limit is not None and start_time is not None and self._time_limit_reached(start_time):
                break
            deduplicated.append(
                Individual.random(
                    initial_board=self.initial_board,
                    length=self.initial_chromosome_length,
                    rng=self.rng,
                )
            )

        return deduplicated[: self.population_size]

    def solve(self) -> Dict[str, Any]:
        """Executa o algoritmo genético e retorna um resultado estruturado.

        ``generations_run`` representa o número de entradas em ``history``.
        Cada entrada corresponde a uma geração iniciada, mesmo quando o tempo
        expira antes de a geração ser concluída; nesse caso, as métricas são
        marcadas com ``partial=True`` para evitar que a geração parcial seja
        interpretada como uma população completa.
        """
        if self.initial_board.is_solved():
            return {
                "solved": True,
                "solution": [],
                "best_sequence": [],
                "final_state": self.initial_board.goal_state(),
                "generations_run": 0,
                "stop_reason": "solved",
                "history": [{
                    "generation": 0,
                    "best_fitness": 1.0,
                    "average_fitness": 1.0,
                    "min_manhattan_distance": 0,
                    "best_chromosome_length": 0,
                    "distinct_individuals": 1,
                    "evaluated_count": 1,
                    "partial": False,
                }],
            }

        start_time = time.perf_counter()
        population = self._initialize_population()
        generation = 0
        stop_reason = "max_generations"
        history: List[Dict[str, Any]] = []

        while generation < self.max_generations:
            if self._time_limit_reached(start_time):
                stop_reason = "time_limit"
                break

            evaluations = self._evaluate_population(population, start_time=start_time)
            if self._time_limit_reached(start_time):
                stop_reason = "time_limit"
                if evaluations:
                    metrics = self._generation_metrics(population, evaluations, partial=True)
                    history.append({"generation": generation, **metrics})
                break
            if not evaluations:
                stop_reason = "time_limit"
                break

            metrics = self._generation_metrics(population, evaluations, partial=False)
            history.append({"generation": generation, **metrics})

            current_best = max(evaluations, key=lambda item: item[1])[0]
            current_best_result = current_best.simulate()
            if self.best_individual is None or self.fitness.evaluate(current_best) > self.fitness.evaluate(self.best_individual):
                self.best_individual = current_best.copy()

            if current_best_result["solved"]:
                stop_reason = "solved"
                break
            if self._time_limit_reached(start_time):
                stop_reason = "time_limit"
                break

            if generation + 1 >= self.max_generations:
                stop_reason = "max_generations"
                break
            if self._time_limit_reached(start_time):
                stop_reason = "time_limit"
                break

            population = self._evolve_population(population, start_time=start_time)
            if self._time_limit_reached(start_time):
                stop_reason = "time_limit"
                break
            generation += 1

        if self.best_individual is None:
            self.best_individual = Individual([], self.initial_board)

        best_result = self.best_individual.simulate()
        best_sequence = list(self.best_individual.chromosome)
        final_state = list(best_result["final_state"])
        solution = best_sequence[:] if best_result["solved"] else None

        return {
            "solved": bool(best_result["solved"]),
            "solution": solution,
            "best_sequence": best_sequence,
            "final_state": final_state,
            "generations_run": len(history),
            "stop_reason": stop_reason,
            "history": history,
        }

    def run(self) -> Dict[str, Any]:
        """Alias público para executar a busca genética."""
        return self.solve()

    def __call__(self) -> Dict[str, Any]:
        """Permite invocar a instância como função."""
        return self.solve()

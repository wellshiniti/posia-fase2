document.addEventListener('DOMContentLoaded', () => {
  const sizeSelect = document.getElementById('size');
  const boardElement = document.getElementById('board');
  const initialStateText = document.getElementById('initial-state-text');
  const resultBox = document.getElementById('result');
  const randomBoardButton = document.getElementById('random-board-btn');
  const solveButton = document.getElementById('solve-btn');
  const solverStatus = document.getElementById('solver-status');
  const solverStatusText = document.getElementById('solver-status-text');

  const replayStartButton = document.getElementById('replay-start-btn');
  const replayPauseButton = document.getElementById('replay-pause-btn');
  const replayResumeButton = document.getElementById('replay-resume-btn');
  const replayStepButton = document.getElementById('replay-step-btn');
  const replayResetButton = document.getElementById('replay-reset-btn');
  const replaySpeedInput = document.getElementById('replay-speed');
  const replaySpeedLabel = document.getElementById('replay-speed-label');
  const replayCounter = document.getElementById('replay-counter');
  const evolutionPanel = document.getElementById('evolution-panel');
  const generationCount = document.getElementById('generation-count');
  const bestFitness = document.getElementById('best-fitness');
  const averageFitness = document.getElementById('average-fitness');
  const minManhattan = document.getElementById('min-manhattan');
  const bestChromosomeLength = document.getElementById('best-chromosome-length');
  const distinctIndividuals = document.getElementById('distinct-individuals');
  const stopReason = document.getElementById('stop-reason');
  const evolutionChart = document.getElementById('evolution-chart');
  const toastContainer = document.createElement('div');
  toastContainer.className = 'toast-container';
  document.body.appendChild(toastContainer);

  const solverParams = {
    populationSize: document.getElementById('population-size'),
    initialChromosomeLength: document.getElementById('initial-chromosome-length'),
    crossoverRate: document.getElementById('crossover-rate'),
    mutationRate: document.getElementById('mutation-rate'),
    tournamentSize: document.getElementById('tournament-size'),
    elitesCount: document.getElementById('elites-count'),
    maxChromosomeLength: document.getElementById('max-chromosome-length'),
    maxGenerations: document.getElementById('max-generations'),
    timeLimit: document.getElementById('time-limit'),
    randomSeed: document.getElementById('random-seed'),
  };

  const playbackState = {
    sequence: [],
    initialState: [],
    currentState: [],
    currentIndex: 0,
    speedMs: Number(replaySpeedInput.value),
    timerId: null,
    playing: false,
  };

  function buildBoardFromState(state, size) {
    boardElement.style.gridTemplateColumns = `repeat(${size}, minmax(0, 64px))`;
    boardElement.innerHTML = '';

    state.forEach((value) => {
      const cell = document.createElement('div');
      cell.className = `cell ${value === 0 ? 'empty' : ''}`;
      cell.textContent = value === 0 ? '' : String(value);
      boardElement.appendChild(cell);
    });
  }

  function normalizeBoardStateFromGrid() {
    return [...boardElement.children].map((cell) => {
      const raw = cell.textContent.trim();
      return raw === '' ? 0 : Number(raw);
    });
  }

  function setResult(message, isError = false) {
    resultBox.classList.remove('error', 'hidden');
    resultBox.innerHTML = '';

    if (isError) {
      resultBox.classList.add('error');
    }

    if (typeof message === 'string') {
      resultBox.textContent = message;
      return;
    }

    if (Array.isArray(message)) {
      message.forEach((item) => {
        const row = document.createElement('div');
        row.className = 'result-row';

        if (item.label) {
          const label = document.createElement('strong');
          label.textContent = `${item.label}:`;
          row.appendChild(label);
        }

        const value = document.createElement('span');
        value.textContent = item.value;
        row.appendChild(value);
        resultBox.appendChild(row);
      });
    }
  }

  function setSolverStatus(isBusy, message = 'Pensando...') {
    if (!solverStatus || !solverStatusText) {
      return;
    }
    solverStatus.classList.toggle('hidden', !isBusy);
    solverStatusText.textContent = message;
    solveButton.disabled = isBusy;
  }

  function setSolveButtonLoading(isLoading) {
    solveButton.classList.toggle('is-loading', isLoading);
    solveButton.disabled = isLoading;

    if (isLoading) {
      solveButton.innerHTML = '<span class="button-spinner" aria-hidden="true"></span><span>Processando...</span>';
      return;
    }

    solveButton.innerHTML = 'Resolver';
  }

  function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `app-toast ${type}`;
    toast.textContent = message;
    toastContainer.appendChild(toast);

    window.setTimeout(() => {
      toast.remove();
    }, 2600);
  }

  function updateInitialStateText(state) {
    initialStateText.textContent = state.join(', ');
  }

  function defaultStateForSize(size) {
    if (size === 4) {
      return [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 0];
    }
    return [1, 2, 3, 4, 5, 6, 7, 0, 8];
  }

  function getSequenceFromPayload(payload) {
    const preferred = Array.isArray(payload.solution) ? payload.solution : [];
    if (preferred.length > 0 || payload.solution === []) {
      return preferred;
    }
    return Array.isArray(payload.best_sequence) ? payload.best_sequence.slice() : [];
  }

  function applyMoveToState(state, move, size) {
    const nextState = state.slice();
    if (!['U', 'D', 'L', 'R'].includes(move)) {
      return nextState;
    }

    const zeroIndex = nextState.indexOf(0);
    const row = Math.floor(zeroIndex / size);
    const col = zeroIndex % size;
    let targetIndex = null;

    if (move === 'U') {
      if (row === 0) {
        return nextState;
      }
      targetIndex = zeroIndex - size;
    } else if (move === 'D') {
      if (row === size - 1) {
        return nextState;
      }
      targetIndex = zeroIndex + size;
    } else if (move === 'L') {
      if (col === 0) {
        return nextState;
      }
      targetIndex = zeroIndex - 1;
    } else if (move === 'R') {
      if (col === size - 1) {
        return nextState;
      }
      targetIndex = zeroIndex + 1;
    }

    if (targetIndex === null) {
      return nextState;
    }

    [nextState[zeroIndex], nextState[targetIndex]] = [
      nextState[targetIndex],
      nextState[zeroIndex],
    ];

    return nextState;
  }

  function updateReplayCounter() {
    const total = playbackState.sequence.length;
    const current = Math.min(playbackState.currentIndex, total);
    replayCounter.textContent = `${current} / ${total}`;
  }

  function updateReplayButtons() {
    const hasSequence = playbackState.sequence.length > 0;
    const isComplete = playbackState.currentIndex >= playbackState.sequence.length;

    replayStartButton.disabled = !hasSequence || playbackState.playing || isComplete;
    replayPauseButton.disabled = !playbackState.playing;
    replayResumeButton.disabled = !hasSequence || playbackState.playing || playbackState.currentIndex === 0;
    replayStepButton.disabled = !hasSequence || isComplete || playbackState.playing;
    replayResetButton.disabled = !hasSequence;
  }

  function stopPlayback() {
    if (playbackState.timerId !== null) {
      clearInterval(playbackState.timerId);
      playbackState.timerId = null;
    }
    playbackState.playing = false;
    updateReplayButtons();
  }

  function stepPlayback() {
    if (!playbackState.sequence.length) {
      stopPlayback();
      return;
    }

    if (playbackState.currentIndex >= playbackState.sequence.length) {
      stopPlayback();
      return;
    }

    const move = playbackState.sequence[playbackState.currentIndex];
    const size = Number(sizeSelect.value);
    playbackState.currentState = applyMoveToState(playbackState.currentState, move, size);
    playbackState.currentIndex += 1;
    buildBoardFromState(playbackState.currentState, size);
    updateReplayCounter();
    updateReplayButtons();

    if (playbackState.currentIndex >= playbackState.sequence.length) {
      stopPlayback();
    }
  }

  function startPlayback() {
    if (!playbackState.sequence.length || playbackState.currentIndex >= playbackState.sequence.length) {
      return;
    }

    stopPlayback();
    playbackState.playing = true;
    updateReplayButtons();

    playbackState.timerId = setInterval(() => {
      stepPlayback();
    }, playbackState.speedMs);
  }

  function resetPlaybackSequence(initialState, sequence) {
    stopPlayback();
    playbackState.sequence = Array.isArray(sequence) ? sequence.slice() : [];
    playbackState.initialState = Array.isArray(initialState) ? initialState.slice() : [];
    playbackState.currentState = playbackState.initialState.slice();
    playbackState.currentIndex = 0;
    buildBoardFromState(playbackState.currentState, Number(sizeSelect.value));
    updateReplayCounter();
    updateReplayButtons();
  }

  function formatStat(value) {
    if (typeof value === 'number' && Number.isFinite(value)) {
      return Number(value).toFixed(3).replace(/\.0+$/, '').replace(/(\.\d*?)0+$/, '$1');
    }
    return '0';
  }

  function renderEvolutionChart(history) {
    const safeHistory = Array.isArray(history) ? history : [];
    const validEntries = safeHistory.filter((entry) => entry && typeof entry === 'object');

    if (!validEntries.length) {
      evolutionChart.innerHTML = `
        <g>
          <text x="340" y="130" text-anchor="middle" fill="#9aa9ba" font-size="16">Sem histórico de evolução disponível</text>
        </g>
      `;
      return;
    }

    const chartWidth = 680;
    const chartHeight = 260;
    const padding = { top: 24, right: 18, bottom: 34, left: 42 };
    const usableHeight = chartHeight - padding.top - padding.bottom;
    const usableWidth = chartWidth - padding.left - padding.right;
    const allFitness = validEntries.flatMap((entry) => [
      Number(entry.best_fitness ?? 0),
      Number(entry.average_fitness ?? 0),
    ]);
    const maxY = allFitness.length ? Math.max(...allFitness, 1) : 1;

    const toX = (index) => {
      if (validEntries.length <= 1) {
        return padding.left + usableWidth / 2;
      }
      return padding.left + (index / (validEntries.length - 1)) * usableWidth;
    };

    const toY = (value) => padding.top + usableHeight - ((value / Math.max(maxY, 1)) * usableHeight);

    const bestPath = validEntries
      .map((entry, index) => `${index === 0 ? 'M' : 'L'} ${toX(index)} ${toY(Number(entry.best_fitness ?? 0))}`)
      .join(' ');

    const averagePath = validEntries
      .map((entry, index) => `${index === 0 ? 'M' : 'L'} ${toX(index)} ${toY(Number(entry.average_fitness ?? 0))}`)
      .join(' ');

    const gridLines = Array.from({ length: 5 }, (_, index) => {
      const y = padding.top + (usableHeight / 4) * index;
      return `<line x1="${padding.left}" y1="${y}" x2="${chartWidth - padding.right}" y2="${y}" stroke="#2f3b4d" stroke-width="1" />`;
    }).join('');

    const markersBest = validEntries.map((entry, index) => {
      const x = toX(index);
      const y = toY(Number(entry.best_fitness ?? 0));
      const fill = entry.partial === true ? '#f3c96b' : '#61a5ff';
      return `<circle cx="${x}" cy="${y}" r="${entry.partial === true ? 4 : 5}" fill="${fill}" stroke="#ebf1f7" stroke-width="1" />`;
    }).join('');

    const markersAverage = validEntries.map((entry, index) => {
      const x = toX(index);
      const y = toY(Number(entry.average_fitness ?? 0));
      const fill = entry.partial === true ? '#f8d981' : '#6dd3a0';
      return `<circle cx="${x}" cy="${y}" r="${entry.partial === true ? 3 : 4}" fill="${fill}" stroke="#ebf1f7" stroke-width="1" />`;
    }).join('');

    evolutionChart.innerHTML = `
      <g>
        ${gridLines}
        <line x1="${padding.left}" y1="${chartHeight - padding.bottom}" x2="${chartWidth - padding.right}" y2="${chartHeight - padding.bottom}" stroke="#51657a" />
        <line x1="${padding.left}" y1="${padding.top}" x2="${padding.left}" y2="${chartHeight - padding.bottom}" stroke="#51657a" />
        <path d="${bestPath}" fill="none" stroke="#61a5ff" stroke-width="2.8" />
        <path d="${averagePath}" fill="none" stroke="#6dd3a0" stroke-width="2" stroke-dasharray="7 5" />
        ${markersBest}
        ${markersAverage}
        <text x="${chartWidth / 2}" y="${chartHeight - 8}" text-anchor="middle" font-size="12" fill="#9aa9ba">Gerações</text>
        <text x="16" y="${chartHeight / 2}" text-anchor="middle" font-size="12" fill="#9aa9ba" transform="rotate(-90 16 ${chartHeight / 2})">Fitness</text>
      </g>
    `;
  }

  function renderEvolutionPanel(history, stopReasonText) {
    const safeHistory = Array.isArray(history) ? history : [];
    const validEntries = safeHistory.filter((entry) => entry && typeof entry === 'object');
    const fullEntries = validEntries.filter((entry) => entry.partial !== true);
    const latestEntry = validEntries.length ? validEntries[validEntries.length - 1] : null;

    if (!validEntries.length) {
      evolutionPanel.classList.remove('hidden');
      generationCount.textContent = '0';
      bestFitness.textContent = '0';
      averageFitness.textContent = '0';
      minManhattan.textContent = '0';
      bestChromosomeLength.textContent = '0';
      distinctIndividuals.textContent = '0';
      stopReason.textContent = stopReasonText || '-';
      renderEvolutionChart([]);
      return;
    }

    const bestEntry = (() => {
      if (!fullEntries.length) {
        return latestEntry;
      }
      return fullEntries.reduce((selected, current) => {
        const currentBest = Number(current.best_fitness ?? Number.NEGATIVE_INFINITY);
        const selectedBest = Number(selected.best_fitness ?? Number.NEGATIVE_INFINITY);
        return currentBest > selectedBest ? current : selected;
      }, fullEntries[0]);
    })();

    const bestFitnessValue = Number(bestEntry?.best_fitness ?? 0);
    const averageFitnessValue = Number(bestEntry?.average_fitness ?? 0);
    const minManhattanValue = Number(bestEntry?.min_manhattan_distance ?? 0);
    const bestChromosomeLengthValue = Number(bestEntry?.best_chromosome_length ?? 0);
    const distinctValue = Number(bestEntry?.distinct_individuals ?? 0);

    generationCount.textContent = String(validEntries.length);
    bestFitness.textContent = formatStat(bestFitnessValue);
    averageFitness.textContent = formatStat(averageFitnessValue);
    minManhattan.textContent = String(minManhattanValue);
    bestChromosomeLength.textContent = String(bestChromosomeLengthValue);
    distinctIndividuals.textContent = String(distinctValue);
    stopReason.textContent = stopReasonText || '-';

    renderEvolutionChart(validEntries);
    evolutionPanel.classList.remove('hidden');
  }

  function renderBoardForCurrentSize() {
    const size = Number(sizeSelect.value);
    const state = defaultStateForSize(size);
    resetPlaybackSequence(state, []);
    buildBoardFromState(state, size);
    updateInitialStateText(state);
    resultBox.classList.add('hidden');
    evolutionPanel.classList.add('hidden');
  }

  function collectSolverParameters() {
    const parseOptionalNumber = (field) => {
      const rawValue = field.value.trim();
      if (rawValue === '') {
        return null;
      }
      const number = Number(rawValue);
      return Number.isFinite(number) ? number : null;
    };

    const payload = {
      population_size: Number(solverParams.populationSize.value),
      initial_chromosome_length: Number(solverParams.initialChromosomeLength.value),
      crossover_rate: Number(solverParams.crossoverRate.value),
      mutation_rate: Number(solverParams.mutationRate.value),
      tournament_size: Number(solverParams.tournamentSize.value),
      elites_count: Number(solverParams.elitesCount.value),
      max_chromosome_length: Number(solverParams.maxChromosomeLength.value),
      max_generations: Number(solverParams.maxGenerations.value),
      time_limit: parseOptionalNumber(solverParams.timeLimit),
      random_seed: parseOptionalNumber(solverParams.randomSeed),
    };

    return payload;
  }

  sizeSelect.addEventListener('change', renderBoardForCurrentSize);

  replaySpeedInput.addEventListener('input', (event) => {
    playbackState.speedMs = Number(event.target.value);
    replaySpeedLabel.textContent = `${playbackState.speedMs} ms`;
    if (playbackState.playing) {
      startPlayback();
    }
  });

  replayStartButton.addEventListener('click', () => {
    if (playbackState.sequence.length && playbackState.currentIndex < playbackState.sequence.length) {
      startPlayback();
    }
  });

  replayPauseButton.addEventListener('click', () => {
    stopPlayback();
  });

  replayResumeButton.addEventListener('click', () => {
    if (playbackState.sequence.length && playbackState.currentIndex < playbackState.sequence.length) {
      startPlayback();
    }
  });

  replayStepButton.addEventListener('click', () => {
    if (playbackState.sequence.length && playbackState.currentIndex < playbackState.sequence.length) {
      stopPlayback();
      stepPlayback();
    }
  });

  replayResetButton.addEventListener('click', () => {
    if (playbackState.initialState.length) {
      playbackState.currentState = playbackState.initialState.slice();
      playbackState.currentIndex = 0;
      buildBoardFromState(playbackState.currentState, Number(sizeSelect.value));
      updateReplayCounter();
      updateReplayButtons();
    }
  });

  randomBoardButton.addEventListener('click', async () => {
    const size = Number(sizeSelect.value);
    try {
      const response = await fetch(`/random?size=${size}`);
      const payload = await response.json();

      if (!response.ok) {
        setResult([{ label: 'Erro', value: payload.error || 'Não foi possível gerar um tabuleiro aleatório.' }], true);
        return;
      }

      const nextState = payload.state.slice();
      buildBoardFromState(nextState, payload.size);
      resetPlaybackSequence(nextState, []);
      updateInitialStateText(nextState);
      resultBox.classList.add('hidden');
    } catch (error) {
      setResult([{ label: 'Erro', value: 'Falha ao gerar tabuleiro aleatório.' }], true);
    }
  });

  solveButton.addEventListener('click', async () => {
    const size = Number(sizeSelect.value);
    const state = normalizeBoardStateFromGrid();

    if (state.length !== size * size) {
      setResult([{ label: 'Erro', value: 'Estado inválido para o tabuleiro selecionado.' }], true);
      showToast('Estado inválido para o tabuleiro.', 'error');
      return;
    }

    setSolveButtonLoading(true);
    setSolverStatus(true, 'Pensando...');
    showToast('Processando solução...', 'info');

    try {
      const response = await fetch('/solve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          size,
          state,
          ...collectSolverParameters(),
        }),
      });

      const payload = await response.json();
      if (!response.ok) {
        setResult([{ label: 'Erro', value: payload.error || 'Não foi possível resolver o puzzle.' }], true);
        setSolverStatus(false, 'Erro');
        setSolveButtonLoading(false);
        showToast(payload.error || 'Não foi possível resolver o puzzle.', 'error');
        return;
      }

      const sequence = getSequenceFromPayload(payload);
      const bestSequence = Array.isArray(payload.best_sequence) ? payload.best_sequence.join(', ') : 'N/A';
      const finalState = Array.isArray(payload.final_state) ? payload.final_state.join(', ') : 'N/A';
      const history = Array.isArray(payload.history) ? payload.history : [];
      const stopReasonText = typeof payload.stop_reason === 'string' ? payload.stop_reason : '-';

      resetPlaybackSequence(state.slice(), sequence);
      buildBoardFromState(state.slice(), size);
      updateInitialStateText(state);
      renderEvolutionPanel(history, stopReasonText);

      setResult([
        { label: 'Estado inicial', value: state.join(', ') },
        { label: 'Resolvido', value: payload.solved ? 'Sim' : 'Não' },
        { label: 'Motivo', value: payload.stop_reason || '-' },
        { label: 'Sequência', value: bestSequence },
        { label: 'Estado final', value: finalState },
        { label: 'Gerações', value: String(payload.generations_run ?? 0) },
      ]);
      setSolverStatus(false, 'Concluído');
      setSolveButtonLoading(false);
      showToast(payload.solved ? 'Cálculo concluído com sucesso.' : 'Busca encerrada sem solução.', payload.solved ? 'success' : 'info');
    } catch (error) {
      setResult([{ label: 'Erro', value: 'Falha ao comunicar com o servidor.' }], true);
      setSolverStatus(false, 'Erro');
      setSolveButtonLoading(false);
      showToast('Falha ao comunicar com o servidor.', 'error');
    }
  });

  replaySpeedLabel.textContent = `${playbackState.speedMs} ms`;
  resultBox.classList.add('hidden');
  renderBoardForCurrentSize();
});

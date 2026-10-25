"""QAP10 instance loading and objective helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class QAPInstance:
    flows: np.ndarray
    distances: np.ndarray
    name: str = "qap10"
    # Optional linear term L[i, j]: extra cost of placing flight i at gate j.
    # Zero for the benchmark; used by LNS subproblems (interaction with fixed flights).
    linear: np.ndarray | None = None

    @property
    def n(self) -> int:
        return int(self.flows.shape[0])

    def subinstance(self, n: int) -> "QAPInstance":
        if not 1 <= n <= self.n:
            raise ValueError(f"N debe estar entre 1 y {self.n}")
        linear = None if self.linear is None else self.linear[:n, :n]
        return QAPInstance(self.flows[:n, :n], self.distances[:n, :n], f"{self.name}-N{n}", linear)

    def cost(self, assignment: tuple[int, ...] | list[int]) -> int:
        """Cost under the challenge convention: each flight pair i < k once."""
        if len(assignment) != self.n or set(assignment) != set(range(self.n)):
            raise ValueError("La asignación debe ser una permutación de las puertas")
        total = sum(
            int(self.flows[i, k]) * int(self.distances[assignment[i], assignment[k]])
            for i in range(self.n)
            for k in range(i + 1, self.n)
        )
        if self.linear is not None:
            total += sum(int(self.linear[i, assignment[i]]) for i in range(self.n))
        return total


def load_qap10() -> QAPInstance:
    path = Path(__file__).resolve().parents[2] / "data" / "qap10_matrices.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    return QAPInstance(np.asarray(raw["flows"], dtype=int), np.asarray(raw["distances"], dtype=int))


EXTENSION_SEED = 20261025
EXTENSION_MAX_N = 14


def extended_qap14() -> QAPInstance:
    """Nested, synthetic extension; the leading 10x10 blocks remain QAP10.

    New flows are independent draws from the 45 original off-diagonal flows
    (including zeros). Gates continue the original four-column Manhattan grid.
    The seed defines the instance, independently of solver seeds and results.
    """
    base = load_qap10()
    n = EXTENSION_MAX_N
    flows = np.zeros((n, n), dtype=int)
    flows[:base.n, :base.n] = base.flows
    population = base.flows[np.triu_indices(base.n, 1)]
    rng = np.random.default_rng(EXTENSION_SEED)
    for k in range(base.n, n):
        for i in range(k):
            flows[i, k] = flows[k, i] = int(rng.choice(population))
    gates = np.arange(n)
    distances = 2 * (abs(gates[:, None] // 4 - gates[None, :] // 4)
                     + abs(gates[:, None] % 4 - gates[None, :] % 4))
    return QAPInstance(flows, distances, "qap10-extension14")


def load_instance(n: int) -> QAPInstance:
    """Original QAP10 up to N=10; nested synthetic extension at N=11..14."""
    base = load_qap10() if n <= 10 else extended_qap14()
    return base.subinstance(n)

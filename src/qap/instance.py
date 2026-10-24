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

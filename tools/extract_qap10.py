"""Recover F and D from MIPLIB's linearized qap10 MPS objective."""

import gzip
import json
from functools import reduce
from math import gcd
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "qap10.mps.gz"
OUTPUT = ROOT / "data" / "qap10_matrices.json"
N = 10


def main() -> None:
    mps = gzip.open(SOURCE, "rt", encoding="ascii").read()
    columns = mps[mps.index("COLUMNS"):mps.index("RHS")]
    row_entries: dict[str, list[tuple[str, float]]] = {}
    variable_rows: dict[str, list[str]] = {}
    y_cost: dict[str, int] = {}
    for line in columns.splitlines():
        fields = line.split()
        if len(fields) < 3 or fields[0] in {"COLUMNS", "INT1", "INT1END"}:
            continue
        variable, row, raw_value = fields[:3]
        value = float(raw_value)
        if row == "NOBJ" and variable.startswith("Y"):
            y_cost[variable] = int(value)
        elif row.startswith("C"):
            row_entries.setdefault(row, []).append((variable, value))
            variable_rows.setdefault(variable, []).append(row)

    terms: dict[tuple[int, int], dict[tuple[int, int], int]] = {}
    for variable, cost in y_cost.items():
        link_rows = variable_rows[variable]
        x_variables = {
            var for row in link_rows for var, value in row_entries[row]
            if var.startswith("X") and value < 0
        }
        if len(x_variables) != 2:
            raise ValueError(f"No pude asociar {variable} a dos variables X")
        a, b = sorted(int(name[1:]) - 1 for name in x_variables)
        i, j = divmod(a, N)
        k, ell = divmod(b, N)
        if i != k and j != ell:
            terms.setdefault((i, k), {})[(j, ell)] = cost

    first_pair = min(terms)
    first_row = terms[first_pair]
    row_gcds = [reduce(gcd, row.values()) for row in terms.values()]
    scale = reduce(gcd, row_gcds)
    first_flow = reduce(gcd, first_row.values()) // scale
    distances = [[0] * N for _ in range(N)]
    for (j, ell), value in first_row.items():
        distances[j][ell] = value // first_flow

    flows = [[0] * N for _ in range(N)]
    for (i, k), row in terms.items():
        flow = reduce(gcd, row.values()) // scale
        if len(row) != len(first_row) or any(
            row[pair] != flow * distances[pair[0]][pair[1]] for pair in first_row
        ):
            raise ValueError(f"Los coeficientes para F[{i},{k}] no separan como F*D")
        flows[i][k] = flows[k][i] = flow

    if any(distances[j][ell] != distances[ell][j]
           for j in range(N) for ell in range(N)):
        raise ValueError("La matriz D recuperada no es simétrica")
    payload = {
        "name": "qap10",
        "source": "https://miplib.zib.de/WebData/instances/qap10.mps.gz",
        "mps_objective_scale": scale,
        "flows": flows,
        "distances": distances,
    }
    OUTPUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Matrices recuperadas en {OUTPUT}; escala global del objetivo MPS: {scale}.")


if __name__ == "__main__":
    main()

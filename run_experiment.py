"""Run the first Track A experiment (classical baseline and optional QAOA)."""

import argparse
import json
from pathlib import Path

from src.qap.classical import solve_exact
from src.qap.instance import load_qap10
from src.qap.qaoa import solve_qaoa


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, default=4, help="subinstancia inicial (3 o 4)")
    parser.add_argument("--qaoa", action="store_true", help="ejecuta el experimento QAOA de Qiskit")
    parser.add_argument("--maxiter", type=int, default=100)
    parser.add_argument("--shots", type=int, default=2048)
    parser.add_argument("--mixer", choices=("x", "xy", "perm"), default="perm",
                        help="x: QAOA estándar; perm: mezclador de intercambio (siempre factible)")
    parser.add_argument("--reps", type=int, default=2, help="profundidad p del QAOA")
    parser.add_argument("--alpha", type=float, default=1.0, help="CVaR alpha (1.0 = valor esperado)")
    parser.add_argument("--seed", type=int, default=1)
    args = parser.parse_args()
    if args.n not in (3, 4):
        parser.error("El primer experimento acepta --n 3 o --n 4")

    instance = load_qap10().subinstance(args.n)
    results = {"track": "A - puertas de embarque", "instance": instance.name,
               "flight_labeling": "benchmark matemático interpretado como vuelos",
               "gate_labeling": "benchmark matemático interpretado como puertas",
               "classical": solve_exact(instance)}
    if args.qaoa:
        results["qaoa"] = solve_qaoa(instance, maxiter=args.maxiter, shots=args.shots,
                                     mixer=args.mixer, reps=args.reps, alpha=args.alpha,
                                     seed=args.seed, resources=True)
    print(json.dumps(results, indent=2, ensure_ascii=False))
    output = Path("results") / f"first_attempt_n{args.n}.json"
    output.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\nResultado guardado en {output}")


if __name__ == "__main__":
    main()

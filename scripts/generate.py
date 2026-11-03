#!/usr/bin/env python3
"""Synthetic assignment. The retention shift is planted here, not estimated."""

import csv
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "src"
N = 20000
SEED = 20261103
# Planted in the generator. The readout is not allowed to treat these as a result.
P_CONTROL = 0.40
P_TREATMENT = 0.42


def write_rows(path, user_id, treat, retained, revenue):
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["user_id", "arm", "retained", "revenue"])
        for i in range(len(user_id)):
            arm = "treatment" if treat[i] else "control"
            writer.writerow([int(user_id[i]), arm, int(retained[i]), "%.10f" % float(revenue[i])])


def main():
    rng = np.random.default_rng(SEED)
    user_id = np.arange(N)
    treat = rng.random(N) < 0.5
    retained = rng.random(N) < np.where(treat, P_TREATMENT, P_CONTROL)
    revenue = rng.lognormal(1.2, 0.5, size=N)
    OUT.mkdir(parents=True, exist_ok=True)
    write_rows(OUT / "units.csv", user_id, treat, retained, revenue)
    # A separate stream, so the clean file does not depend on the broken one.
    hole = treat & (np.random.default_rng(SEED + 1).random(N) < 0.10)
    keep = ~hole
    write_rows(
        OUT / "units_broken.csv",
        user_id[keep],
        treat[keep],
        retained[keep],
        revenue[keep],
    )
    print("generated", N, "broken", int(keep.sum()))


if __name__ == "__main__":
    main()

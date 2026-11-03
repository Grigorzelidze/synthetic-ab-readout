#!/usr/bin/env python3
"""Second calculation. Pandas reads the CSV; SQL is the mart dbt just built."""

import csv
import json
import math
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "src" / "units.csv"
COUNTS_PATH = ROOT / "dashboard" / "data" / "counts.json"
CHI2_LIMIT = 10.827


def chi2(n0, n1):
    total = float(n0 + n1)
    expected = total / 2.0
    return (n0 - expected) ** 2 / expected + (n1 - expected) ** 2 / expected


def frame_counts(frame):
    out = {}
    for arm, part in frame.groupby("arm", sort=True):
        out[arm] = {
            "n": int(len(part)),
            "n_retained": int(part["retained"].sum()),
            "mean_revenue": float(part["revenue"].mean()),
            "sd_revenue": float(part["revenue"].std(ddof=1)),
        }
    early = frame[frame["user_id"] < 2000]
    early_out = {}
    for arm, part in early.groupby("arm", sort=True):
        early_out[arm] = {
            "n": int(len(part)),
            "n_retained": int(part["retained"].sum()),
        }
    return {"arms": out, "early": early_out, "chi2": chi2(out["control"]["n"], out["treatment"]["n"])}


def query_sql():
    def run(sql):
        proc = subprocess.run(
            ["psql", "-v", "ON_ERROR_STOP=1", "--csv", "-c", sql],
            check=True,
            text=True,
            capture_output=True,
        )
        return list(csv.DictReader(proc.stdout.splitlines()))

    arms = {}
    for row in run(
        "select arm, n, n_retained, mean_revenue, sd_revenue from mart.by_arm order by arm"
    ):
        arms[row["arm"]] = {
            "n": int(row["n"]),
            "n_retained": int(row["n_retained"]),
            "mean_revenue": float(row["mean_revenue"]),
            "sd_revenue": float(row["sd_revenue"]),
        }
    early = {}
    for row in run("select arm, n, n_retained from mart.early order by arm"):
        early[row["arm"]] = {"n": int(row["n"]), "n_retained": int(row["n_retained"])}
    return {
        "arms": arms,
        "early": early,
        "chi2": chi2(arms["control"]["n"], arms["treatment"]["n"]),
    }


def compare(sql_facts, py_facts):
    for arm in ("control", "treatment"):
        for key in ("n", "n_retained"):
            if sql_facts["arms"][arm][key] != py_facts["arms"][arm][key]:
                raise SystemExit("arms %s %s disagree" % (arm, key))
            if sql_facts["early"][arm][key] != py_facts["early"][arm][key]:
                raise SystemExit("early %s %s disagree" % (arm, key))
        if not math.isclose(
            sql_facts["arms"][arm]["mean_revenue"],
            py_facts["arms"][arm]["mean_revenue"],
            abs_tol=1e-4,
        ):
            raise SystemExit("mean revenue disagrees for %s" % arm)
        if not math.isclose(
            sql_facts["arms"][arm]["sd_revenue"],
            py_facts["arms"][arm]["sd_revenue"],
            abs_tol=1e-4,
        ):
            raise SystemExit("revenue sd disagrees for %s" % arm)
    if sql_facts["chi2"] > CHI2_LIMIT:
        raise SystemExit("clean assignment failed the SRM limit")


def dump(facts):
    stored = {
        "chi2": round(facts["chi2"], 4),
        "arms": {},
        "early": facts["early"],
    }
    for arm, row in facts["arms"].items():
        stored["arms"][arm] = {
            "n": row["n"],
            "n_retained": row["n_retained"],
            "mean_revenue": round(row["mean_revenue"], 6),
            "sd_revenue": round(row["sd_revenue"], 6),
        }
    COUNTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    COUNTS_PATH.write_text(
        json.dumps(stored, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main():
    frame = pd.read_csv(CSV_PATH)
    if len(frame) != 20000:
        raise SystemExit("row count is %s, expected 20000" % len(frame))
    sql_facts = query_sql()
    compare(sql_facts, frame_counts(frame))
    dump(sql_facts)
    print("recompute ok", COUNTS_PATH)


if __name__ == "__main__":
    sys.exit(main() or 0)

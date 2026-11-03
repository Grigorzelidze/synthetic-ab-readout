#!/usr/bin/env python3
"""The broken assignment must fail dbt. The clean file is restored after."""

import os
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CHI2_LIMIT = 10.827


def chi2(n0, n1):
    total = float(n0 + n1)
    expected = total / 2.0
    return (n0 - expected) ** 2 / expected + (n1 - expected) ** 2 / expected


def dbt_on_path():
    if subprocess.call(["sh", "-c", "command -v dbt >/dev/null 2>&1"]) == 0:
        return
    user_bin = subprocess.check_output(
        [sys.executable, "-c", "import site; print(site.getuserbase() + '/bin')"],
        text=True,
    ).strip()
    os.environ["PATH"] = user_bin + os.pathsep + os.environ.get("PATH", "")


def psql_copy(path):
    cleared = subprocess.run(
        ["psql", "-v", "ON_ERROR_STOP=1", "-c", "TRUNCATE raw.unit"],
        text=True,
        capture_output=True,
    )
    if cleared.returncode != 0:
        raise SystemExit(cleared.stderr)
    loaded = subprocess.run(
        [
            "psql",
            "-v",
            "ON_ERROR_STOP=1",
            "-c",
            "\\copy raw.unit FROM '%s' WITH (FORMAT csv, HEADER true)" % path,
        ],
        text=True,
        capture_output=True,
    )
    if loaded.returncode != 0:
        raise SystemExit(loaded.stderr)


def dbt_build():
    env = os.environ.copy()
    env["DBT_PROFILES_DIR"] = str(ROOT)
    env["DBT_SEND_ANONYMOUS_USAGE_STATS"] = "false"
    return subprocess.run(
        ["dbt", "build", "--project-dir", str(ROOT), "--profiles-dir", str(ROOT)],
        cwd=str(ROOT),
        env=env,
        text=True,
        capture_output=True,
    )


def chi2_file(path):
    frame = pd.read_csv(path)
    n0 = int((frame["arm"] == "control").sum())
    n1 = int((frame["arm"] == "treatment").sum())
    return chi2(n0, n1)


def main():
    dbt_on_path()
    clean = ROOT / "data" / "src" / "units.csv"
    broken = ROOT / "data" / "src" / "units_broken.csv"
    if chi2_file(clean) > CHI2_LIMIT:
        raise SystemExit("clean file is already unbalanced")
    if chi2_file(broken) <= CHI2_LIMIT:
        raise SystemExit("broken file did not trip the SRM limit")
    psql_copy(broken)
    failed = dbt_build()
    if failed.returncode == 0:
        psql_copy(clean)
        dbt_build()
        raise SystemExit("broken assignment did not fail dbt build")
    psql_copy(clean)
    restored = dbt_build()
    if restored.returncode != 0:
        raise SystemExit(restored.stderr)
    print("srm ok")


if __name__ == "__main__":
    main()

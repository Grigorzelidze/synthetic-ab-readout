#!/usr/bin/env python3
"""Fill README.md and index.html from the mart counts. The interval is not in SQL."""

import json
import math
import sys
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COUNTS = ROOT / "dashboard" / "data" / "counts.json"
README_IN = ROOT / "README.md.in"
README = ROOT / "README.md"
PAGE = ROOT / "index.html"


def proportion_diff(treated, control):
    p1 = treated["n_retained"] / float(treated["n"])
    p0 = control["n_retained"] / float(control["n"])
    se = math.sqrt(p1 * (1.0 - p1) / treated["n"] + p0 * (1.0 - p0) / control["n"])
    diff = p1 - p0
    return diff, diff - 1.96 * se, diff + 1.96 * se


def revenue_diff(treated, control):
    diff = treated["mean_revenue"] - control["mean_revenue"]
    se = math.sqrt(
        treated["sd_revenue"] ** 2 / treated["n"] + control["sd_revenue"] ** 2 / control["n"]
    )
    return diff, diff - 1.96 * se, diff + 1.96 * se


def pp(value, places="0.1"):
    number = (Decimal(str(value)) * Decimal(100)).quantize(Decimal(places), rounding=ROUND_HALF_UP)
    return format(number, "f").replace(".", ",")


def money(value):
    number = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return format(number, "f").replace(".", ",")


def covers_zero(lo, hi):
    return lo <= 0.0 <= hi


def note_retention(lo, hi, early=False):
    subject = "На первых 2000 идентификаторах интервал удержания" if early else "Интервал удержания"
    if covers_zero(lo, hi):
        return subject + " включает ноль: этот срез сдвиг не отделяет."
    if lo > 0:
        return subject + " лежит выше нуля."
    return subject + " лежит ниже нуля."


def bar(label, rate):
    width = format(Decimal(str(rate * 100)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP), "f")
    shown = pp(rate)
    return (
        '<div class="bar-row"><span class="bar-label">%s</span>'
        '<span class="bar-track"><span class="bar-fill" style="width: %s%%"></span></span>'
        '<span class="bar-value">%s%%</span></div>' % (label, width, shown)
    )


def render(facts):
    control = facts["arms"]["control"]
    treated = facts["arms"]["treatment"]
    early_c = facts["early"]["control"]
    early_t = facts["early"]["treatment"]
    diff, lo, hi = proportion_diff(treated, control)
    early_diff, early_lo, early_hi = proportion_diff(early_t, early_c)
    rev_diff, rev_lo, rev_hi = revenue_diff(treated, control)
    rev = {"diff": rev_diff, "lo": rev_lo, "hi": rev_hi}
    tokens = {
        "@@N0@@": str(control["n"]),
        "@@N1@@": str(treated["n"]),
        "@@RET0@@": pp(control["n_retained"] / float(control["n"])),
        "@@RET1@@": pp(treated["n_retained"] / float(treated["n"])),
        "@@LIFT@@": pp(diff),
        "@@LIFT_LO@@": pp(lo),
        "@@LIFT_HI@@": pp(hi),
        "@@RET_NOTE@@": note_retention(lo, hi),
        "@@EARLY_LIFT@@": pp(early_diff),
        "@@EARLY_LO@@": pp(early_lo),
        "@@EARLY_HI@@": pp(early_hi),
        "@@EARLY_NOTE@@": note_retention(early_lo, early_hi, early=True),
        "@@REV0@@": money(control["mean_revenue"]),
        "@@REV1@@": money(treated["mean_revenue"]),
        "@@REV_DIFF@@": money(rev["diff"]),
        "@@REV_LO@@": money(rev["lo"]),
        "@@REV_HI@@": money(rev["hi"]),
        "@@REV_NOTE@@": (
            "Интервал средней выручки включает ноль. Это не доказательство, что выручка не сдвинулась: выборка такого сдвига не отделила."
            if covers_zero(rev["lo"], rev["hi"])
            else "Интервал средней выручки не включает ноль."
        ),
        "@@CHI2@@": str(facts["chi2"]).replace(".", ","),
        "@@BARS@@": bar("control", control["n_retained"] / float(control["n"]))
        + bar("treatment", treated["n_retained"] / float(treated["n"])),
    }
    readme = README_IN.read_text(encoding="utf-8")
    page = (ROOT / "index.html.in").read_text(encoding="utf-8")
    for key, value in tokens.items():
        readme = readme.replace(key, value)
        page = page.replace(key, value)
    return readme, page


def main():
    facts = json.loads(COUNTS.read_text(encoding="utf-8"))
    readme, page = render(facts)
    if "--check" in sys.argv:
        stale = []
        if not README.exists() or README.read_text(encoding="utf-8") != readme:
            stale.append("README.md")
        if not PAGE.exists() or PAGE.read_text(encoding="utf-8") != page:
            stale.append("index.html")
        if stale:
            raise SystemExit("out of date: " + ", ".join(stale))
        print("check ok")
        return
    README.write_text(readme, encoding="utf-8")
    PAGE.write_text(page, encoding="utf-8")
    print("rendered")


if __name__ == "__main__":
    main()

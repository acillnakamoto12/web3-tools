#!/usr/bin/env python3
"""funding.py — search and list crypto funding rounds from data/funding.json.

The data file is a verified snapshot (24 Nov 2026) of rounds announced
2–21 Nov 2026; see data/funding.json for sources. This tool only reads and
filters that file — it fetches nothing from the internet.

Usage:
    python funding.py                        # all rounds, biggest first
    python funding.py --min-amount 10000000 # rounds of $10M+
    python funding.py --round "Series B"     # only Series B
    python funding.py --search tether        # rounds mentioning Tether
    python funding.py --sort date            # oldest first
    python funding.py --total                # print the disclosed total
    python funding.py --json                 # print raw JSON
"""

import argparse
import json
import sys
from pathlib import Path

DEFAULT_DATA = Path(__file__).resolve().parent.parent / "data" / "funding.json"


def load_rounds(data_path=DEFAULT_DATA):
    with open(data_path, encoding="utf-8") as fh:
        data = json.load(fh)
    return data


def filter_rounds(rounds, min_amount=None, round_type=None, search=None):
    out = list(rounds)
    if min_amount is not None:
        out = [r for r in out if (r.get("amount_usd") or 0) >= min_amount]
    if round_type:
        out = [r for r in out if r.get("round", "").lower() == round_type.lower()]
    if search:
        q = search.lower()
        out = [
            r
            for r in out
            if q
            in " ".join(
                [
                    r.get("project", ""),
                    r.get("lead_investor", ""),
                    r.get("category", ""),
                    r.get("round", ""),
                    " ".join(r.get("investors", [])),
                    r.get("description", ""),
                ]
            ).lower()
        ]
    return out


def sort_rounds(rounds, sort="amount"):
    if sort == "date":
        return sorted(rounds, key=lambda r: r.get("date", ""))
    if sort == "date-desc":
        return sorted(rounds, key=lambda r: r.get("date", ""), reverse=True)
    return sorted(rounds, key=lambda r: r.get("amount_usd") or 0, reverse=True)


def fmt_amount(n):
    if n is None:
        return "Undisclosed"
    if n >= 1_000_000_000:
        return f"${n / 1e9:g}B"
    if n >= 1_000_000:
        return f"${n / 1e6:g}M"
    if n >= 1_000:
        return f"${n / 1e3:g}K"
    return f"${n:,}"


def render_table(rounds):
    rows = [
        (r["project"], r["date"], r["round"], fmt_amount(r.get("amount_usd")),
         r.get("category", "—"), r.get("lead_investor", "—"))
        for r in rounds
    ]
    headers = ("Project", "Date", "Round", "Amount", "Category", "Lead investor")
    widths = [max(len(str(c)) for c in col) for col in zip(headers, *rows)] if rows else [len(h) for h in headers]
    fmt = "  ".join(f"{{:<{w}}}" for w in widths)
    lines = [fmt.format(*headers), fmt.format(*["-" * w for w in widths])]
    lines += [fmt.format(*row) for row in rows]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description="List crypto funding rounds (snapshot data).")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA, help="path to funding.json")
    parser.add_argument("--min-amount", type=float, default=None, help="minimum round size in USD")
    parser.add_argument("--round", default=None, help="filter by round type, e.g. 'Series B'")
    parser.add_argument("--search", default=None, help="free-text search")
    parser.add_argument("--sort", choices=["amount", "date", "date-desc"], default="amount")
    parser.add_argument("--total", action="store_true", help="print the disclosed total and exit")
    parser.add_argument("--json", action="store_true", help="print raw JSON")
    args = parser.parse_args(argv)

    try:
        data = load_rounds(args.data)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"error: cannot read {args.data}: {exc}", file=sys.stderr)
        return 1

    rounds = data["rounds"]
    if args.total:
        total = sum(r.get("amount_usd") or 0 for r in rounds)
        print(f"Disclosed total across {len(rounds)} rounds: {fmt_amount(total)} "
              f"(${total:,}) — snapshot {data.get('snapshot_date')}")
        return 0

    rounds = filter_rounds(rounds, args.min_amount, args.round, args.search)
    rounds = sort_rounds(rounds, args.sort)
    if args.json:
        print(json.dumps(rounds, indent=2))
    elif not rounds:
        print("No rounds match.")
    else:
        print(render_table(rounds))
        print(f"\n{len(rounds)} round(s) — snapshot {data.get('snapshot_date')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

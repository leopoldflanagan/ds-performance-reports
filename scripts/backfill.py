#!/usr/bin/env python3
"""Computes a release that closed before this repository existed.

The refresh job measures the period in progress and freezes it when it closes.
That is enough forever after, and no help at all on day one: a team whose
reporting starts in September has four closed releases behind it that nothing
ever measured, and they cannot be invented -- only read back out of Jira.

This does that, once per release, and writes the result into frozen.json in
exactly the shape the freeze step would have written it. After that the release
is history: it is never recomputed, and a later run leaves it alone.

    python3 scripts/backfill.py --team DS --board 257 --project DS 9.04 9.05

It refuses to overwrite a release that already carries figures unless --force is
given, so running it twice cannot quietly change a number somebody has already
read.
"""
import argparse, importlib.util, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_spec = importlib.util.spec_from_file_location(
    "fetch_jira", os.path.join(ROOT, "scripts", "fetch_jira.py"))
fj = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fj)          # exits by itself if the credentials are missing


def _ordered(rows, by_period):
    order = [n for ns in by_period.values() for n in ns]
    pos = {n: i for i, n in enumerate(order)}
    return sorted(rows, key=lambda r: pos.get(r[0], len(pos)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--team", required=True)
    ap.add_argument("--board", type=int, required=True)
    ap.add_argument("--project", required=True)
    ap.add_argument("--frozen", default=os.path.join(ROOT, "data", "frozen.json"))
    ap.add_argument("--force", action="store_true",
                    help="recompute a release that already has figures")
    ap.add_argument("releases", nargs="*",
                    help="release keys, e.g. 9.04 9.05. With none given, every "
                         "closed release that has never been measured.")
    a = ap.parse_args()

    D = json.load(open(a.frozen))
    REL = D.get("RELEASES") or {}

    # No list given means: whatever is still unmeasured. The job knows which those
    # are -- it prints them on every run -- so making a person type them in was
    # asking for a step that gets skipped, mistyped, or lost in a re-run.
    targets = a.releases or [k for k, v in sorted(REL.items())
                             if v.get("closed") is None and not v.get("open")]
    if not targets:
        print("backfill: every closed release is already measured")
        return
    mine = [s for s in fj.sprints(a.board) if s.get("startDate")
            and s["name"].upper().startswith(a.team.upper())]

    for rk in targets:
        r = REL.get(rk)
        if not r:
            sys.exit(f"{rk} is not in RELEASES: add its window and sprints first")
        if r.get("closed") and not a.force:
            print(f"{rk}: already has figures, skipping (use --force to recompute)")
            continue
        if r.get("open"):
            print(f"{rk}: still open, the refresh job measures it -- skipping")
            continue

        blk = fj.month_block(a.board, a.project, a.team, mine, rk,
                             window=(r["start"], r["end"]),
                             sprint_names=r["sprints"],
                             label=f"Release {rk}")
        m = blk["month"]
        keep = {k: r[k] for k in ("slug", "label", "short", "sprints", "n_sprints",
                                  "weeks") if k in r}
        REL[rk] = {**m, **keep, "open": False,
                   "per_sprint": round(m["closed"] / max(1, keep.get("n_sprints", 1)), 1)}
        D.setdefault("CAP_R", {})[rk] = list(blk["CAP"].values())[0]
        D.setdefault("CYC_R", {})[rk] = list(blk["CYC"].values())[0]
        D.setdefault("SP_BY_RELEASE", {})[rk] = r["sprints"]
        D.setdefault("RELEASE_LABEL", {})[rk] = "R" + rk

        have = {x[0] for x in D.get("SPRINTS", [])}
        D.setdefault("SPRINTS", []).extend(
            [row for row in blk["SPRINTS"] if row[0] not in have])
        D["SPRINTS"] = _ordered(D["SPRINTS"], D["SP_BY_RELEASE"])
        for key in ("SPILL", "SPLIT", "TIS", "GHOST"):
            D.setdefault(key, {}).update(blk.get(key) or {})

        href = REL[rk]["slug"] + ".html"
        D.setdefault("INDEX", {})[href] = {
            "short": REL[rk]["short"],
            "title": f"{REL[rk]['label']} Performance Report",
            "badge": "Pending review",
            "blurb": m["headline"]}
        entry = [REL[rk]["short"], href]
        if entry not in D.setdefault("REPORTS", []):
            D["REPORTS"].append(entry)

        print(f"{rk}: {m['closed']} closed, {m['discarded']} discarded, "
              f"{len(blk['SPRINTS'])} sprint(s), cycle time median "
              f"{list(blk['CYC'].values())[0]['med']}d")

    D["REPORTS"] = sorted(D["REPORTS"], key=lambda e: e[0], reverse=True)
    with open(a.frozen, "w") as f:
        json.dump(D, f, indent=1, ensure_ascii=False)
    print(f"{a.frozen}: {len(REL)} release(s) on file")


if __name__ == "__main__":
    main()

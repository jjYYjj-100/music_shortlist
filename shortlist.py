import argparse
import csv
import json
import sqlite3
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SELECTION_WEEK = "2026-11-13"
OUTCOME_WEEK = "2026-11-20"
BUDGET = 3

QUERIES = {
    "momentum": """
        SELECT title, artist, rank, last_rank, last_rank - rank AS gain
        FROM candidates
        WHERE rank BETWEEN 21 AND 35 AND last_rank > rank
        ORDER BY gain DESC, rank ASC
        LIMIT ?
    """,
    "popularity": """
        SELECT title, artist, rank, last_rank, last_rank - rank AS gain
        FROM candidates
        WHERE rank BETWEEN 21 AND 35
        ORDER BY rank ASC
        LIMIT ?
    """,
}


def load_candidates():
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.execute("""
        CREATE TABLE candidates (
            rank INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            artist TEXT NOT NULL,
            last_rank INTEGER
        )
    """)
    with (HERE / "candidates.csv").open(encoding="utf-8", newline="") as source:
        db.executemany(
            "INSERT INTO candidates VALUES (?, ?, ?, ?)",
            (
                (int(row["rank"]), row["title"], row["artist"],
                 int(row["last_rank"]) if row["last_rank"] else None)
                for row in csv.DictReader(source)
            ),
        )
    return db


def select_candidates(db, strategy="momentum", limit=BUDGET):
    if type(limit) is not int or not 1 <= limit <= BUDGET:
        raise ValueError(f"limit must be an integer from 1 to {BUDGET}")
    return [dict(row) for row in db.execute(QUERIES[strategy], (limit,))]


def get_shortlist(week=SELECTION_WEEK, limit=BUDGET):
    if week != SELECTION_WEEK:
        raise ValueError(f"Only the week starting {SELECTION_WEEK} is available")
    with load_candidates() as db:
        return {"week": week, "chart_rank_range": [21, 35],
                "candidates": select_candidates(db, limit=limit)}


def load_outcomes():
    with (HERE / "outcomes.csv").open(encoding="utf-8", newline="") as source:
        rows = list(csv.DictReader(source))
    if {int(row["next_rank"]) for row in rows} != set(range(1, 21)) or len(rows) != 20:
        raise ValueError("Evaluation requires the complete next-week Top 20")
    return {
        int(row["selection_week_rank"]): int(row["next_rank"])
        for row in rows if row["selection_week_rank"]
    }


def evaluate():
    outcomes = load_outcomes()
    report = {"selection_week": SELECTION_WEEK, "outcome_week": OUTCOME_WEEK,
              "review_budget": BUDGET, "target": "next-week Top 20"}
    with load_candidates() as db:
        for strategy in QUERIES:
            picks = select_candidates(db, strategy)
            for pick in picks:
                pick["next_top20_rank"] = outcomes.get(pick["rank"])
            hits = sum(pick["next_top20_rank"] is not None for pick in picks)
            report[strategy] = {"hits": hits, "selected": len(picks),
                                "hits_per_review_slot": hits / BUDGET,
                                "candidates": picks}
    return report


class ShortlistTests(unittest.TestCase):
    def test_frozen_chart_order(self):
        self.assertEqual([r["rank"] for r in get_shortlist()["candidates"]], [22, 29, 23])

    def test_gain_is_computed_from_source_ranks(self):
        self.assertEqual([r["gain"] for r in get_shortlist()["candidates"]], [32, 22, 13])

    def test_limit_is_respected(self):
        self.assertEqual(len(get_shortlist(limit=1)["candidates"]), 1)

    def test_invalid_budget(self):
        for limit in (0, 4, True, "3"):
            with self.subTest(limit=limit), self.assertRaises(ValueError):
                get_shortlist(limit=limit)

    def test_unknown_week(self):
        with self.assertRaises(ValueError):
            get_shortlist(week="2026-11-20")

    def test_ties_missing_rank_and_outside_pool(self):
        with load_candidates() as db:
            db.execute("DELETE FROM candidates")
            db.executemany("INSERT INTO candidates VALUES (?, ?, ?, ?)", [
                (20, "Outside", "Test", 40), (21, "Missing", "Test", None),
                (22, "First", "Test", 27), (23, "Second", "Test", 28),
                (24, "Down", "Test", 23),
            ])
            self.assertEqual([row["rank"] for row in select_candidates(db)], [22, 23])

    def test_next_week_ground_truth(self):
        report = evaluate()
        self.assertEqual(
            [pick["next_top20_rank"] for pick in report["momentum"]["candidates"]],
            [12, 19, 17],
        )
        self.assertEqual(report["momentum"]["hits"], 3)
        self.assertEqual(report["popularity"]["hits"], 2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("recommend", "evaluate", "test"))
    parser.add_argument("--week", default=SELECTION_WEEK)
    parser.add_argument("--limit", type=int, default=BUDGET)
    args = parser.parse_args()
    if args.action == "test":
        unittest.main(argv=["shortlist.py"], verbosity=2)
    else:
        try:
            result = get_shortlist(args.week, args.limit) if args.action == "recommend" else evaluate()
        except ValueError as error:
            parser.error(str(error))
        print(json.dumps(result, ensure_ascii=False, indent=2))

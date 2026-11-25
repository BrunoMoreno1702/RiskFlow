"""CLI do pipeline.

    python -m pipeline.run init-db
    python -m pipeline.run daily --date 2026-11-01
    python -m pipeline.run backfill --start 2026-08-01 --end 2026-10-31
    python -m pipeline.run train
    python -m pipeline.run score --date 2026-11-01
"""

from __future__ import annotations

import argparse
import logging
from datetime import date, timedelta

from ml.model import ModelNotTrainedError
from pipeline import config, db, steps

log = logging.getLogger("riskflow")


def run_day(day: date) -> None:
    steps.extract_and_load_raw(day)
    steps.stage(day)
    steps.build_mart(day)
    try:
        steps.score(day)
    except ModelNotTrainedError:
        log.warning("Sem modelo treinado: scoring de %s ignorado.", day)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(prog="pipeline.run")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init-db")
    daily = sub.add_parser("daily")
    daily.add_argument("--date", type=date.fromisoformat, required=True)
    backfill = sub.add_parser("backfill")
    backfill.add_argument("--start", type=date.fromisoformat, required=True)
    backfill.add_argument("--end", type=date.fromisoformat, required=True)
    sub.add_parser("train")
    score = sub.add_parser("score")
    score.add_argument("--date", type=date.fromisoformat, required=True)

    args = parser.parse_args()

    if args.command == "init-db":
        with db.connect() as conn:
            db.apply_schema(conn)
    elif args.command == "daily":
        run_day(args.date)
    elif args.command == "backfill":
        # Dias em ordem: as features de cada dia dependem do historico dos anteriores.
        day = args.start
        while day <= args.end:
            run_day(day)
            day += timedelta(days=1)
    elif args.command == "train":
        from ml.train import train_from_mart

        metadata = train_from_mart(config.ARTIFACTS_DIR)
        log.info("Metricas de teste: %s", metadata["test_metrics"])
    elif args.command == "score":
        steps.score(args.date)


if __name__ == "__main__":
    main()

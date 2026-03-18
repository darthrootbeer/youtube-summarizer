from __future__ import annotations

import argparse
import sys

from youtube_summarizer.run import run_once


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="youtube-summarizer")
    sub = parser.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("run", help="Check channels and email new summaries")
    run.add_argument("--limit", type=int, default=10, help="Max new videos per run")
    run.add_argument("--dry-run", action="store_true", help="Do not send email or mark videos as seen")

    args = parser.parse_args(argv)

    if args.cmd == "run":
        if args.dry_run:
            # Ensure settings loader sees dry-run even without .env.
            import os

            os.environ["YTS_DRY_RUN"] = "1"
        run_once(limit=args.limit)
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))


from __future__ import annotations

import argparse
import os
import sys

from youtube_summarizer.run import run_forever, run_once, setup_logging


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="youtube-summarizer")
    sub = parser.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("run", help="Check channels and email new summaries")
    run.add_argument("--limit", type=int, default=10, help="Max new videos per run")
    run.add_argument("--dry-run", action="store_true", help="Do not send email or mark videos as seen")
    run.add_argument("--debug", action="store_true", help="Enable debug logging (same as YTS_LOG_LEVEL=DEBUG)")

    watch = sub.add_parser("watch", help="Continuously poll and process new videos")
    watch.add_argument("--poll-seconds", type=int, default=900, help="Sleep duration when no new work is found")
    watch.add_argument("--limit", type=int, default=10, help="Max new videos per polling cycle")
    watch.add_argument("--debug", action="store_true", help="Enable debug logging (same as YTS_LOG_LEVEL=DEBUG)")

    args = parser.parse_args(argv)

    if getattr(args, "debug", False):
        os.environ["YTS_LOG_LEVEL"] = "DEBUG"

    if args.cmd == "run":
        if args.dry_run:
            os.environ["YTS_DRY_RUN"] = "1"
        run_once(limit=args.limit)
        return 0

    if args.cmd == "watch":
        run_forever(poll_seconds=args.poll_seconds, limit=args.limit)
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

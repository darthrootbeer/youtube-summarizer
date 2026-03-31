from __future__ import annotations

import argparse
import os
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="youtube-summarizer")
    sub = parser.add_subparsers(dest="cmd", required=True)

    run_cmd = sub.add_parser("run", help="Check channels and email new summaries")
    run_cmd.add_argument("--limit", type=int, default=10, help="Max new videos per run")
    run_cmd.add_argument("--dry-run", action="store_true", help="Do not send email")
    run_cmd.add_argument("--debug", action="store_true", help="Enable debug logging")

    watch_cmd = sub.add_parser("watch", help="Continuously poll and process new videos")
    watch_cmd.add_argument("--poll-seconds", type=int, default=900, help="Sleep between polls")
    watch_cmd.add_argument("--limit", type=int, default=10, help="Max new videos per cycle")
    watch_cmd.add_argument("--debug", action="store_true", help="Enable debug logging")

    test_email_cmd = sub.add_parser("test-email", help="Send a test email to verify SMTP works")
    test_email_cmd.add_argument("--debug", action="store_true", help="Enable debug logging")

    retry_cmd = sub.add_parser("retry-failed", help="List and retry failed videos")
    retry_cmd.add_argument("--debug", action="store_true", help="Enable debug logging")

    force_cmd = sub.add_parser("force", help="Force-process a video by ID, bypassing seen check")
    force_cmd.add_argument("video_id", help="YouTube video ID (e.g. 5I5Y6fVSqrk)")
    force_cmd.add_argument("--dry-run", action="store_true", help="Process but do not send email")
    force_cmd.add_argument("--debug", action="store_true", help="Enable debug logging")

    args = parser.parse_args(argv)

    if getattr(args, "debug", False):
        os.environ["YTS_LOG_LEVEL"] = "DEBUG"

    if args.cmd == "run":
        from youtube_summarizer.pipeline import run_once
        run_once(limit=args.limit, dry_run=args.dry_run, debug=args.debug)
        return 0

    if args.cmd == "watch":
        from youtube_summarizer.pipeline import run_forever
        run_forever(poll_seconds=args.poll_seconds, limit=args.limit, debug=args.debug)
        return 0

    if args.cmd == "test-email":
        from youtube_summarizer.config import load_dotenv, load_settings, repo_root
        from youtube_summarizer.emailer import EmailContent, send_gmail_smtp
        load_dotenv(repo_root() / ".env")
        settings = load_settings()
        send_gmail_smtp(
            email_from=settings.email_from,
            email_to=settings.email_to,
            gmail_app_password=settings.gmail_app_password,
            content=EmailContent(
                subject=f"{settings.subject_prefix}Test Email",
                text="This is a test email from youtube-summarizer v2.",
                html="<p>This is a test email from youtube-summarizer v2.</p>",
            ),
        )
        print("Test email sent successfully.")
        return 0

    if args.cmd == "force":
        from youtube_summarizer.pipeline import force_process_video
        force_process_video(args.video_id, dry_run=args.dry_run, debug=args.debug)
        return 0

    if args.cmd == "retry-failed":
        from youtube_summarizer import db
        from youtube_summarizer.config import load_dotenv, load_settings, repo_root
        load_dotenv(repo_root() / ".env")
        settings = load_settings()
        conn = db.connect(settings.data_dir)
        failed = db.get_failed(conn)
        if not failed:
            print("No failed videos.")
            return 0
        print(f"Found {len(failed)} failed video(s):")
        for f in failed:
            print(f"  {f['video_id']}: {f['video_title']} — {f['error']}")
        conn.close()
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

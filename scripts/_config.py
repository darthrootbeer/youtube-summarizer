#!/usr/bin/env python3
"""
Config manipulation helper for manage.sh.
All TOML reads/writes go through here so the bash script stays clean.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CHANNELS_TOML = REPO_ROOT / "config" / "channels.toml"
PROMPTS_DIR = REPO_ROOT / "config" / "prompts"
TRANSCRIBE_MD = REPO_ROOT / "config" / "transcribe.md"

TRANSCRIBE_OPTION_DESCRIPTIONS = {
    "remove_fillers":          "Remove um, uh, kind of, you know, and similar speech fillers",
    "questions_own_paragraph": "Put questions on their own paragraph (good for Q&A videos)",
    "robust_sentence_breaks":  "Add paragraph breaks at sentence boundaries",
    "qa_paragraph_breaks":     "Detect Q&A intro patterns and force paragraph breaks",
    "split_long_clauses":      "Split long compound sentences at natural clause boundaries",
    "strip_stage_directions":  "Remove [music], [applause], and similar markers",
    "normalize_numbers":       "Normalize spoken numbers (twenty one → 21)",
    "speaker_labels":          "Attempt to label speakers (high hallucination risk)",
}

TRANSCRIBE_OPTIONS_ORDER = list(TRANSCRIBE_OPTION_DESCRIPTIONS.keys())


# ── TOML helpers ──────────────────────────────────────────────────────────────

def _read_raw() -> str:
    return CHANNELS_TOML.read_text(encoding="utf-8")


def _write_raw(raw: str) -> None:
    CHANNELS_TOML.write_text(raw, encoding="utf-8")


def _read_cfg() -> dict:
    with open(CHANNELS_TOML, "rb") as f:
        return tomllib.load(f)


def _toml_str(v: str) -> str:
    return '"' + v.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _toml_list(items: list[str]) -> str:
    return "[" + ", ".join(_toml_str(i) for i in items) + "]"


# ── subscriptions ─────────────────────────────────────────────────────────────

def cmd_list_subscriptions(_args) -> None:
    cfg = _read_cfg()
    print(json.dumps(cfg.get("subscriptions", [])))


def cmd_get_subscription_prompts(args) -> None:
    cfg = _read_cfg()
    for sub in cfg.get("subscriptions", []):
        if sub.get("name") == args.name:
            print(json.dumps(sub.get("prompts") or []))
            return
    print("[]")


def cmd_add_subscription(args) -> None:
    raw = _read_raw()
    lines = ["\n[[subscriptions]]", f"name = {_toml_str(args.name)}", f"url  = {_toml_str(args.url)}"]
    if args.prompts:
        lines.append(f"prompts = {_toml_list(args.prompts)}")
    block = "\n".join(lines) + "\n"
    # Insert before [summarize_queue] / [transcribe_queue], or at end
    m = re.search(r"\n\[(summarize_queue|transcribe_queue)\]", raw)
    if m:
        raw = raw[: m.start()] + block + raw[m.start() :]
    else:
        raw = raw.rstrip() + block + "\n"
    _write_raw(raw)


def cmd_remove_subscription(args) -> None:
    raw = _read_raw()
    escaped = re.escape(args.name)
    # Match [[subscriptions]] block containing this name, up to next [ or end
    pattern = r"\n\[\[subscriptions\]\](?:(?!\n\[).)*?name\s*=\s*\"" + escaped + r"\"(?:(?!\n\[).)*"
    new_raw = re.sub(pattern, "", raw, flags=re.S)
    if new_raw == raw:
        print(f"ERROR: subscription '{args.name}' not found", file=sys.stderr)
        sys.exit(1)
    _write_raw(new_raw)


def cmd_edit_subscription_prompts(args) -> None:
    raw = _read_raw()
    escaped = re.escape(args.name)

    def replace_block(m: re.Match) -> str:
        block = m.group(0)
        # Remove existing prompts line
        block = re.sub(r"\nprompts\s*=\s*\[[^\]]*\]", "", block)
        if args.prompts:
            block = block.rstrip("\n") + f"\nprompts = {_toml_list(args.prompts)}\n"
        return block

    # Match [[subscriptions]] block containing this name
    pattern = r"\[\[subscriptions\]\](?:(?!\n\[).)*?name\s*=\s*\"" + escaped + r"\"(?:(?!\n\[).)*"
    new_raw = re.sub(pattern, replace_block, raw, flags=re.S)
    if new_raw == raw:
        print(f"ERROR: subscription '{args.name}' not found", file=sys.stderr)
        sys.exit(1)
    _write_raw(new_raw)


# ── queues ────────────────────────────────────────────────────────────────────

def cmd_set_queue(args) -> None:
    raw = _read_raw()
    section_key = f"{args.queue_type}_queue"
    lines = [f"[{section_key}]", f"name    = {_toml_str(args.name)}", f"url     = {_toml_str(args.url)}"]
    if args.prompts:
        lines.append(f"prompts = {_toml_list(args.prompts)}")
    new_section = "\n".join(lines) + "\n"

    if f"[{section_key}]" in raw:
        pattern = r"\[" + section_key + r"\][^\[]*"
        raw = re.sub(pattern, new_section, raw, flags=re.S)
    else:
        raw = raw.rstrip() + "\n\n" + new_section + "\n"
    _write_raw(raw)


def cmd_get_queue(args) -> None:
    cfg = _read_cfg()
    section_key = f"{args.queue_type}_queue"
    q = cfg.get(section_key, {})
    print(json.dumps(q))


def cmd_clear_queue(args) -> None:
    raw = _read_raw()
    section_key = f"{args.queue_type}_queue"
    pattern = r"\n\[" + section_key + r"\][^\[]*"
    new_raw = re.sub(pattern, "", raw, flags=re.S)
    if new_raw == raw:
        print(f"ERROR: [{section_key}] not found", file=sys.stderr)
        sys.exit(1)
    _write_raw(new_raw)


# ── prompts ───────────────────────────────────────────────────────────────────

def cmd_list_prompts(_args) -> None:
    out = []
    for p in sorted(PROMPTS_DIR.glob("*.md")):
        raw = p.read_text(encoding="utf-8")
        key = re.sub(r"^\d+_?", "", p.stem)

        label_m = re.search(r"(?mi)^\s*label\s*:\s*(.+?)\s*$", raw)
        label = label_m.group(1).strip() if label_m else key

        enabled_m = re.search(r"(?mi)^\s*enabled\s*:\s*(true|false)\s*$", raw)
        enabled = (enabled_m.group(1).lower() == "true") if enabled_m else False

        # Extract first meaningful line of the short prompt as a description
        short_m = re.search(r"(?m)^## short\s*$\n+```prompt\n(.*?)```", raw, re.S)
        desc = ""
        if short_m:
            for line in short_m.group(1).strip().splitlines():
                line = line.strip()
                if line and not line.startswith("Rules:") and "{transcript}" not in line:
                    desc = line[:100]
                    break

        out.append({"key": key, "label": label, "enabled": enabled, "description": desc})
    print(json.dumps(out))


# ── transcribe options ────────────────────────────────────────────────────────

def cmd_list_transcribe_options(_args) -> None:
    raw = TRANSCRIBE_MD.read_text(encoding="utf-8")
    out = []
    for key in TRANSCRIBE_OPTIONS_ORDER:
        m = re.search(rf"(?mi)^\s*{key}\s*:\s*(true|false)\s*$", raw)
        enabled = (m.group(1).lower() == "true") if m else False
        out.append({
            "key": key,
            "description": TRANSCRIBE_OPTION_DESCRIPTIONS.get(key, key),
            "enabled": enabled,
        })
    print(json.dumps(out))


def cmd_set_transcribe_options(args) -> None:
    raw = TRANSCRIBE_MD.read_text(encoding="utf-8")
    selected = set(args.options) if args.options else set()
    for key in TRANSCRIBE_OPTIONS_ORDER:
        val = "true" if key in selected else "false"
        raw = re.sub(
            rf"(?m)^(\s*{key}\s*:\s*)(true|false)(\s*)$",
            rf"\g<1>{val}\g<3>",
            raw,
        )
    TRANSCRIBE_MD.write_text(raw, encoding="utf-8")


# ── subscription detail display ───────────────────────────────────────────────

def cmd_show_subscription_detail(args) -> None:
    """Print a human-readable prompt status block for one subscription."""
    cfg = _read_cfg()
    sub = next((s for s in cfg.get("subscriptions", []) if s.get("name") == args.name), None)
    if sub is None:
        print(f"  (subscription '{args.name}' not found)", file=sys.stderr)
        return

    print(f"  URL: {sub.get('url', '(none)')}")
    print()

    explicit: list[str] = sub.get("prompts") or []

    # Load all prompts
    all_prompts = []
    for p in sorted(PROMPTS_DIR.glob("*.md")):
        if p.name == "README.md":
            continue
        raw = p.read_text(encoding="utf-8")
        key = re.sub(r"^\d+_?", "", p.stem)
        label_m = re.search(r"(?mi)^\s*label\s*:\s*(.+)", raw)
        label = label_m.group(1).strip() if label_m else key
        enabled_m = re.search(r"(?mi)^\s*enabled\s*:\s*(true|false)", raw)
        enabled = (enabled_m.group(1).lower() == "true") if enabled_m else False
        all_prompts.append({"key": key, "label": label, "enabled": enabled})

    if explicit:
        print(f"  Prompts (per-feed — {len(explicit)} selected):")
        for p in all_prompts:
            active = p["key"] in explicit
            mark = "✓" if active else " "
            faded = "" if active else "  "
            print(f"    {mark}  {p['label']:{faded}}")
    else:
        running = [p for p in all_prompts if p["enabled"]]
        off = [p for p in all_prompts if not p["enabled"]]
        print(f"  Prompts: all globally-enabled ({len(running)} running, {len(off)} off)")
        for p in running:
            print(f"    ✓  {p['label']}")
        if off:
            print(f"       ({len(off)} others globally disabled)")


def cmd_main_menu_subs(_args) -> None:
    """Print subscription items for the main menu, one per line: 'NAME\tPROMPT_SUMMARY'"""
    cfg = _read_cfg()
    for s in cfg.get("subscriptions", []):
        name = s.get("name", "(unnamed)")
        prompts = s.get("prompts") or []
        summary = ", ".join(prompts) if prompts else "all enabled"
        print(f"{name}\t{summary}")


# ── entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list-subscriptions")
    sub.add_parser("list-prompts")
    sub.add_parser("list-transcribe-options")
    sub.add_parser("main-menu-subs")

    ssd = sub.add_parser("show-subscription-detail")
    ssd.add_argument("--name", required=True)

    gs = sub.add_parser("get-subscription-prompts")
    gs.add_argument("--name", required=True)

    gq = sub.add_parser("get-queue")
    gq.add_argument("--type", dest="queue_type", required=True, choices=["summarize", "transcribe"])

    add = sub.add_parser("add-subscription")
    add.add_argument("--name", required=True)
    add.add_argument("--url", required=True)
    add.add_argument("--prompts", nargs="*", default=[])

    rm = sub.add_parser("remove-subscription")
    rm.add_argument("--name", required=True)

    ep = sub.add_parser("edit-subscription-prompts")
    ep.add_argument("--name", required=True)
    ep.add_argument("--prompts", nargs="*", default=[])

    sq = sub.add_parser("set-queue")
    sq.add_argument("--type", dest="queue_type", required=True, choices=["summarize", "transcribe"])
    sq.add_argument("--name", required=True)
    sq.add_argument("--url", required=True)
    sq.add_argument("--prompts", nargs="*", default=[])

    cq = sub.add_parser("clear-queue")
    cq.add_argument("--type", dest="queue_type", required=True, choices=["summarize", "transcribe"])

    sto = sub.add_parser("set-transcribe-options")
    sto.add_argument("--options", nargs="*", default=[])

    args = p.parse_args()
    {
        "list-subscriptions":        cmd_list_subscriptions,
        "list-prompts":              cmd_list_prompts,
        "list-transcribe-options":   cmd_list_transcribe_options,
        "get-subscription-prompts":  cmd_get_subscription_prompts,
        "get-queue":                 cmd_get_queue,
        "clear-queue":               cmd_clear_queue,
        "add-subscription":          cmd_add_subscription,
        "remove-subscription":       cmd_remove_subscription,
        "edit-subscription-prompts": cmd_edit_subscription_prompts,
        "set-queue":                 cmd_set_queue,
        "set-transcribe-options":      cmd_set_transcribe_options,
        "show-subscription-detail":    cmd_show_subscription_detail,
        "main-menu-subs":              cmd_main_menu_subs,
    }[args.cmd](args)


if __name__ == "__main__":
    main()

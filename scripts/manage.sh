#!/usr/bin/env bash
# YouTube Summarizer — management TUI
# Requires: gum (brew install gum), yt-dlp, python3

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON="$REPO_ROOT/.venv/bin/python3"
CONFIG="$SCRIPT_DIR/_config.py"
ENV_FILE="$REPO_ROOT/.env"
PLIST_LABEL="com.youtube-summarizer"

# ── dependency check ──────────────────────────────────────────────────────────
if ! command -v gum &>/dev/null; then
  echo "gum is not installed. Run: brew install gum"
  exit 1
fi
if [ ! -f "$PYTHON" ]; then
  PYTHON="$(command -v python3)"
fi

# ── first-run bootstrap ───────────────────────────────────────────────────────
CHANNELS_TOML="$REPO_ROOT/config/channels.toml"
CHANNELS_EXAMPLE="$REPO_ROOT/config/channels.example.toml"
if [ ! -f "$CHANNELS_TOML" ] && [ -f "$CHANNELS_EXAMPLE" ]; then
  cp "$CHANNELS_EXAMPLE" "$CHANNELS_TOML"
  echo "  Created config/channels.toml from channels.example.toml"
fi

# ── colours ───────────────────────────────────────────────────────────────────
ACCENT=212
DIM=240
GREEN=82
YELLOW=214
RED=196

# ── ui helpers ────────────────────────────────────────────────────────────────
header() {
  # Usage: header "Title" ["Subtitle"]
  if [ -n "${2:-}" ]; then
    gum style \
      --foreground "$ACCENT" --border-foreground "$ACCENT" --border double \
      --align center --width 64 --margin "1 2" --padding "1 2" \
      "⬛  YouTube Summarizer" "${1}" "${2}"
  else
    gum style \
      --foreground "$ACCENT" --border-foreground "$ACCENT" --border double \
      --align center --width 64 --margin "1 2" --padding "1 2" \
      "⬛  YouTube Summarizer" "${1}"
  fi
}

section() { echo ""; gum style --foreground "$ACCENT" --bold "  ${1}"; echo ""; }
dim()     { gum style --foreground "$DIM"    "  ${1}"; }
ok()      { gum style --foreground "$GREEN"  "  ✓  ${1}"; }
warn()    { gum style --foreground "$YELLOW" "  ⚠   ${1}"; }
err()     { gum style --foreground "$RED"    "  ✗  ${1}"; }

pause() {
  echo ""
  read -r -p "  Press Enter to continue…" </dev/tty
  echo ""
}

# ── live status (shown in main menu header) ───────────────────────────────────
live_status() {
  local svc
  if launchctl list 2>/dev/null | grep -q "$PLIST_LABEL"; then
    svc="● running"
  else
    svc="○ stopped"
  fi
  local info
  info=$("$PYTHON" - "$REPO_ROOT" <<'PYEOF'
import tomllib, sys
repo = sys.argv[1]
try:
    with open(f"{repo}/config/channels.toml", "rb") as f:
        cfg = tomllib.load(f)
    n  = len(cfg.get("subscriptions", []))
    sq = "✓" if cfg.get("summarize_queue",  {}).get("url") else "—"
    tq = "✓" if cfg.get("transcribe_queue", {}).get("url") else "—"
    s  = "s" if n != 1 else ""
    print(f"{n} sub{s}  ·  summarize:{sq}  transcribe:{tq}")
except Exception:
    print("config unreadable")
PYEOF
)
  echo "service $svc  ·  $info"
}

# ── fetch channel/playlist name via yt-dlp ────────────────────────────────────
fetch_name() {
  local url="$1"
  gum spin --spinner dot --title "  Fetching info from YouTube…" -- \
    bash -c "yt-dlp --flat-playlist --playlist-items 1 --dump-single-json '$url' \
             2>/dev/null > /tmp/yts_urlinfo.json || true"
  "$PYTHON" - <<'PYEOF'
import json
try:
    with open('/tmp/yts_urlinfo.json') as f:
        d = json.load(f)
    print((d.get('channel') or d.get('uploader') or
           d.get('playlist_title') or d.get('title') or '').strip())
except Exception:
    print('')
PYEOF
}

# ── prompt picker (multi-select, shows global on/off per item) ────────────────
# $1 = space-separated currently-selected keys (for pre-selection)
pick_prompts() {
  local current_keys="${1:-}"
  local display_items=()
  local selected_display=()

  while IFS= read -r entry; do
    local key label glob_on
    key=$(     echo "$entry" | "$PYTHON" -c "import json,sys; print(json.loads(sys.stdin.read())['key'])")
    label=$(   echo "$entry" | "$PYTHON" -c "import json,sys; print(json.loads(sys.stdin.read())['label'])")
    glob_on=$( echo "$entry" | "$PYTHON" -c "import json,sys; print(json.loads(sys.stdin.read())['enabled'])")
    local status; [ "$glob_on" = "True" ] && status="on" || status="off"
    local item="$key — $label  [default: $status]"
    display_items+=("$item")
    if echo " $current_keys " | grep -qF " $key "; then
      selected_display+=("$item")
    fi
  done < <("$PYTHON" "$CONFIG" list-prompts | "$PYTHON" -c "
import json,sys
for p in json.load(sys.stdin): print(json.dumps(p))
")

  [ ${#display_items[@]} -eq 0 ] && { err "No prompts found."; return 1; }

  dim "↑↓ navigate  ·  x toggle  ·  Enter confirm  ·  none selected = global defaults"
  echo ""

  local choose_args=("--no-limit" "--height" "16")
  if [ ${#selected_display[@]} -gt 0 ]; then
    local sel_str
    sel_str=$(printf '%s\n' "${selected_display[@]}" | paste -sd',' -)
    choose_args+=("--selected" "$sel_str")
  fi
  printf '%s\n' "${display_items[@]}" | gum choose "${choose_args[@]}" || true
}

keys_from_choice() { sed 's/ — .*//'; }

# ── subscription detail screen ────────────────────────────────────────────────
cmd_subscription_detail() {
  local sub_name="$1"

  while true; do
    header "$sub_name"

    # Show URL + prompt status (via _config.py)
    "$PYTHON" "$CONFIG" show-subscription-detail --name "$sub_name"
    echo ""

    local action
    action=$(gum choose \
      --header "  ──────────────────────────────" \
      "✏️   Edit prompts" \
      "🗑   Remove subscription" \
      "←   Back") || return

    case "$action" in

      "✏️"*)
        local current_keys
        current_keys=$("$PYTHON" "$CONFIG" get-subscription-prompts --name "$sub_name" | \
          "$PYTHON" -c "import json,sys; print(' '.join(json.load(sys.stdin)))")
        section "Prompts for: $sub_name"
        local chosen
        chosen=$(pick_prompts "$current_keys")
        local prompt_args=()
        if [ -n "$chosen" ]; then
          while IFS= read -r line; do
            local k; k=$(echo "$line" | keys_from_choice)
            [ -n "$k" ] && prompt_args+=("$k")
          done <<< "$chosen"
        fi
        "$PYTHON" "$CONFIG" edit-subscription-prompts \
          --name "$sub_name" \
          ${prompt_args:+--prompts "${prompt_args[@]}"}
        local pd="all enabled"
        [ ${#prompt_args[@]} -gt 0 ] && pd="${prompt_args[*]}"
        ok "Prompts updated → $pd"
        pause
        ;;

      "🗑"*)
        echo ""
        if gum confirm "  Remove '$sub_name'?"; then
          "$PYTHON" "$CONFIG" remove-subscription --name "$sub_name"
          ok "Removed: $sub_name"
          pause
          return
        else
          warn "Cancelled."
        fi
        ;;

      "←"*) return ;;
    esac
  done
}

# ── 1. add subscription ───────────────────────────────────────────────────────
cmd_subscribe() {
  header "Add Subscription"

  section "YouTube channel or playlist URL:"
  local url
  url=$(gum input --placeholder "https://www.youtube.com/channel/UC…" --width 68)
  [ -z "$url" ] && { warn "Cancelled."; return; }

  local name; name=$(fetch_name "$url")
  if [ -z "$name" ]; then
    warn "Could not auto-detect name."
    section "Enter name manually:"
    name=$(gum input --placeholder "Channel or playlist name" --width 60)
  else
    section "Detected: $name"
    gum confirm "  Use this name?" || name=$(gum input --value "$name" --width 60)
  fi
  [ -z "$name" ] && { warn "Name is required. Cancelled."; return; }

  section "Which prompts should run for this feed?"
  local chosen; chosen=$(pick_prompts "")
  local prompt_args=()
  if [ -n "$chosen" ]; then
    while IFS= read -r line; do
      local k; k=$(echo "$line" | keys_from_choice)
      [ -n "$k" ] && prompt_args+=("$k")
    done <<< "$chosen"
  fi
  local pd="all enabled"
  [ ${#prompt_args[@]} -gt 0 ] && pd="${prompt_args[*]}"

  echo ""
  dim "Name:    $name"
  dim "URL:     $url"
  dim "Prompts: $pd"
  echo ""
  gum confirm "  Add this subscription?" || { warn "Cancelled."; return; }

  "$PYTHON" "$CONFIG" add-subscription \
    --name "$name" --url "$url" \
    ${prompt_args:+--prompts "${prompt_args[@]}"}
  ok "Subscribed: $name"
  pause
}

# ── shared: edit transcribe queue URL/options ─────────────────────────────────
_edit_transcribe_queue() {
  local current_url="${1:-}" current_name="${2:-}"

  section "YouTube playlist URL:"
  local url
  url=$(gum input --value "${current_url}" \
    --placeholder "https://www.youtube.com/playlist?list=PL…" --width 68)
  [ -z "$url" ] && { warn "Cancelled."; return 1; }

  local name; name=$(fetch_name "$url")
  if [ -z "$name" ]; then
    section "Enter name manually:"
    name=$(gum input --placeholder "Playlist name" --width 60)
  else
    section "Detected: $name"
    gum confirm "  Use this name?" || name=$(gum input --value "$name" --width 60)
  fi
  [ -z "$name" ] && { warn "Name is required. Cancelled."; return 1; }

  section "Transcript cleanup options:"
  dim "Controls how the raw Parakeet transcript is cleaned before emailing."
  echo ""

  local display_items=() selected_display=()
  while IFS= read -r entry; do
    local okey oe od
    okey=$(echo "$entry" | "$PYTHON" -c "import json,sys; print(json.loads(sys.stdin.read())['key'])")
    od=$(  echo "$entry" | "$PYTHON" -c "import json,sys; print(json.loads(sys.stdin.read())['description'])")
    oe=$(  echo "$entry" | "$PYTHON" -c "import json,sys; print(json.loads(sys.stdin.read())['enabled'])")
    local item="$okey — $od"
    display_items+=("$item")
    [ "$oe" = "True" ] && selected_display+=("$item")
  done < <("$PYTHON" "$CONFIG" list-transcribe-options | "$PYTHON" -c "
import json,sys
for o in json.load(sys.stdin): print(json.dumps(o))
")

  local choose_args=("--no-limit" "--height" "12")
  if [ ${#selected_display[@]} -gt 0 ]; then
    local sel_str
    sel_str=$(printf '%s\n' "${selected_display[@]}" | paste -sd',' -)
    choose_args+=("--selected" "$sel_str")
  fi
  local chosen_opts
  chosen_opts=$(printf '%s\n' "${display_items[@]}" | gum choose "${choose_args[@]}" || true)

  local opt_args=()
  if [ -n "$chosen_opts" ]; then
    while IFS= read -r line; do
      local ov; ov=$(echo "$line" | sed 's/ — .*//')
      [ -n "$ov" ] && opt_args+=("$ov")
    done <<< "$chosen_opts"
  fi

  echo ""
  dim "Name: $name"
  dim "URL:  $url"
  echo ""
  gum confirm "  Save transcribe queue?" || { warn "Cancelled."; return 1; }

  "$PYTHON" "$CONFIG" set-queue --type transcribe --name "$name" --url "$url"
  "$PYTHON" "$CONFIG" set-transcribe-options ${opt_args:+--options "${opt_args[@]}"}
  ok "Transcribe queue saved: $name"
  pause
}

# ── manage transcribe queue ───────────────────────────────────────────────────
cmd_manage_transcribe_queue() {
  while true; do
    header "Transcribe Queue"

    local current_url current_name
    current_url=$("$PYTHON" "$CONFIG" get-queue --type transcribe 2>/dev/null | \
      "$PYTHON" -c "import json,sys; print(json.load(sys.stdin).get('url',''))" 2>/dev/null || echo "")
    current_name=$("$PYTHON" "$CONFIG" get-queue --type transcribe 2>/dev/null | \
      "$PYTHON" -c "import json,sys; print(json.load(sys.stdin).get('name',''))" 2>/dev/null || echo "")

    echo ""
    if [ -n "$current_url" ]; then
      dim "Name:  $current_name"
      dim "URL:   $current_url"
    else
      dim "(not configured)"
    fi
    echo ""

    local actions=()
    if [ -n "$current_url" ]; then
      actions+=("✏️   Edit URL & options")
      actions+=("🗑   Remove queue")
    else
      actions+=("➕  Set up queue")
    fi
    actions+=("←   Back")

    local action
    action=$(printf '%s\n' "${actions[@]}" | gum choose \
      --header "  ──────────────────────────────") || return

    case "$action" in
      "✏️"* | "➕"*)
        _edit_transcribe_queue "$current_url" "$current_name"
        ;;
      "🗑"*)
        echo ""
        if gum confirm "  Remove transcribe queue?"; then
          "$PYTHON" "$CONFIG" clear-queue --type transcribe
          ok "Transcribe queue removed."
          pause
        else
          warn "Cancelled."
        fi
        ;;
      "←"*) return ;;
    esac
  done
}

# ── shared: edit summarize queue URL/prompts ──────────────────────────────────
_edit_summarize_queue() {
  local current_url="${1:-}" current_name="${2:-}"

  section "YouTube playlist URL:"
  local url
  url=$(gum input --value "${current_url}" \
    --placeholder "https://www.youtube.com/playlist?list=PL…" --width 68)
  [ -z "$url" ] && { warn "Cancelled."; return 1; }

  local name; name=$(fetch_name "$url")
  if [ -z "$name" ]; then
    section "Enter name manually:"
    name=$(gum input --placeholder "Playlist name" --width 60)
  else
    section "Detected: $name"
    gum confirm "  Use this name?" || name=$(gum input --value "$name" --width 60)
  fi
  [ -z "$name" ] && { warn "Name is required. Cancelled."; return 1; }

  section "Which prompts should run for this queue?"
  local chosen; chosen=$(pick_prompts "")
  local prompt_args=()
  if [ -n "$chosen" ]; then
    while IFS= read -r line; do
      local k; k=$(echo "$line" | keys_from_choice)
      [ -n "$k" ] && prompt_args+=("$k")
    done <<< "$chosen"
  fi
  local pd="all enabled"
  [ ${#prompt_args[@]} -gt 0 ] && pd="${prompt_args[*]}"

  echo ""
  dim "Name:    $name"
  dim "URL:     $url"
  dim "Prompts: $pd"
  echo ""
  gum confirm "  Save summarize queue?" || { warn "Cancelled."; return 1; }

  "$PYTHON" "$CONFIG" set-queue --type summarize --name "$name" --url "$url" \
    ${prompt_args:+--prompts "${prompt_args[@]}"}
  ok "Summarize queue saved: $name"
  pause
}

# ── manage summarize queue ────────────────────────────────────────────────────
cmd_manage_summarize_queue() {
  while true; do
    header "Summarize Queue"

    local current_url current_name current_prompts
    current_url=$("$PYTHON" "$CONFIG" get-queue --type summarize 2>/dev/null | \
      "$PYTHON" -c "import json,sys; print(json.load(sys.stdin).get('url',''))" 2>/dev/null || echo "")
    current_name=$("$PYTHON" "$CONFIG" get-queue --type summarize 2>/dev/null | \
      "$PYTHON" -c "import json,sys; print(json.load(sys.stdin).get('name',''))" 2>/dev/null || echo "")
    current_prompts=$("$PYTHON" "$CONFIG" get-queue --type summarize 2>/dev/null | \
      "$PYTHON" -c "import json,sys; p=json.load(sys.stdin).get('prompts') or []; print(', '.join(p) if p else 'all enabled')" \
      2>/dev/null || echo "all enabled")

    echo ""
    if [ -n "$current_url" ]; then
      dim "Name:    $current_name"
      dim "URL:     $current_url"
      dim "Prompts: $current_prompts"
    else
      dim "(not configured)"
    fi
    echo ""

    local actions=()
    if [ -n "$current_url" ]; then
      actions+=("✏️   Edit URL & prompts")
      actions+=("🗑   Remove queue")
    else
      actions+=("➕  Set up queue")
    fi
    actions+=("←   Back")

    local action
    action=$(printf '%s\n' "${actions[@]}" | gum choose \
      --header "  ──────────────────────────────") || return

    case "$action" in
      "✏️"* | "➕"*)
        _edit_summarize_queue "$current_url" "$current_name"
        ;;
      "🗑"*)
        echo ""
        if gum confirm "  Remove summarize queue?"; then
          "$PYTHON" "$CONFIG" clear-queue --type summarize
          ok "Summarize queue removed."
          pause
        else
          warn "Cancelled."
        fi
        ;;
      "←"*) return ;;
    esac
  done
}

# ── run now ───────────────────────────────────────────────────────────────────
cmd_run_now() {
  header "Run Now"

  local mode
  mode=$(gum choose \
    --header "  Choose run mode:" \
    "▶️   Normal — process videos and send emails" \
    "🔍  Dry run — preview only, no emails sent") || return

  local cmd=("$PYTHON" -m youtube_summarizer run)
  [[ "$mode" == "🔍"* ]] && cmd+=("--dry-run")

  echo ""
  dim "Running: ${cmd[*]}"
  echo ""
  (cd "$REPO_ROOT" && "${cmd[@]}")
  pause
}

# ── service status ────────────────────────────────────────────────────────────
cmd_status() {
  header "Service Status"

  echo ""
  if launchctl list 2>/dev/null | grep -q "$PLIST_LABEL"; then
    ok "launchd service: running (polls every 15 min)"
  else
    warn "launchd service: not running"
    dim "Install: sed \"s|__PROJECT_PATH__|$REPO_ROOT|g\" launchd/com.youtube-summarizer.plist \\"
    dim "           > ~/Library/LaunchAgents/com.youtube-summarizer.plist"
    dim "Start:   launchctl load ~/Library/LaunchAgents/com.youtube-summarizer.plist"
  fi

  echo ""
  section "Database:"
  "$PYTHON" - "$REPO_ROOT" <<'PYEOF'
import sqlite3, pathlib, sys
db = pathlib.Path(sys.argv[1]) / "data" / "state.db"
if db.exists():
    con = sqlite3.connect(db)
    total  = con.execute("SELECT COUNT(*) FROM seen_videos").fetchone()[0]
    recent = con.execute(
        "SELECT COUNT(*) FROM seen_videos WHERE seen_at > datetime('now', '-7 days')"
    ).fetchone()[0]
    rows = con.execute(
        "SELECT channel_name, title, seen_at FROM seen_videos ORDER BY seen_at DESC LIMIT 5"
    ).fetchall()
    con.close()
    print(f"    Processed all time:   {total}")
    print(f"    Processed last 7d:    {recent}")
    if rows:
        print()
        print("    Most recent:")
        for ch, ti, at in rows:
            print(f"      {at[:16]}  {(ch or '?')[:20]:<20}  {(ti or '?')[:38]}")
else:
    print("    No database yet — run once to create it.")
PYEOF

  echo ""
  section "Configured feeds:"
  "$PYTHON" - "$REPO_ROOT" <<'PYEOF'
import tomllib, pathlib, sys
try:
    with open(pathlib.Path(sys.argv[1]) / "config" / "channels.toml", "rb") as f:
        cfg = tomllib.load(f)
    subs = cfg.get("subscriptions", [])
    if subs:
        print(f"    Subscriptions ({len(subs)}):")
        for s in subs:
            p = s.get("prompts") or []
            label = ", ".join(p) if p else "all enabled"
            print(f"      •  {s.get('name', '(unnamed)')}  [{label}]")
    else:
        print("    Subscriptions: none")
    sq = cfg.get("summarize_queue", {})
    if sq.get("url"):
        p = sq.get("prompts") or []
        print(f"    Summarize queue:   {sq.get('name', '(unnamed)')}  [{', '.join(p) if p else 'all enabled'}]")
    else:
        print("    Summarize queue:   not configured")
    tq = cfg.get("transcribe_queue", {})
    print(f"    Transcribe queue:  {'configured — ' + tq.get('name','') if tq.get('url') else 'not configured'}")
except Exception as e:
    print(f"    Error: {e}")
PYEOF

  echo ""
  section "Recent logs:"
  local shown=0
  for log in /tmp/youtube-summarizer.out.log /tmp/youtube-summarizer.err.log; do
    if [ -f "$log" ] && [ -s "$log" ]; then
      dim "$(basename "$log"):"
      tail -8 "$log" | while IFS= read -r line; do echo "    $line"; done
      echo ""
      shown=1
    fi
  done
  [ "$shown" = "0" ] && dim "No logs yet."
  pause
}

# ── settings ──────────────────────────────────────────────────────────────────
cmd_settings() {
  header "Settings"

  local email_from="" email_to="" ollama_model="" parakeet_model="" has_pw="no"
  if [ -f "$ENV_FILE" ]; then
    email_from=$(     grep '^YTS_EMAIL_FROM='          "$ENV_FILE" 2>/dev/null | cut -d= -f2- | tr -d '"' || echo "")
    email_to=$(       grep '^YTS_EMAIL_TO='            "$ENV_FILE" 2>/dev/null | cut -d= -f2- | tr -d '"' || echo "")
    ollama_model=$(   grep '^YTS_OLLAMA_MODEL='        "$ENV_FILE" 2>/dev/null | cut -d= -f2- | tr -d '"' || echo "")
    parakeet_model=$( grep '^YTS_PARAKEET_MODEL='      "$ENV_FILE" 2>/dev/null | cut -d= -f2- | tr -d '"' || echo "")
    local _pw
    _pw=$(            grep '^YTS_GMAIL_APP_PASSWORD='  "$ENV_FILE" 2>/dev/null | cut -d= -f2- | tr -d '"' || echo "")
    [ -n "$_pw" ] && has_pw="yes"
  fi

  section "Email from (your Gmail address):"
  email_from=$(gum input --value "$email_from" --placeholder "you@gmail.com" --width 54)

  section "Email to (where summaries are delivered):"
  email_to=$(gum input --value "$email_to" --placeholder "you@gmail.com" --width 54)

  section "Gmail app password:"
  dim "Generate at: myaccount.google.com/apppasswords"
  [ "$has_pw" = "yes" ] && dim "Already set — leave blank to keep existing password."
  local gmail_pw
  gmail_pw=$(gum input --password --placeholder "xxxx xxxx xxxx xxxx" --width 54)

  section "Ollama model:"
  dim "Recommended: qwen2.5:14b (24 GB RAM)  ·  qwen2.5:7b (8 GB)  ·  qwen2.5:32b (64 GB)"
  ollama_model=$(gum input --value "${ollama_model:-qwen2.5:14b}" --placeholder "qwen2.5:14b" --width 40)

  section "Parakeet model (transcription):"
  parakeet_model=$(gum input \
    --value "${parakeet_model:-mlx-community/parakeet-tdt-0.6b-v3}" --width 60)

  echo ""
  gum confirm "  Save settings to .env?" || { warn "Cancelled."; return; }

  local tmp; tmp=$(mktemp)

  if [ -f "$ENV_FILE" ]; then
    if [ -n "$gmail_pw" ]; then
      # New password — strip old one too
      grep -Ev '^(YTS_EMAIL_FROM|YTS_EMAIL_TO|YTS_OLLAMA_MODEL|YTS_PARAKEET_MODEL|YTS_GMAIL_APP_PASSWORD)=' \
        "$ENV_FILE" > "$tmp" 2>/dev/null || true
    else
      # Keep existing password
      grep -Ev '^(YTS_EMAIL_FROM|YTS_EMAIL_TO|YTS_OLLAMA_MODEL|YTS_PARAKEET_MODEL)=' \
        "$ENV_FILE" > "$tmp" 2>/dev/null || true
    fi
  fi

  {
    echo "YTS_EMAIL_FROM=\"$email_from\""
    echo "YTS_EMAIL_TO=\"$email_to\""
    [ -n "$gmail_pw" ]       && echo "YTS_GMAIL_APP_PASSWORD=\"$gmail_pw\""
    [ -n "$ollama_model" ]   && echo "YTS_OLLAMA_MODEL=\"$ollama_model\""
    [ -n "$parakeet_model" ] && echo "YTS_PARAKEET_MODEL=\"$parakeet_model\""
  } >> "$tmp"
  mv "$tmp" "$ENV_FILE"

  ok "Settings saved to .env"
  pause
}

# ── main menu (dynamic — subscriptions listed inline) ─────────────────────────
main() {
  while true; do
    local status; status=$(live_status)
    header "Setup & Management" "$status"

    # Build item list dynamically
    local items=()
    items+=("➕  Add subscription")

    # One item per subscription
    while IFS=$'\t' read -r sub_name sub_prompts; do
      [ -z "$sub_name" ] && continue
      items+=("📺  $sub_name  ·  $sub_prompts")
    done < <("$PYTHON" "$CONFIG" main-menu-subs 2>/dev/null || true)

    # Queues with current state
    local sq_label tq_label
    sq_label=$("$PYTHON" "$CONFIG" get-queue --type summarize 2>/dev/null | \
      "$PYTHON" -c "import json,sys; d=json.load(sys.stdin); print(d['name'] if d.get('url') else 'not configured')" \
      2>/dev/null || echo "not configured")
    tq_label=$("$PYTHON" "$CONFIG" get-queue --type transcribe 2>/dev/null | \
      "$PYTHON" -c "import json,sys; d=json.load(sys.stdin); print(d['name'] if d.get('url') else 'not configured')" \
      2>/dev/null || echo "not configured")

    items+=("📋  Summarize queue  ·  $sq_label")
    items+=("📼  Transcribe queue  ·  $tq_label")
    items+=("▶️   Run now")
    items+=("📊  Status")
    items+=("🔧  Settings")
    items+=("╌╌  Exit")

    local choice
    choice=$(printf '%s\n' "${items[@]}" | gum choose --height 20) || exit 0

    case "$choice" in
      "➕"*)
        cmd_subscribe
        ;;
      "📺"*)
        # Extract subscription name (everything between "📺  " and "  ·  ")
        local sub_name
        sub_name=$(echo "$choice" | sed 's/^📺  //' | sed 's/  ·  .*//')
        cmd_subscription_detail "$sub_name"
        ;;
      "📋"*)
        cmd_manage_summarize_queue
        ;;
      "📼"*)
        cmd_manage_transcribe_queue
        ;;
      "▶️"*)
        cmd_run_now
        ;;
      "📊"*)
        cmd_status
        ;;
      "🔧"*)
        cmd_settings
        ;;
      "╌╌"*)
        exit 0
        ;;
    esac
  done
}

main

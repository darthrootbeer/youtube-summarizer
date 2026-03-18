#!/usr/bin/env bash
# YouTube Summarizer — setup & management TUI
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

# ── styling ───────────────────────────────────────────────────────────────────
ACCENT=212   # pink/magenta
DIM=240
GREEN=82
YELLOW=214
RED=196

header() {
  gum style \
    --foreground "$ACCENT" --border-foreground "$ACCENT" --border double \
    --align center --width 58 --margin "1 2" --padding "1 2" \
    "⬛ YouTube Summarizer" "$1"
}

section() {
  echo ""
  gum style --foreground "$ACCENT" --bold "  $1"
  echo ""
}

dim() {
  gum style --foreground "$DIM" "  $1"
}

ok() {
  gum style --foreground "$GREEN" "  ✓ $1"
}

warn() {
  gum style --foreground "$YELLOW" "  ⚠  $1"
}

err() {
  gum style --foreground "$RED" "  ✗ $1"
}

# ── fetch channel/playlist name via yt-dlp ────────────────────────────────────
fetch_name() {
  local url="$1"
  gum spin --spinner dot --title "  Fetching info from YouTube..." -- \
    bash -c "yt-dlp --flat-playlist --playlist-items 1 --dump-single-json '$url' \
             2>/dev/null > /tmp/yts_urlinfo.json || true"
  "$PYTHON" - "$url" <<'PYEOF'
import json, sys
try:
    with open('/tmp/yts_urlinfo.json') as f:
        d = json.load(f)
    name = (
        d.get('channel') or d.get('uploader') or
        d.get('playlist_title') or d.get('title') or ''
    ).strip()
    print(name)
except Exception:
    print('')
PYEOF
}

# ── pick prompts (multi-select with legend) ───────────────────────────────────
# Args: $1 = space-separated current keys (optional, for pre-selection)
pick_prompts() {
  local current_keys="${1:-}"

  # Build display items and find pre-selected ones
  local display_items=()
  local selected_display=()

  while IFS= read -r entry; do
    local key label desc
    key=$(echo "$entry" | "$PYTHON" -c "import json,sys; d=json.loads(sys.stdin.read()); print(d['key'])")
    label=$(echo "$entry" | "$PYTHON" -c "import json,sys; d=json.loads(sys.stdin.read()); print(d['label'])")
    desc=$(echo "$entry" | "$PYTHON" -c "import json,sys; d=json.loads(sys.stdin.read()); print(d['description'])")

    local item="$key — $label"
    display_items+=("$item")

    if echo " $current_keys " | grep -qF " $key "; then
      selected_display+=("$item")
    fi
  done < <("$PYTHON" "$CONFIG" list-prompts | "$PYTHON" -c "
import json,sys
for p in json.load(sys.stdin):
    print(json.dumps(p))
")

  if [ ${#display_items[@]} -eq 0 ]; then
    err "No prompts found."
    return 1
  fi

  # Show legend
  section "Available prompts:"
  "$PYTHON" "$CONFIG" list-prompts | "$PYTHON" - <<'PYEOF'
import json, sys
data = json.load(sys.stdin)
for p in data:
    status = "on " if p["enabled"] else "off"
    desc = f"  {p['description']}" if p['description'] else ""
    print(f"    [{status}]  {p['key']:20s}  {p['label']}{desc}")
PYEOF
  echo ""
  dim "Leave all unselected = run all globally-enabled prompts"
  echo ""

  local choose_args=("--no-limit" "--height" "14")
  if [ ${#selected_display[@]} -gt 0 ]; then
    local selected_str
    selected_str=$(printf '%s\n' "${selected_display[@]}" | paste -sd',' -)
    choose_args+=("--selected" "$selected_str")
  fi

  printf '%s\n' "${display_items[@]}" | gum choose "${choose_args[@]}" || true
}

# Extract keys from pick_prompts output (strips " — label" suffix)
keys_from_choice() {
  sed 's/ — .*//'
}

# ── 1. subscribe ──────────────────────────────────────────────────────────────
cmd_subscribe() {
  header "Subscribe to Channel / Playlist"

  section "YouTube channel or playlist URL:"
  local url
  url=$(gum input --placeholder "https://www.youtube.com/channel/UC..." --width 68)
  [ -z "$url" ] && { warn "Cancelled."; return; }

  local name
  name=$(fetch_name "$url")

  if [ -z "$name" ]; then
    warn "Could not auto-detect name."
    section "Enter name manually:"
    name=$(gum input --placeholder "Channel or playlist name" --width 60)
  else
    section "Detected: $name"
    if ! gum confirm "  Use this name?"; then
      name=$(gum input --value "$name" --width 60)
    fi
  fi

  [ -z "$name" ] && { warn "Name is required. Cancelled."; return; }

  section "Which prompts should run for this feed?"
  local chosen
  chosen=$(pick_prompts "")

  local prompt_args=()
  if [ -n "$chosen" ]; then
    while IFS= read -r line; do
      key=$(echo "$line" | keys_from_choice)
      [ -n "$key" ] && prompt_args+=("$key")
    done <<< "$chosen"
  fi

  local prompt_display="all enabled"
  [ ${#prompt_args[@]} -gt 0 ] && prompt_display="${prompt_args[*]}"

  echo ""
  gum style --foreground "$DIM" "  Name:    $name"
  gum style --foreground "$DIM" "  URL:     $url"
  gum style --foreground "$DIM" "  Prompts: $prompt_display"
  echo ""

  gum confirm "  Add this subscription?" || { warn "Cancelled."; return; }

  "$PYTHON" "$CONFIG" add-subscription \
    --name "$name" \
    --url  "$url"  \
    ${prompt_args:+--prompts "${prompt_args[@]}"}

  ok "Subscribed: $name"
}

# ── 2. add transcribe queue ───────────────────────────────────────────────────
cmd_add_transcribe_queue() {
  header "Add Transcribe Queue"

  section "YouTube playlist URL (from your account):"
  local url
  url=$(gum input --placeholder "https://www.youtube.com/playlist?list=PL..." --width 68)
  [ -z "$url" ] && { warn "Cancelled."; return; }

  local name
  name=$(fetch_name "$url")

  if [ -z "$name" ]; then
    section "Enter name manually:"
    name=$(gum input --placeholder "Playlist name" --width 60)
  else
    section "Detected: $name"
    if ! gum confirm "  Use this name?"; then
      name=$(gum input --value "$name" --width 60)
    fi
  fi

  [ -z "$name" ] && { warn "Name is required. Cancelled."; return; }

  section "Transcript cleanup options:"
  dim "These control how the raw transcript is cleaned before emailing."
  echo ""

  # Build display items from current state
  local display_items=()
  local selected_display=()
  while IFS= read -r entry; do
    local opt_key opt_desc opt_enabled
    opt_key=$(echo "$entry" | "$PYTHON" -c "import json,sys; d=json.loads(sys.stdin.read()); print(d['key'])")
    opt_desc=$(echo "$entry" | "$PYTHON" -c "import json,sys; d=json.loads(sys.stdin.read()); print(d['description'])")
    opt_enabled=$(echo "$entry" | "$PYTHON" -c "import json,sys; d=json.loads(sys.stdin.read()); print(d['enabled'])")

    local item="$opt_key — $opt_desc"
    display_items+=("$item")
    [ "$opt_enabled" = "True" ] && selected_display+=("$item")
  done < <("$PYTHON" "$CONFIG" list-transcribe-options | "$PYTHON" -c "
import json,sys
for o in json.load(sys.stdin):
    print(json.dumps(o))
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
      local opt_key
      opt_key=$(echo "$line" | sed 's/ — .*//')
      [ -n "$opt_key" ] && opt_args+=("$opt_key")
    done <<< "$chosen_opts"
  fi

  echo ""
  gum style --foreground "$DIM" "  Name: $name"
  gum style --foreground "$DIM" "  URL:  $url"
  echo ""

  gum confirm "  Set transcribe queue?" || { warn "Cancelled."; return; }

  "$PYTHON" "$CONFIG" set-queue \
    --type transcribe \
    --name "$name"   \
    --url  "$url"

  "$PYTHON" "$CONFIG" set-transcribe-options \
    ${opt_args:+--options "${opt_args[@]}"}

  ok "Transcribe queue set: $name"
}

# ── 3. add summarize queue ────────────────────────────────────────────────────
cmd_add_summarize_queue() {
  header "Add Summarize Queue"

  section "YouTube playlist URL (from your account):"
  local url
  url=$(gum input --placeholder "https://www.youtube.com/playlist?list=PL..." --width 68)
  [ -z "$url" ] && { warn "Cancelled."; return; }

  local name
  name=$(fetch_name "$url")

  if [ -z "$name" ]; then
    section "Enter name manually:"
    name=$(gum input --placeholder "Playlist name" --width 60)
  else
    section "Detected: $name"
    if ! gum confirm "  Use this name?"; then
      name=$(gum input --value "$name" --width 60)
    fi
  fi

  [ -z "$name" ] && { warn "Name is required. Cancelled."; return; }

  section "Which prompts should run for this queue?"
  local chosen
  chosen=$(pick_prompts "")

  local prompt_args=()
  if [ -n "$chosen" ]; then
    while IFS= read -r line; do
      key=$(echo "$line" | keys_from_choice)
      [ -n "$key" ] && prompt_args+=("$key")
    done <<< "$chosen"
  fi

  local prompt_display="all enabled"
  [ ${#prompt_args[@]} -gt 0 ] && prompt_display="${prompt_args[*]}"

  echo ""
  gum style --foreground "$DIM" "  Name:    $name"
  gum style --foreground "$DIM" "  URL:     $url"
  gum style --foreground "$DIM" "  Prompts: $prompt_display"
  echo ""

  gum confirm "  Set summarize queue?" || { warn "Cancelled."; return; }

  "$PYTHON" "$CONFIG" set-queue \
    --type summarize \
    --name "$name"   \
    --url  "$url"    \
    ${prompt_args:+--prompts "${prompt_args[@]}"}

  ok "Summarize queue set: $name"
}

# ── 4. manage subscriptions ───────────────────────────────────────────────────
cmd_manage() {
  header "Manage Subscriptions"

  local subs_json
  subs_json=$("$PYTHON" "$CONFIG" list-subscriptions)

  local count
  count=$(echo "$subs_json" | "$PYTHON" -c "import json,sys; print(len(json.load(sys.stdin)))")

  if [ "$count" = "0" ]; then
    warn "No subscriptions configured."
    return
  fi

  # Build display list
  local display_items=()
  while IFS= read -r entry; do
    local sub_name sub_prompts
    sub_name=$(echo "$entry" | "$PYTHON" -c "import json,sys; d=json.loads(sys.stdin.read()); print(d.get('name','(unnamed)'))")
    sub_prompts=$(echo "$entry" | "$PYTHON" -c "
import json,sys
d=json.loads(sys.stdin.read())
p = d.get('prompts') or []
print(', '.join(p) if p else 'all enabled')
")
    display_items+=("$sub_name  [$sub_prompts]")
  done < <(echo "$subs_json" | "$PYTHON" -c "
import json,sys
for s in json.load(sys.stdin):
    print(json.dumps(s))
")

  section "Select a subscription to manage:"
  local choice
  choice=$(printf '%s\n' "${display_items[@]}" | gum choose --height 14) || { warn "Cancelled."; return; }

  # Extract name (everything before the last  [...)
  local sub_name
  sub_name=$(echo "$choice" | "$PYTHON" -c "
import sys, re
line = sys.stdin.read().strip()
print(re.sub(r'\s+\[.*\]$', '', line).strip())
")

  echo ""
  local action
  action=$(gum choose \
    --header "  $sub_name" \
    "Edit prompts" \
    "Remove subscription") || { warn "Cancelled."; return; }

  case "$action" in
    "Edit prompts")
      # Get current prompts for pre-selection
      local current_json
      current_json=$("$PYTHON" "$CONFIG" get-subscription-prompts --name "$sub_name")
      local current_keys
      current_keys=$(echo "$current_json" | "$PYTHON" -c "
import json,sys
keys = json.load(sys.stdin)
print(' '.join(keys))
")
      section "Update prompts for: $sub_name"
      local chosen
      chosen=$(pick_prompts "$current_keys")

      local prompt_args=()
      if [ -n "$chosen" ]; then
        while IFS= read -r line; do
          key=$(echo "$line" | keys_from_choice)
          [ -n "$key" ] && prompt_args+=("$key")
        done <<< "$chosen"
      fi

      "$PYTHON" "$CONFIG" edit-subscription-prompts \
        --name "$sub_name" \
        ${prompt_args:+--prompts "${prompt_args[@]}"}

      local prompt_display="all enabled"
      [ ${#prompt_args[@]} -gt 0 ] && prompt_display="${prompt_args[*]}"
      ok "Prompts updated → $prompt_display"
      ;;

    "Remove subscription")
      echo ""
      if gum confirm "  Remove '$sub_name'?"; then
        "$PYTHON" "$CONFIG" remove-subscription --name "$sub_name"
        ok "Removed: $sub_name"
      else
        warn "Cancelled."
      fi
      ;;
  esac
}

# ── 5. run now ────────────────────────────────────────────────────────────────
cmd_run_now() {
  header "Run Now"

  local mode
  mode=$(gum choose \
    --header "  Choose run mode:" \
    "Normal — process videos and send emails" \
    "Dry run — preview what would be processed, no emails sent") || { warn "Cancelled."; return; }

  local cmd=("$PYTHON" -m youtube_summarizer run)
  [[ "$mode" == "Dry run"* ]] && cmd+=("--dry-run")

  echo ""
  gum style --foreground "$DIM" "  Running: ${cmd[*]}"
  echo ""

  (cd "$REPO_ROOT" && "${cmd[@]}")
}

# ── 6. service status ─────────────────────────────────────────────────────────
cmd_status() {
  header "Service Status"

  echo ""
  if launchctl list 2>/dev/null | grep -q "$PLIST_LABEL"; then
    ok "launchd service: running"
  else
    warn "launchd service: not running"
    dim "Start with: launchctl load ~/Library/LaunchAgents/com.youtube-summarizer.plist"
  fi

  echo ""
  section "Database:"
  "$PYTHON" - <<PYEOF
import sqlite3, pathlib
db = pathlib.Path("$REPO_ROOT/data/state.db")
if db.exists():
    con = sqlite3.connect(db)
    total = con.execute("SELECT COUNT(*) FROM seen_videos").fetchone()[0]
    print(f"    Videos processed (all time): {total}")
    recent = con.execute(
        "SELECT COUNT(*) FROM seen_videos WHERE seen_at > datetime('now', '-7 days')"
    ).fetchone()[0]
    print(f"    Processed last 7 days:       {recent}")
    con.close()
else:
    print("    Database not found (no runs yet).")
PYEOF

  echo ""
  section "Configured feeds:"
  "$PYTHON" - <<PYEOF
import tomllib, pathlib
try:
    with open("$REPO_ROOT/config/channels.toml", "rb") as f:
        cfg = tomllib.load(f)
    subs = cfg.get("subscriptions", [])
    print(f"    Subscriptions: {len(subs)}")
    for s in subs:
        p = s.get("prompts") or []
        label = ", ".join(p) if p else "all enabled"
        print(f"      • {s.get('name', '(unnamed)')}  [{label}]")
    sq = cfg.get("summarize_queue", {})
    if sq.get("url"):
        p = sq.get("prompts") or []
        label = ", ".join(p) if p else "all enabled"
        print(f"    Summarize queue: {sq.get('name', '(unnamed)')}  [{label}]")
    else:
        print("    Summarize queue: not configured")
    tq = cfg.get("transcribe_queue", {})
    print(f"    Transcribe queue: {'configured' if tq.get('url') else 'not configured'}")
except Exception as e:
    print(f"    Error reading config: {e}")
PYEOF

  echo ""
  section "Recent logs:"
  for log in /tmp/youtube-summarizer.out.log /tmp/youtube-summarizer.err.log; do
    if [ -f "$log" ] && [ -s "$log" ]; then
      gum style --foreground "$DIM" "  $(basename "$log"):"
      tail -10 "$log" | while IFS= read -r line; do
        echo "    $line"
      done
      echo ""
    fi
  done
}

# ── 7. settings ───────────────────────────────────────────────────────────────
cmd_settings() {
  header "Settings"

  # Load existing values from .env
  local email_from="" email_to="" ollama_model="" parakeet_model=""
  if [ -f "$ENV_FILE" ]; then
    email_from=$(grep   '^YTS_EMAIL_FROM='    "$ENV_FILE" 2>/dev/null | cut -d= -f2- | tr -d '"' || echo "")
    email_to=$(grep     '^YTS_EMAIL_TO='      "$ENV_FILE" 2>/dev/null | cut -d= -f2- | tr -d '"' || echo "")
    ollama_model=$(grep '^YTS_OLLAMA_MODEL='  "$ENV_FILE" 2>/dev/null | cut -d= -f2- | tr -d '"' || echo "")
    parakeet_model=$(grep '^YTS_PARAKEET_MODEL=' "$ENV_FILE" 2>/dev/null | cut -d= -f2- | tr -d '"' || echo "")
  fi

  section "Email from (your Gmail address):"
  email_from=$(gum input --value "$email_from" --placeholder "you@gmail.com" --width 50)

  section "Email to (recipient address):"
  email_to=$(gum input --value "$email_to" --placeholder "you@gmail.com" --width 50)

  section "Gmail app password:"
  dim "Generate at: myaccount.google.com/apppasswords"
  local gmail_pw
  gmail_pw=$(gum input --password --placeholder "xxxx xxxx xxxx xxxx" --width 50)

  section "Ollama model:"
  ollama_model=$(gum input --value "${ollama_model:-qwen2.5:14b}" --placeholder "qwen2.5:14b" --width 40)

  section "Parakeet model (transcription):"
  parakeet_model=$(gum input --value "${parakeet_model:-mlx-community/parakeet-tdt-0.6b-v3}" --width 60)

  echo ""
  gum confirm "  Save settings to .env?" || { warn "Cancelled."; return; }

  # Preserve any other existing vars, update ours
  local tmp
  tmp=$(mktemp)
  [ -f "$ENV_FILE" ] && grep -Ev '^(YTS_EMAIL_FROM|YTS_EMAIL_TO|YTS_GMAIL_APP_PASSWORD|YTS_OLLAMA_MODEL|YTS_PARAKEET_MODEL)=' "$ENV_FILE" > "$tmp" 2>/dev/null || true
  {
    echo "YTS_EMAIL_FROM=\"$email_from\""
    echo "YTS_EMAIL_TO=\"$email_to\""
    [ -n "$gmail_pw" ] && echo "YTS_GMAIL_APP_PASSWORD=\"$gmail_pw\""
    [ -n "$ollama_model" ]    && echo "YTS_OLLAMA_MODEL=\"$ollama_model\""
    [ -n "$parakeet_model" ]  && echo "YTS_PARAKEET_MODEL=\"$parakeet_model\""
  } >> "$tmp"
  mv "$tmp" "$ENV_FILE"

  ok "Settings saved to .env"
}

# ── main menu ─────────────────────────────────────────────────────────────────
main() {
  while true; do
    header "Setup & Management"

    local choice
    choice=$(gum choose \
      "➕  Subscribe to channel or playlist" \
      "📼  Manage transcribe queue"          \
      "📋  Manage summarize queue"           \
      "⚙️   Manage subscriptions"             \
      "▶️   Run now"                           \
      "📊  Service status"                   \
      "🔧  Settings"                         \
      "╌╌  Exit")

    echo ""
    case "$choice" in
      "➕"*)  cmd_subscribe            ;;
      "📼"*)  cmd_add_transcribe_queue ;;
      "📋"*)  cmd_add_summarize_queue  ;;
      "⚙️"*)   cmd_manage              ;;
      "▶️"*)   cmd_run_now             ;;
      "📊"*)  cmd_status               ;;
      "🔧"*)  cmd_settings             ;;
      "╌╌"*)  exit 0                   ;;
    esac

    echo ""
    gum confirm "  Back to main menu?" || exit 0
  done
}

main

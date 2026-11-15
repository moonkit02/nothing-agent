#!/bin/bash
# Run one brain action on the phone over adb.
# Usage: act.sh <adb-serial> <intent> <query>
#   play_music  search YT Music, tap the top result's Play (song) or Shuffle play (artist), then bring back the app that was in front
#   navigate    start Waze turn-by-turn to <query> ("home" = Waze saved Home)
#   media       pause | play | next | previous
#   volume      signed steps, e.g. -2 or +2 (max 15)
set -euo pipefail
serial=$1; intent=$2; query=$3

# Git Bash on Windows: leave /sdcard/... alone for adb, but still convert /tmp/... for adb.exe/python.exe.
case "$(uname -s)" in MINGW*|MSYS*) export MSYS2_ARG_CONV_EXCL="/sdcard" ;; esac

# Kill switch (Pause button on the config page): while this file exists, touch nothing.
[ -e "$(dirname "$0")/paused" ] && { echo "act.sh: paused, not touching the phone" >&2; exit 3; }

# Safe stop: no action may run longer than this. The hard kill switch is on the phone:
# turning off Wireless debugging cuts adb, so nothing here can touch the phone.
MAX_SECONDS=45
( sleep "$MAX_SECONDS"; echo "act.sh: over ${MAX_SECONDS}s, killed" >&2; kill -TERM $$ 2>/dev/null ) &
watchdog=$!
# Kill the watchdog's sleep too, or it lives on and later signals a reused PID.
# "|| true": Git Bash has no pkill, and a failing trap would turn every success into exit 127.
trap 'pkill -P $watchdog 2>/dev/null || true; kill $watchdog 2>/dev/null || true' EXIT
adb_cmd=(adb -s "$serial")
YT=com.google.android.apps.youtube.music
WAZE=com.waze

phone() { "${adb_cmd[@]}" shell "$@" </dev/null; }  # </dev/null: adb shell would eat the caller's stdin
encode() { python3 -I -c 'import sys, urllib.parse; print(urllib.parse.quote_plus(sys.argv[1]))' "$1"; }

front_pkg() {
  phone dumpsys activity activities | grep -m1 topResumedActivity | grep -oE 'u0 [^/ ]+' | cut -d' ' -f2 || true
}

# Top search result's button: "Play <song>" for a song, "Shuffle play" for an artist. Both sit at the
# same spot, so one fixed tap covers both (measured 2026-11-14 on the Nothing Phone 3a, 1080x2392,
# 5 queries). Much faster than reading the screen with uiautomator. Re-measure if YT Music changes layout.
PLAY_X=307; PLAY_Y=675
PLAY_WAIT=${PLAY_WAIT:-2}  # seconds for the results to load before tapping

play_music() {
  local prev
  prev=$(front_pkg)
  phone am start -a android.intent.action.VIEW -p "$YT" -d "'https://music.youtube.com/search?q=$(encode "$query")'" >/dev/null
  sleep "$PLAY_WAIT"
  phone input tap $PLAY_X $PLAY_Y
  # Give back the screen (e.g. navigation while driving).
  if [ -n "$prev" ] && [ "$prev" != "$YT" ]; then
    sleep 1; phone monkey -p "$prev" -c android.intent.category.LAUNCHER 1 >/dev/null 2>&1
  fi
  echo "playing: $query (restored: ${prev:-none})"
}

saved_place() {
  # Exact name match in places.txt ("name = where"), comments skipped.
  awk -v k="$1" -F'[[:space:]]*=[[:space:]]*' '!/^[[:space:]]*#/ && $1 == k { print $2; exit }' \
    "$(dirname "$0")/places.txt" 2>/dev/null
}

navigate() {
  # "home" = Home saved in Waze; a places.txt name = its coordinates or search text; else a Waze search.
  local where target
  where=$(saved_place "$query")
  if [ "$query" = home ]; then target="favorite=home"
  elif [[ $where =~ ^-?[0-9]+(\.[0-9]+)?,[[:space:]]*-?[0-9]+(\.[0-9]+)?$ ]]; then target="ll=${where//[[:space:]]/}"
  else target="q=$(encode "${where:-$query}")"
  fi
  phone am start -a android.intent.action.VIEW -p "$WAZE" -d "'https://waze.com/ul?$target&navigate=yes'" >/dev/null
  echo "navigating: $query ($target)"
}

media() {
  # Send straight to the active media session: "input keyevent" goes to the front window
  # and never reached YT Music (tested). No tapping, so Waze stays in front.
  case $query in
    pause|play|next|previous) phone cmd media_session dispatch "$query" ;;
    *) echo "bad media query: $query" >&2; exit 2 ;;
  esac
  echo "media: $query"
}

volume() {
  # query is untrusted model output: accept only a signed small number.
  [[ $query =~ ^[+-]?[0-9]{1,2}$ ]] || { echo "bad volume query: $query" >&2; exit 2; }
  local n=$((10#${query#[+-]})) key=VOLUME_UP
  [[ $query == -* ]] && key=VOLUME_DOWN
  (( n > 15 )) && n=15
  for _ in $(seq 1 "$n"); do phone input keyevent "KEYCODE_$key"; done
  echo "volume: $query"
}

case $intent in
  play_music) play_music ;;
  navigate) navigate ;;
  media) media ;;
  volume) volume ;;
  *) echo "unsupported intent: $intent" >&2; exit 2 ;;
esac

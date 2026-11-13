#!/bin/bash
# Run one brain action on the phone over adb.
# Usage: act.sh <adb-serial> <intent> <query>
#   play_music  search YT Music, tap the top result's Play (song) or Shuffle play (artist), then bring back the app that was in front
#   navigate    start Waze turn-by-turn to <query> ("home" = Waze saved Home)
#   media       pause | play | next | previous
#   volume      signed steps, e.g. -2 or +2 (max 15)
set -euo pipefail
serial=$1; intent=$2; query=$3
adb_cmd=(adb -s "$serial")
YT=com.google.android.apps.youtube.music
WAZE=com.waze

phone() { "${adb_cmd[@]}" shell "$@" </dev/null; }  # </dev/null: adb shell would eat the caller's stdin
encode() { python3 -I -c 'import sys, urllib.parse; print(urllib.parse.quote_plus(sys.argv[1]))' "$1"; }

front_pkg() {
  phone dumpsys activity activities | grep -m1 topResumedActivity | grep -oE 'u0 [^/ ]+' | cut -d' ' -f2 || true
}

find_play_button() {
  # Find the button by its label, not a fixed position: results layout changes per query.
  local xml; xml=$(mktemp)
  phone uiautomator dump /sdcard/ui.xml >/dev/null 2>&1
  "${adb_cmd[@]}" pull /sdcard/ui.xml "$xml" >/dev/null 2>&1 </dev/null
  # Only trust the screen once the search box shows this query; else we may tap the previous search's results.
  python3 -I -c '
import sys, re, xml.etree.ElementTree as ET
nodes = list(ET.parse(sys.argv[1]).iter("node"))
if any((n.get("text") or "").strip().lower() == sys.argv[2].strip().lower() for n in nodes):
    for n in nodes:
        # Song top result shows "Play <title>"; artist top result shows "Shuffle play".
        d = n.get("content-desc") or ""
        if d.startswith("Play ") or d == "Shuffle play":
            x1, y1, x2, y2 = map(int, re.findall(r"\d+", n.get("bounds")))
            print((x1 + x2) // 2, (y1 + y2) // 2); break
' "$xml" "$query" 2>/dev/null || true
  rm -f "$xml"
}

play_music() {
  local prev xy
  prev=$(front_pkg)
  phone am start -a android.intent.action.VIEW -p "$YT" -d "'https://music.youtube.com/search?q=$(encode "$query")'" >/dev/null
  for _ in $(seq 1 10); do
    xy=$(find_play_button); [ -n "$xy" ] && break; sleep 1
  done
  [ -z "$xy" ] && { echo "no Play button found for: $query" >&2; exit 1; }
  phone input tap $xy
  # Give back the screen (e.g. navigation while driving).
  if [ -n "$prev" ] && [ "$prev" != "$YT" ]; then
    sleep 1; phone monkey -p "$prev" -c android.intent.category.LAUNCHER 1 >/dev/null 2>&1
  fi
  echo "playing: $query (restored: ${prev:-none})"
}

navigate() {
  # "home" uses the Home saved in Waze; anything else is a Waze search.
  local target="q=$(encode "$query")"
  [ "$query" = home ] && target="favorite=home"
  phone am start -a android.intent.action.VIEW -p "$WAZE" -d "'https://waze.com/ul?$target&navigate=yes'" >/dev/null
  echo "navigating: $query"
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

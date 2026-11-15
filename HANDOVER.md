# HANDOVER: nothing-agent (2026-11-14, home Windows PC)

Read this, then TODO.md (decisions, next steps, voice results). PREREQ.md is the new-machine setup list.
The `.vibe-wise/` notes are older than this file; where they differ, this file is right.

## What it is
Personal voice assistant for the Nothing Phone 3a (model A059). Speak Mandarin + English rojak,
the PC works out the actions and drives the phone over adb. Wake word: **"Apollo"** (was "Bossku",
changed 2026-11-14 because "bossku" is everyday Malaysian speech).

```
phone Chrome page  https://asus-tuf-f15.tailddf27e.ts.net   (mic + simple VAD; screen must stay on)
  -> tailscale serve (HTTPS, tailnet only) -> brain.mjs 127.0.0.1:8080   (token, /pause, /parse, /listen proxy)
  -> listen.py 127.0.0.1:8081: voiceprint (3D-Speaker, shadow mode) -> SenseVoice speech-to-text
       -> wake word regex -> brain /parse (Claude subscription) -> act.sh per action
  -> act.sh: adb to the phone at 100.99.1.104:5555 over Tailscale (works on 4G)
```

## State (verified on the real phone unless marked)
| Part | File | Notes |
|---|---|---|
| Brain | `brain.mjs` | Agent SDK on the subscription, no tools, 1 turn, max 5 actions. Listens on 127.0.0.1 only now; reach it through `tailscale serve`. `/listen` proxies to listen.py |
| Listen | `listen.py` | Body = float32 16 kHz PCM. Logs every utterance to `voice-samples/listen-log.jsonl` (gitignored). `SPEAKER_ENFORCE=1` to block non-matching voices (default: log only) |
| Phone actions | `act.sh` | play_music now = search deep link, wait 2 s, tap (307,675). Same spot for song ("Play X") and artist ("Shuffle play") results. Exits 3 while `paused` exists |
| Page | `editor.html` | Pause/Resume button, Start listening + level meter + what it heard, places.txt editor |
| Voice test | `voice-test.py` | `python voice-test.py` compares all clips; `python voice-test.py <clip>` = PASS/REJECT one clip |
| Kill switch | `paused` file | Page button. Claude must not run act.sh or any phone adb while it exists (user rule) |

Commits: `2a8ca0c` (pause + Windows act.sh) is local, **not pushed** (this PC has no GitHub login yet:
`git credential-manager github login`). Everything after it is uncommitted at the time of writing.

## Not done (top of the list), details in TODO.md
1. The user found the web listening "not very stable". Last fixes (VAD floor, pre-roll, meter, looser
   wake word) were not tried by the user yet.
2. Wake word via regex on speech-to-text is the weak part. Next: sherpa-onnx keyword spotting.
3. Android app with an always-on mic (user wants it; reuse /listen).
4. Speaker check: shadow mode; more and other-day recordings needed before enforcing.

## Agent skills to bring up (user asked: mention this when reading this file)
Vercel's agent skills, looked at on 2026-11-15, not installed yet:
- `vercel-labs/agent-skills` (official collection, agentskills.io format, works in Claude Code).
  Relevant here: `web-design-guidelines` (audit `editor.html`: accessibility, focus, forms, dark mode)
  and `react-native-skills` (if the Android app is written in React Native / Expo).
  Others (react-best-practices, composition-patterns, react-view-transitions, writing-guidelines,
  vercel-optimize, deploy-to-vercel, vercel-cli-with-tokens) are React- or Vercel-specific.
- `vercel-labs/skills` = the `npx skills` CLI (needs Node 22.20+): install, find, update skills.
  `npx skills add vercel-labs/agent-skills --skill web-design-guidelines -a claude-code` (add `-g` for
  all projects); `npx skills use <repo>@<skill> --agent claude-code` to try one without installing.
  Sends anonymous telemetry unless `DISABLE_TELEMETRY=1`.
Ask the user whether to install, and project vs global (`-g`).

## How to run (home PC, PowerShell)
```
# token: 6 digits, the user knows it (not written here: this repo is public). Pick a new one if lost.
$env:BRAIN_TOKEN = "<token>"
cd C:\Claude\nothing-agent; node brain.mjs                       # 127.0.0.1:8080
$env:PHONE_SERIAL = "100.99.1.104:5555"; $env:PYTHONUTF8 = "1"
.\.venv\Scripts\python.exe -u listen.py                          # 127.0.0.1:8081, loads models ~10 s
& "C:\Program Files\Tailscale\tailscale.exe" serve status        # should proxy / -> http://127.0.0.1:8080
adb connect 100.99.1.104:5555
```
Both services run as background tasks of a Claude Code session: they stop when that session ends.

Phone restarted? `adb tcpip 5555` is gone. On home Wi-Fi: turn on Wireless debugging,
`adb mdns services` (port changes every time), `adb connect <ip:port>`, `adb -s <ip:port> tcpip 5555`,
then `adb connect 100.99.1.104:5555`. This PC is already paired.

## Home PC (Windows 11, Tailscale name asus-tuf-f15, 100.118.27.117)
- Installed 2026-11-14 with winget: Git 2.56, Node 26 LTS, Android platform-tools (adb), Python 3.13
  (+ a copy `python3.exe` next to `python.exe`: act.sh calls `python3`, and Windows otherwise runs the
  Microsoft Store stub), Tailscale 1.104. `.venv/`: sherpa-onnx 2.0.1, numpy, soundfile, av.
- `models/` (gitignored): 3D-Speaker CAM++ zh/en (used), WeSpeaker en (dropped), SenseVoice zh/en/ja/ko/yue.
- Git identity: moonkit02 / GitHub noreply email. No push login yet.
- Firewall rule "nothing-agent brain (Tailscale only)", TCP 8080 inbound: no longer needed since the
  brain is localhost-only. Can be deleted.
- `tailscale serve` was enabled for the tailnet on 2026-11-14.
- Claude Code was run as admin once (to add that firewall rule). Not needed any more.
- ~90 GB free.

## Gotchas learned the hard way
- Wireless debugging turns itself off when the phone leaves Wi-Fi. Use `adb tcpip 5555` (survives
  network changes, not a phone restart). No pairing on 5555: only reachable inside the tailnet.
- `tailscale serve` on Windows cannot proxy to the PC's own 100.x address (502 after 21 s). Proxy to 127.0.0.1.
- Chrome only gives the mic to HTTPS pages: that is why the page moved to the ts.net address.
- Chrome noise suppression / auto gain lowered voiceprint scores (~0.55 live vs ~0.7 recorded).
  Turned off; without auto gain the mic is quiet, so the VAD floor had to go down to 0.005.
- SenseVoice spells "Apollo" as 啊菠萝, 啊，菠萝, 阿波路, Abo, Apooos. Wake regex needs the 啊/阿 start
  so plain 菠萝 does not wake it. Brain prompt also told to ignore those spellings and fix mishearings.
- YT Music ignores `MEDIA_PLAY_FROM_SEARCH` sent with `am start` (nothing plays). Use search + tap.
- `dumpsys media_session`: the first session listed is not always YT Music; grep its package block.
- Git Bash turns `/sdcard/...` into a Windows path for adb.exe: act.sh sets `MSYS2_ARG_CONV_EXCL=/sdcard`
  (not `MSYS_NO_PATHCONV`, which also breaks mktemp's `/tmp` paths for adb.exe/python.exe).
- Git Bash has no `pkill`; act.sh's EXIT trap ends with `|| true` or every success becomes exit 127.
- Windows Python prints `\r\n` and cp1252: when piping its output into bash, use
  `sys.stdout.reconfigure(encoding="utf-8", newline="\n")` (`-I` ignores `PYTHONUTF8`). A stray `\r`
  once sent Waze a search for "home\r" instead of the saved Home.
- Nothing Recorder saves to `Android/data/com.nothing.soundrecorder/files/*.aac`; each file starts
  with one broken AAC packet (voice-test.py skips it).
- zsh does not split `$VAR` into words: `A="adb -s x"; $A shell` fails. Use bash or arrays.
- `adb shell` eats stdin: inside a heredoc or `while read` loop, add `</dev/null` to every adb call.
- `input keyevent` media keys did not reach YT Music; `cmd media_session dispatch` does.
- `cmd media_session volume --get` reads the wrong stream; read `dumpsys audio`, STREAM_MUSIC, `2 (speaker)`.
- Google Maps result text is not exposed to uiautomator; Waze search results are.
- Android redacts coordinates in `dumpsys location`, so the PC cannot know the phone location.
- WhatsApp UI dumps contain contact names in picture descriptions: filter output to controls only.

## Work laptop (Mac), from the 2026-11-13 handover
- adb installed via brew. Tailscale app deleted; its network extension may still show until a reboot.
- Disk ~99% full: voice work moved to the home PC.

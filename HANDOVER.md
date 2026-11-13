# HANDOVER: nothing-agent (2026-11-13)

Read this, then TODO.md (decisions, next steps, voice experiment plan and recording list).
The `.vibe-wise/` notes are older than this file; where they differ, this file is right.

## What it is
Personal voice assistant for the Nothing Phone 3a (model A059). Speak Malaysian rojak, the PC
works out the actions and drives the phone over adb. Wake word will be "Bossku" ("nothing" is
the test word only).

```
phone (trigger + speech-to-text: NOT BUILT)
  -> brain.mjs on PC: text -> {"actions":[{intent, query}, ...]}   (Claude subscription)
  -> act.sh on PC: runs each action on the phone over Wi-Fi adb     (NOT YET CALLED BY THE BRAIN)
```

## State: everything below is verified on the real phone
| Part | File | Notes |
|---|---|---|
| Brain | `brain.mjs` | Agent SDK on the subscription, no tools, 1 turn, max 5 actions, token guard. Intents: play_music, navigate, media, volume, unknown |
| Saved places | `places.txt` | `name = lat,lng` or `name = Waze search text`. Brain maps spoken names (简/繁, English) to these; read per request |
| Phone actions | `act.sh <serial> <intent> <query>` | YT Music via search deep link + tap top "Play …"/"Shuffle play" by label, then restores previous app (Waze). Waze: `favorite=home`, `ll=`, `q=`. Media via `cmd media_session dispatch`. Volume via keyevents. 45 s watchdog |
| Config page | `editor.html` served at `GET /` | `/files`, `/file` GET/PUT, token, whitelist (places.txt), 64 KB cap, `.bak` on save. `BRAIN_HOST` to expose; refuses without `BRAIN_TOKEN` |

Commits (local only, never pushed): cadf139 … 50ecc58.

## Not done (top of the list)
1. Wiring: the brain does not run act.sh yet. All runs so far were manual (curl, then act.sh).
2. No trigger on the phone at all. Saying a wake word does nothing today.
   Stopgap idea: command box on the web page + Gboard mic. Real one: native app (always-on mic).
3. Voice experiment: user is recording samples into phone folder `Recordings/voice-test/`
   (list in TODO.md). Plan: sherpa-onnx (wheels 2.1 + 9.5 MB, no PyTorch) and compare
   `3dspeaker_speech_campplus_sv_zh_en_16k-common_advanced.onnx` (28.3 MB) vs
   `wespeaker_en_voxceleb_CAM++.onnx` (29.3 MB), from GitHub release tag
   `speaker-recongition-models` (the typo is the real tag). Fits on this Mac. Not installed yet.
   Samples go to `voice-samples/` (gitignored, biometric).
4. Out-of-home over 4G: Tailscale + `adb tcpip 5555`, to test on the home PC.
5. WhatsApp: contact lookup + `wa.me/<number>` opens the chat (verified). `input text` cannot
   type Chinese. A sticker was tapped in a real contact's chat; sending was not confirmed.

## How to run
```
cd nothing-agent && npm install          # once
BRAIN_TOKEN=<secret> node brain.mjs      # localhost only
BRAIN_HOST=<LAN or Tailscale IP> BRAIN_TOKEN=<secret> node brain.mjs   # reachable from the phone
adb mdns services                        # find the phone, port changes every time
adb connect <ip:port>                    # no pairing needed while this Mac's key is trusted
./act.sh <ip:port> play_music "晴天 周杰伦"
```
Phone: Developer options > Wireless debugging must be ON (it turns itself off on network changes).

## Gotchas learned the hard way
- zsh does not split `$VAR` into words: `A="adb -s x"; $A shell` fails. Use bash or arrays.
- `adb shell` eats stdin: inside a heredoc or `while read` loop, add `</dev/null` to every adb call.
- `input keyevent` media keys did not reach YT Music; `cmd media_session dispatch` does.
- `cmd media_session volume --get` reads the wrong stream; read `dumpsys audio`, STREAM_MUSIC, `2 (speaker)`.
- After an `am start` to YT Music, the old results page can still be on screen: act.sh waits
  until the search box text equals the query before tapping.
- Google Maps result text is not exposed to uiautomator; Waze search results are.
- Android redacts coordinates in `dumpsys location` (`3.*** 101.***`), so the PC cannot know the
  phone location.
- WhatsApp UI dumps contain contact names in picture descriptions: filter output to controls only.

## This Mac (work laptop), housekeeping
- Installed today: `android-platform-tools` (adb) via brew. Still installed.
- Tailscale: removed (app deleted by the user). Its network extension still lists as
  "waiting for user"; expected to clear after a reboot (not verified).
- Disk is ~99% full (~2.5 GB free). Check before installing anything big.
- Test token `testsecret` was used only for local tests; Chrome on the phone offered to save it,
  user was told to decline. Use a real secret.

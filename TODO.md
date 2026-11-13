# nothing-agent TODO

## Decisions (2026-11-13)
- Wake word: **"Bossku"** ("nothing" was for testing only). Say "Hey Bossku" to make it longer.
  Known risk: "bossku" is common in Malaysian speech and media, so expect false triggers.
  Defences: two-turn (wake word, beep, then command), speaker verification, action whitelist.
- Config editing: web page served by the brain (editor.html). Native app only for the trigger
  (always-on mic needs a foreground service; a web page cannot do it).
- Navigation: Waze. Saved places: places.txt, kept by the user.
- PC is the always-on home "Jarvis": runs the brain and drives the phone over adb.

## Done and verified
- Brain on the subscription, multi-action output, saved-place name matching.
- act.sh: play_music (song or artist shuffle, restores the previous app), navigate (Waze,
  home, places.txt coords or search), media (pause/play/next/previous), volume.
- Safe stop: 45s per action, max 5 actions per command.
- Config page on the phone with token, whitelist, size cap, .bak.

## Next
1. [ ] Wiring: brain runs act.sh itself; find the phone's adb port automatically (adb mdns).
2. [ ] Stopgap trigger: command box on the web page, use the Gboard mic to dictate.
3. [ ] Out-of-home: Tailscale on home PC + phone, test `adb tcpip 5555` over 4G.
4. [ ] Check the phone has the Wireless debugging Quick Settings tile (hard kill switch).
5. [ ] When "bossku" replaces "nothing": update the wake word in brain.mjs SYSTEM prompt.
6. [ ] WhatsApp: open chat works (contacts -> wa.me). Sending Chinese text not tested;
       `input text` cannot type Chinese. Sticker send to a contact looked sent, not confirmed.

## Experiment: voice (needs the home PC, this Mac has ~2.6 GB free)
Goal: (a) can a speaker-verification model separate my voice from others, Malaysian accent
included; (b) does a wake word engine hear my "Hey Bossku".
- Recordings: phone voice recorder, saved in phone folder `Recordings/voice-test/`, pulled with
  adb into `voice-samples/` (gitignored: biometric data, never commit). One clip per file,
  1 s of silence before and after, phone in its normal spot (hand or car mount).
  - A. enrolment, quiet room: `enrol-1..5`
    1. 今天天气很热，我等下要去 mamak 吃 roti canai。
    2. Hey Bossku, play some Jay Chou songs and turn the volume up a bit.
    3. Saya nak pergi KLCC petang ini, jalan jem tak?
    4. 帮我打电话给妈妈，跟她讲我七点钟回到家。
    5. Free talk for 10 s, like chatting with a friend.
  - B. mine, "Hey Bossku + command", 5 each: `me-quiet-*`, `me-tv-*` (TV/YouTube on),
    `me-car-music-*` (music on, phone on mount), `me-car-window-*` (window open or strong
    aircon), `me-tired-*` (tired, just woke up, or quiet voice)
  - C. mine, casual "bossku" not meant to trigger: `me-casual-1..5` (wake word false triggers;
    speaker verification cannot block these)
  - D. others, ask them first: `other-<name>-1..3` (include one person of my gender and age),
    `other-yt-1..5` (Malaysian speakers from YouTube, ~10 s each)
  - E. optional: `noise-radio`, 30+ min of car radio with nobody talking
- Speaker verification: score every clip against my enrolment. Pass only if one threshold
  separates mine from others. Candidates: SpeechBrain ECAPA (needs PyTorch, GBs) or
  sherpa-onnx speaker embedding (lighter, size and accuracy not yet checked).
- Wake word: count misses (say it 20x in the car) and false triggers (1-2 h of radio/YouTube).
- Roll-out: log scores only ("shadow mode") for 1-2 weeks before blocking anything.
  Not a security control: a recording can fool it.

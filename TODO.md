# nothing-agent TODO

## Decisions (2026-11-13)
- Wake word: **"Apollo"** (changed from "Bossku" on 2026-11-14; "nothing" was for testing only).
  Say "Hey Apollo" to make it longer. Why not Bossku: "bossku" is common in Malaysian speech
  and media, so it would false-trigger a lot; "Apollo" is rare in daily talk.
  Defences still apply: two-turn (wake word, beep, then command), speaker verification, action whitelist.
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
- (2026-11-14, home Windows PC) Out-of-home over 4G: Tailscale + `adb tcpip 5555`, play_music and
  media pause run end to end with the phone on LTE only.
- (2026-11-14) Pause kill switch: button on the page, `paused` file, act.sh exits 3 while it exists.
- (2026-11-14) play_music: one fixed tap (307,675) for both song and artist results, 3.5-5.5 s (was 4.5-8 s).
- (2026-11-14) Wiring + web trigger: page "Start listening" -> listen.py -> STT -> wake word -> brain -> act.sh.
  Works, but "not very stable" (user): see Next 1-2.

## Next
1. [ ] Test tonight's last fixes on the phone (not tried by the user yet): VAD floor 0.005, 0.6 s
       pre-roll, level meter, looser wake word (啊，菠萝 / Abo).
2. [ ] Wake word: replace "regex on SenseVoice text" with sherpa-onnx keyword spotting (KWS) for
       Apollo / 阿波罗. STT spelled Apollo 6 ways in 4 tries (啊菠萝, 阿波路, Abo, Apooos…).
3. [ ] Android app: foreground service (mic), always listening with the screen off, sends utterances
       to the same /listen (or runs KWS on the phone and only sends after the wake word).
4. [ ] Speaker check is in shadow mode (logged, not enforced). Live page clips scored ~0.55 with
       Chrome noise suppression/AGC; both now off, effect not measured yet. Decide enforce after 1-2 weeks.
5. [ ] Check the phone has the Wireless debugging Quick Settings tile (hard kill switch).
6. [x] Wake word "Apollo" in the brain.mjs SYSTEM prompt (incl. STT spellings).
7. [ ] WhatsApp: open chat works (contacts -> wa.me). Sending Chinese text not tested;
       `input text` cannot type Chinese. Sticker send to a contact looked sent, not confirmed.
8. [ ] brain.mjs exited once with code 4 and no message (while the user was out). Unknown cause;
       consider running brain + listen.py under a restart loop or as a Windows service.

## Experiment: voice (needs the home PC, this Mac has ~2.6 GB free)
Goal: (a) can a speaker-verification model separate my voice from others, Malaysian accent
included; (b) does a wake word engine hear my "Hey Apollo".
- Recordings: phone voice recorder, saved in phone folder `Recordings/voice-test/`, pulled with
  adb into `voice-samples/` (gitignored: biometric data, never commit). One clip per file,
  1 s of silence before and after, phone in its normal spot (hand or car mount).
  - A. enrolment, quiet room: `enrol-1..5`
    1. 今天天气很热，我等下要去 mamak 吃 roti canai。
    2. Hey Apollo, play some Jay Chou songs and turn the volume up a bit.
    3. Saya nak pergi KLCC petang ini, jalan jem tak?
    4. 帮我打msg给mummy跟她讲我7点到
    5. Free talk for 10 s, like chatting with a friend.
  - A2. long enrolment, quiet room, normal speed (~60 s): `enrol-long-1` today, `enrol-long-2` another day.
    Mandarin + English only (user does not speak Malay to the assistant). Text:
    今天早上我七点半起床，外面在下雨，所以我决定 drive 去 office 而不是坐 LRT。路上好塞，Federal Highway
    又是一样的 jam，我等了快四十分钟才到 Mid Valley。一到 office，boss 就叫我们进去 meeting，说这个 project
    一定要在月底之前搞定。After the meeting, I went down to grab a teh tarik and some roti canai with my
    colleagues. 中午我们去吃了一间新开的 ramen 店，一碗要二十八块，有点贵但是汤头真的不错。下午我打电话给
    mummy，跟她讲周末会回 Ipoh 吃饭，顺便帮她修那个坏掉的 Wi-Fi router。After work, I'll probably go to the
    gym for an hour, then go home, feed the cat, and watch two episodes of that Korean drama. Apollo，set
    回家的路，帮我播周杰伦的稻香，然后音量大声一点。Okay lah, that's all for today, good night everyone.
  - B. mine, "Hey Apollo + command", 5 each: `me-quiet-*`, `me-tv-*` (TV/YouTube on),
    `me-car-music-*` (music on, phone on mount), `me-car-window-*` (window open or strong
    aircon), `me-tired-*` (tired, just woke up, or quiet voice)
  - C. mine, casual "apollo" not meant to trigger ("apollo上月球真的假的哦，可是我家的猫叫apollo leh"): `me-casual-1..5` (wake word false triggers;
    speaker verification cannot block these)
  - D. others, ask them first: `other-<name>-1..3` (include one person of my gender and age),
    `other-yt-1..5` (Malaysian speakers from YouTube, ~10 s each)
  - E. optional: `noise-radio`, 30+ min of car radio with nobody talking
- Speaker verification: score every clip against my enrolment. Pass only if one threshold
  separates mine from others. Candidates: SpeechBrain ECAPA (needs PyTorch, GBs) or
  sherpa-onnx speaker embedding (lighter, size and accuracy not yet checked).
- Results 2026-11-14 (`voice-test.py`, sherpa-onnx 2.0.1, all clips recorded the same evening):
  - 3D-Speaker CAM++ zh/en: me 0.619..0.768, two younger brothers 0.318..0.464 (incl. one reading
    the same long text) -> SEPARATED, gap +0.155. Threshold 0.54. Long enrolment helped a little.
  - WeSpeaker CAM++ en: OVERLAP (brother above me). Dropped.
  - Live checks: 3 of 4 right. A very quiet/whispered command scored 0.32 (false reject).
  - Multi-voiceprint code is ready (enrol-soft-*, enrol-low-*, enrol-high-* each get their own
    print, best match wins) but those clips are not recorded: user chose to skip for now.
  - Still unknown: a different day's voice (record `enrol-long-2` and a few `me-quiet-*` another day),
    unrelated speakers (`other-yt-*`), more clips per scenario (only 1 each so far).
  - Nothing Recorder saves to `Android/data/com.nothing.soundrecorder/files/*.aac`, not `Recordings/`.
- Wake word: count misses (say it 20x in the car) and false triggers (1-2 h of radio/YouTube).
- Roll-out: log scores only ("shadow mode") for 1-2 weeks before blocking anything.
  Not a security control: a recording can fool it.

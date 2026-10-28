# drive-and-study

App to study while driving or in other audio-only situations.

The first prototype is a hands-free practice exam: questions are read aloud, you answer
by saying **one, two, three or four** (or tapping / pressing keys 1–4), and the app scores you,
plays the explanation and queues the questions you missed for review.

The runtime is deterministic, with no AI in the app. Audio is pre-rendered offline, and speech is
transcribed by the browser's own recognizer. The app only accepts a fixed vocabulary:
`one two three four repeat skip`, with a few common mis-hearings mapped (e.g. "for" → 4).

## Use it

The site has three pages:

- `/` is the home page. It lists the study pack.
- `/lessons` has 11 audio episodes: 8 lessons, 2 practice exams and a recap podcast. They play in order and the page remembers where you stopped.
- `/drill` is the voice drill: 20 questions read aloud, answered by voice, tap or keys.
- `/buttons` is a button test page. It keeps a quiet media session running and logs every
  steering-wheel or headset button that reaches the browser. Press *next* 1–4 times to try the
  answer-by-buttons gesture, which uses no microphone.

Open it in **Chrome** (Android, Windows, Mac) or **Safari** (iPhone, Mac).

- The microphone only works when the page is served over **HTTPS**. It does not work inside
  chat-app file previews or embedded frames.
- iPhone: *Settings → Siri & Dictation* must be enabled for speech recognition.
- In the drill, run **Test microphone** first. It shows what was heard and how it was read.
- Voice commands: `one`–`four`, `repeat`, `skip`. Keys: `1`–`4`, `R`, `S`, `Space` (pause).
  Headset or steering-wheel *previous* / *next* buttons map to repeat / skip.
- Progress and the review queue are stored in the browser (localStorage) on that device only.

## Layout

```
public/                           what Vercel serves (committed, no build step on deploy)
  index.html                      home page (hand-written)
  drill.html                      voice drill (generated)
  lessons.html                    lessons player (generated)
  buttons.html                    media-button test page (hand-written)
  audio/lessons/ep1..11.mp3       lesson audio (64 kbps mono)
  audio/test/quiet.mp3            near-silent loop that keeps the button test the active media player
app/template.html                 voice drill UI + state machine (questions and clips injected)
app/lessons.html                  lessons player UI
content/<pack>/source/*.txt       practice-exam scripts (question, options A–D, [THINK], explanation)
content/<pack>/questions.json     parsed questions (answers balanced over 1–4)
content/<pack>/clips/*.mp3        drill speech clips
content/<pack>/lessons/ep*.txt    lesson scripts (ep11 is the two-host recap podcast)
tools/parse.py                    source/*.txt -> questions.json
tools/gen_clips.py                questions.json -> clips/*.mp3 (Kokoro offline TTS)
tools/gen_lesson.py               single-voice lesson script -> wav
tools/gen_podcast.py              two-host podcast script -> wav
tools/build.py                    templates + pack -> public/drill.html, public/lessons.html
tests/smoke_tap.py                drill: full session by keyboard, review queue
tests/smoke_voice.py              drill: voice paths with a fake speech engine
tests/smoke_site.py               site: home, lessons player, cross-links, audio files, button-test gesture
```

## Build

```bash
python3 tools/parse.py content/togaf-foundation       # only if source/*.txt changed
python3 tools/gen_clips.py content/togaf-foundation    # only if questions changed (needs models/, see script header)
python3 tools/build.py content/togaf-foundation        # writes public/drill.html and public/lessons.html
python3 tests/smoke_tap.py && python3 tests/smoke_voice.py && python3 tests/smoke_site.py   # pip install playwright
```

## Deploy (Vercel)

Vercel deploys `main` to production and every PR to a preview URL. `vercel.json` serves `public/`
with clean URLs (`/drill`, `/lessons`), a `Permissions-Policy: microphone=(self)` header and `noindex`.

## Content and licensing

The `togaf-foundation` pack is original practice material written against the public TOGAF®
Enterprise Architecture Foundation syllabus. It contains no real exam questions. TOGAF is a
registered trademark of The Open Group. This project is not affiliated with or endorsed by The Open Group.
Commercial use of TOGAF content may require a TOGAF commercial license, so keep deployments
private/unlisted until that is settled.

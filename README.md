# drive-and-study

App to study while driving or in other audio-only situations.

The first prototype is a hands-free practice exam: questions are read aloud, you answer
by saying **one, two, three or four** (or tapping / pressing keys 1–4), and the app scores you,
plays the explanation and queues the questions you missed for review.

The runtime is deterministic, with no AI in the app. Audio is pre-rendered offline, and speech is
transcribed by the browser's own recognizer. The app only accepts a fixed vocabulary:
`one two three four repeat skip`, with a few common mis-hearings mapped (e.g. "for" → 4).

## Use it

Open the deployed `index.html` in **Chrome** (Android, Windows, Mac) or **Safari** (iPhone, Mac).

- The microphone only works when the page is served over **HTTPS** (or opened as a local file
  in desktop Chrome). It does not work inside chat-app file previews or embedded frames.
- iPhone: *Settings → Siri & Dictation* must be enabled for speech recognition.
- Run **Test microphone** on the start screen first. It shows what was heard and how it was read.
- Voice commands: `one`–`four`, `repeat`, `skip`. Keys: `1`–`4`, `R`, `S`, `Space` (pause).
  Headset or steering-wheel *previous* / *next* buttons map to repeat / skip.
- Progress and the review queue are stored in the browser (localStorage) on that device only.

## Layout

```
app/template.html                 UI + state machine (questions and audio injected at build)
content/<pack>/source/*.txt       question scripts (question, options A–D, [THINK], explanation)
content/<pack>/questions.json     parsed questions (answers balanced over 1–4)
content/<pack>/clips/*.mp3        pre-rendered speech clips
tools/parse.py                    source/*.txt -> questions.json
tools/gen_clips.py                questions.json -> clips/*.mp3 (Kokoro offline TTS)
tools/build.py                    template + pack -> index.html (single self-contained file)
tests/smoke_tap.py                full session by keyboard, review queue
tests/smoke_voice.py              voice paths with a fake speech engine (hit, silence, mis-hear,
                                  ambiguity, tap-to-talk, repeat/skip, blocked mic)
```

## Build

```bash
python3 tools/parse.py content/togaf-foundation       # only if source/*.txt changed
python3 tools/gen_clips.py content/togaf-foundation    # only if questions changed (needs models/, see script header)
python3 tools/build.py content/togaf-foundation        # writes index.html
python3 tests/smoke_tap.py && python3 tests/smoke_voice.py   # needs: pip install playwright
```

`index.html` is committed, so hosting needs no build step.

## Deploy (Vercel)

Import the repository in Vercel (framework preset: *Other*, no build command, output directory `.`).
`vercel.json` adds a `Permissions-Policy: microphone=(self)` header and `noindex`.
`.vercelignore` makes only `index.html` get deployed.

## Content and licensing

The `togaf-foundation` pack is original practice material written against the public TOGAF®
Enterprise Architecture Foundation syllabus. It contains no real exam questions. TOGAF is a
registered trademark of The Open Group. This project is not affiliated with or endorsed by The Open Group.
Commercial use of TOGAF content may require a TOGAF commercial license, so keep deployments
private/unlisted until that is settled.

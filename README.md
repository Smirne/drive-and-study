# drive-and-study

App to study while driving or in other audio-only situations.

The first prototype is a hands-free practice exam: questions are read aloud, you answer
by saying **one, two, three or four** (or tapping / pressing keys 1–4), and the app scores you,
plays the explanation and queues the questions you missed for review.

The runtime is deterministic, with no AI in the app. Audio is pre-rendered offline, and speech is
transcribed by the browser's own recognizer. The app matches the text deterministically
(`app/matcher.js`): a number ("number two"), words from an option ("business scenarios"),
or `repeat` / `skip`. It only accepts a clear winner and otherwise asks again.

## Use it

The site is organised in **packs**, one per subject. Each pack has its own lessons and drill:

| Pack | Lessons | Drill |
|---|---|---|
| TOGAF Foundation (`content/togaf-foundation`) | `/lessons` | `/drill` |
| EventStorming (`content/eventstorming`) | `/eventstorming/lessons` | `/eventstorming/drill` |

`/` is the home page and lists the packs. The TOGAF pack:
- `/lessons` has 13 audio episodes: 8 lessons, 2 practice exams, a recap podcast, commonly confused pairs and a 30-minute story of one full ADM cycle. They play in order and the page remembers where you stopped.
- `/drill` is the practice drill and mock exams:
  - **Practice**: 20 questions, with feedback and an explanation after each one.
  - **Mock exams 1–7** (5 is hard: balanced option lengths; 6 and 7 are weighted to governance, the Enterprise
    Continuum and Phases A, E–H, and each reuses five questions from earlier mocks that were often missed): like the real Part 1: 40 questions, 60 minutes, pass mark 24, no feedback until
    the end. Then a score by topic, a review of the mistakes with explanations, and export.
  - **Part 2 (Practitioner)**: 16 original case-study scenarios graded like the real Part 2: each option is worth
    5 (best), 3, 1 or 0 points. *Part 2 practice* shows the points of every option and the explanation after each
    scenario; *Part 2 mocks 1 and 2* are 8 scenarios, 90 minutes, pass mark 24/40 points, no feedback until the end.
  - **Results**: every session is saved in the browser. Download one attempt as CSV or JSON, download all
    attempts as CSV, or copy a summary (score, weakest topics, missed questions) to paste into a chat.
  Choose how to answer on the start screen:
  - **Touch**: silent and fast. Nothing is read aloud and no audio is downloaded. Tap an answer; in practice
    the explanation appears with a *Next* button (or Space / Enter). In a mock exam a tap records the answer and moves on.
  - **Answer by voice**: say "number two" or words from the answer. You get 12 s of quiet
    listening to think before any reprompt (8 s after a reprompt). Uses the microphone and the
    browser's speech service.
  - **Car buttons**: no microphone. Each option is read in turn; press *next* on the one you want,
    then *next* again to confirm (*previous* changes it). *Previous* during the options goes back to
    the question; *next* during the explanation skips it. Works with Android Auto (tested with
    steering-wheel next/previous).
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
  drill.html, lessons.html        TOGAF pack pages (generated)
  eventstorming/*.html            EventStorming pack pages (generated; assets via ../ relative paths)
  buttons.html                    media-button test page (hand-written)
  audio/lessons/ep1..13.mp3       TOGAF lesson audio (64 kbps mono)
  audio/lessons/eventstorming/    EventStorming lesson audio
  audio/drill/<pack>/*.mp3        drill speech clips (voice mode q/e, buttons mode s/o/confirm)
  audio/test/quiet.mp3            near-silent loop that keeps the button test the active media player
app/template.html                 drill UI + state machine (matcher, questions and clip URLs injected)
app/matcher.js                    deterministic answer matcher (numbers, option content, commands)
app/lessons.html                  lessons player UI
content/<pack>/pack.json          pack texts, URL base, storage keys, topics, lesson list, spoken intros
content/<pack>/source/*.txt       question scripts (ep9/ep10 practice set, pool1–pool7 mock-exam pools,
                                  scenarios: graded Part 2 case studies with `Scenario:` and `Grades:` lines)
content/<pack>/questions.json     parsed questions with id and topic (answers balanced over 1–4)
content/<pack>/exams.json         mock exams: title, minutes, pass mark, question ids
content/<pack>/lessons/ep*.txt    lesson scripts (ep11 recap, ep12 confused pairs and ep13 full-cycle story are two-host podcasts)
tools/parse.py                    source/*.txt -> questions.json
tools/gen_clips.py                questions.json -> public/audio/drill/<pack>/*.mp3 (Kokoro offline TTS)
tools/gen_lesson.py               single-voice lesson script -> wav
tools/gen_podcast.py              two-host podcast script -> wav
tools/build.py                    templates + every pack -> its drill.html and lessons.html
tests/test_matcher.js             matcher vs every option in the bank (node; must give 0 wrong)
tests/smoke_tap.py                drill: full session by keyboard, review queue
tests/smoke_voice.py              drill: voice paths with a fake speech engine
tests/smoke_buttons.py            drill: car-buttons scanning via simulated next/previous
tests/smoke_part2.py              drill: graded scenarios, per-option points, mock scored in points, summary/CSV
tests/smoke_touch.py              drill: touch mode is silent (no clip played or fetched), practice, review, full mock exam
tests/smoke_exam.py               mock exam: no feedback, timer, results, CSV/JSON/summary, review, time-up, history
tests/smoke_eventstorming.py      EventStorming drill: concepts, graded scenarios, readiness check, separate saved results
tests/smoke_site.py               site: home, both packs' lessons players and drills, cross-links, audio files, button test
```

### EventStorming pack

A study companion to Alberto Brandolini's *Introducing EventStorming*, for preparing to facilitate
a workshop. The material is an independent summary in our own words, not the book's text.

- `/eventstorming/lessons`: 11 episodes (10 lessons and a two-host recap) covering what EventStorming
  is, preparing the room and invitations, running a Big Picture, facilitation patterns and
  anti-patterns, finding bounded contexts, Process Modeling and its color grammar, Design-Level and
  aggregates, how it maps to DDD / CQRS / event sourcing, and remote workshops. Each lesson ends with
  a short spoken quiz with pauses.
- `/eventstorming/drill`: 30 concept questions with feedback, 12 facilitation scenarios graded
  5/3/1/0 with the reasons for every option, and a 20-question readiness check (20 min, target 14).

## Adding a pack

1. `content/<pack>/pack.json`: page texts, URL `base` (`""` = site root, used by TOGAF only), storage
   keys (keep them unique per pack), topic labels, the practice-set id prefix, the lesson list with
   durations, spoken intros (`say`) and pronunciation fixes (`pronounce`). Copy the EventStorming one.
2. `content/<pack>/source/*.txt`: questions (see `tools/parse.py`), then `python3 tools/parse.py content/<pack>`.
3. `content/<pack>/exams.json`: timed exams, or `"practice": true` sets with feedback.
4. Lessons in `content/<pack>/lessons/ep<n>.txt`, rendered to `public/<lessons.audioDir>/ep<n>.mp3`
   with `tools/gen_lesson.py` (single voice) or `tools/gen_podcast.py` (lines starting `A:` / `S:`).
5. `python3 tools/gen_clips.py content/<pack> models --only-missing`, then `python3 tools/build.py`.
6. Add a card to `public/index.html`.

## Build

```bash
python3 tools/parse.py content/togaf-foundation       # only if source/*.txt changed
python3 tools/gen_clips.py content/togaf-foundation models --only-missing   # after adding questions (see script header)
python3 tools/build.py                                 # all packs (or name pack folders)
node tests/test_matcher.js && for t in tap voice buttons touch part2 eventstorming exam site; do python3 tests/smoke_$t.py || break; done   # pip install playwright
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

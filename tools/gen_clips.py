"""Render the spoken clips for a content pack with Kokoro (offline neural TTS).

Usage:
  pip install kokoro-onnx soundfile        (ffmpeg must be on PATH)
  mkdir -p models && cd models && \
    curl -LO https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx && \
    curl -LO https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
  python3 tools/gen_clips.py content/togaf-foundation [models] [--only-missing]

Writes public/audio/drill/<pack>/*.mp3 (40 kbps mono):

  voice mode    intro, review, correct, wrong, reprompt, end, score0..scoreN,
                q<i> (question + numbered options + "Your answer?"), e<i> (explanation)
  buttons mode  intro_buttons, rescan, confirm1..4, s<i> (question only),
                o<i>_<j> (option j alone, "Two. ..."), one clip per option

--only-missing renders only clips that don't exist yet (use after adding questions).
Exam clips: exam_intro, exam_intro_buttons, recorded, timeup, exam_pass, exam_fail, qnum1..N.
"""
import json, subprocess, sys, tempfile
from pathlib import Path
import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro

args = [a for a in sys.argv[1:] if not a.startswith('--')]
only_missing = '--only-missing' in sys.argv
pack = Path(args[0] if args else 'content/togaf-foundation')
models = Path(args[1] if len(args) > 1 else 'models')
out = Path('public/audio/drill') / pack.name
out.mkdir(parents=True, exist_ok=True)
tmp = Path(tempfile.mkdtemp())

k = Kokoro(str(models / 'kokoro-v1.0.onnx'), str(models / 'voices-v1.0.bin'))
SR = 24000
VOICE = 'am_michael'
# Pronunciation fixes applied to all spoken text
SUBS = {'TOGAF': 'Toe-gaff'}


def say(t):
    for a, b in SUBS.items():
        t = t.replace(a, b)
    s, _ = k.create(t, voice=VOICE, speed=1.0, lang='en-us')
    return s


def sil(x):
    return np.zeros(int(SR * x))


def write(name, parts_fn):
    """parts_fn is called only when the clip has to be rendered (so --only-missing skips the TTS work)."""
    target = out / f'{name}.mp3'
    if only_missing and target.exists():
        return
    wav = tmp / f'{name}.wav'
    sf.write(wav, np.concatenate(parts_fn() + [sil(0.15)]), SR)
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', str(wav), '-ac', '1', '-ar', '24000',
                    '-b:a', '40k', str(target)], check=True)


NUM = ['one', 'two', 'three', 'four']
ONES = 'zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen'.split()
TENS = 'zero ten twenty thirty forty fifty sixty seventy eighty ninety'.split()


def word(n):
    if n < 20:
        return ONES[n]
    t, o = divmod(n, 10)
    return TENS[t] + ('' if o == 0 else '-' + ONES[o])


qs = json.loads((pack / 'questions.json').read_text())
exams = json.loads((pack / 'exams.json').read_text()) if (pack / 'exams.json').exists() else {}
longest = max([len(qs) if not exams else 20] + [len(e['questions']) for e in exams.values()])

# ---- shared prompts ----
G = {
    'intro': 'TOGAF Foundation practice drill. After each question, say number one, two, three, or four, '
             'or words from the answer. Say repeat to hear the question again.',
    'intro_buttons': 'TOGAF Foundation practice drill, with car buttons. I will read each option. '
                     'Press next when you hear the one you want. Press previous to hear the question again.',
    'review': 'Reviewing the questions you missed.',
    'correct': 'Correct.',
    'wrong': 'Not quite.',
    'reprompt': 'Say number one, two, three, or four. Or say repeat.',
    'rescan': 'Here are the options again.',
    'end': 'End of session.',
    # exam simulation
    'exam_intro': 'TOGAF Foundation mock exam. Forty questions, sixty minutes, and no feedback until the end. '
                  'Answer each question by saying number one to four, or words from the answer.',
    'exam_intro_buttons': 'TOGAF Foundation mock exam. Forty questions, sixty minutes, and no feedback until the end. '
                          'I will read each option. Press next on the one you want, then next again to confirm.',
    'recorded': 'Answer recorded.',
    'timeup': 'Time is up. The exam is over.',
    'exam_pass': 'That is a pass. The pass mark is twenty-four out of forty.',
    'exam_fail': 'That is below the pass mark of twenty-four out of forty.',
}
for n, t in G.items():
    write(n, lambda t=t: [say(t)])
for j in range(1, 5):
    write(f'confirm{j}', lambda j=j: [say(f'You chose {NUM[j - 1]}.'), sil(0.25), say('Next to confirm. Previous to change.')])
for i in range(0, longest + 1):
    write(f'score{i}', lambda i=i: [say(f'You got {word(i)} right.')])
for n in range(1, longest + 1):
    write(f'qnum{n}', lambda n=n: [say(f'Question {word(n)}.')])

# ---- per question (no question number inside: the app plays qnum<n> for the position in the session) ----
for i, q in enumerate(qs):
    def voice_q(q=q):
        p = [say(q['q']), sil(0.5)]
        for j, o in enumerate(q['o']):
            p += [say(f'{NUM[j].capitalize()}. {o}'), sil(0.35)]
        return p + [sil(0.2), say('Your answer?')]
    write(f'q{i}', voice_q)                                   # voice mode: question + options
    write(f'e{i}', lambda q=q: [say(q['e'])])                 # explanation
    write(f's{i}', lambda q=q: [say(q['q'])])                 # buttons mode: question only
    for j, o in enumerate(q['o'], start=1):
        write(f'o{i}_{j}', lambda j=j, o=o: [say(f'{NUM[j - 1].capitalize()}. {o}')])   # one option
    print(f'{i + 1}/{len(qs)}', flush=True)

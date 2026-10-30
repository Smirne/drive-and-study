"""Render the spoken clips for a content pack with Kokoro (offline neural TTS).

Usage:
  pip install kokoro-onnx soundfile        (ffmpeg must be on PATH)
  mkdir -p models && cd models && \
    curl -LO https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx && \
    curl -LO https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
  python3 tools/gen_clips.py content/togaf-foundation [models] [--scan-only]

Writes public/audio/drill/<pack>/*.mp3 (40 kbps mono):

  voice mode    intro, review, correct, wrong, reprompt, end, score0..scoreN,
                q<i> (question + numbered options + "Your answer?"), e<i> (explanation)
  buttons mode  intro_buttons, rescan, confirm1..4, s<i> (question only),
                o<i>_<j> (option j alone, "Two. ..."), one clip per option

--scan-only renders just the buttons-mode clips.
"""
import json, subprocess, sys, tempfile
from pathlib import Path
import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro

args = [a for a in sys.argv[1:] if not a.startswith('--')]
scan_only = '--scan-only' in sys.argv
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


def write(name, parts):
    wav = tmp / f'{name}.wav'
    sf.write(wav, np.concatenate(parts + [sil(0.15)]), SR)
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', str(wav), '-ac', '1', '-ar', '24000',
                    '-b:a', '40k', str(out / f'{name}.mp3')], check=True)


NUM = ['one', 'two', 'three', 'four']
WORDS = ('zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen '
         'fifteen sixteen seventeen eighteen nineteen twenty').split()


def word(n):
    return WORDS[n] if n < len(WORDS) else str(n)


qs = json.loads((pack / 'questions.json').read_text())

# ---- voice mode ----
if not scan_only:
    G = {
        'intro': 'TOGAF Foundation practice exam. After each question, say number one, two, three, or four. '
                 'Say repeat to hear the question again.',
        'review': 'Reviewing the questions you missed.',
        'correct': 'Correct.',
        'wrong': 'Not quite.',
        'reprompt': 'Say number one, two, three, or four. Or say repeat.',
        'end': 'End of session.',
    }
    for n, t in G.items():
        write(n, [say(t)])
    for i in range(len(qs) + 1):
        write(f'score{i}', [say(f'You got {word(i)} right.')])
    for i, q in enumerate(qs):
        p = [say(f'Question {word(i + 1)}.'), sil(0.3), say(q['q']), sil(0.5)]
        for j, o in enumerate(q['o']):
            p += [say(f'{NUM[j].capitalize()}. {o}'), sil(0.35)]
        p += [sil(0.2), say('Your answer?')]
        write(f'q{i}', p)
        write(f'e{i}', [say(q['e'])])
        print(f'voice {i + 1}/{len(qs)}', flush=True)

# ---- buttons (scanning) mode ----
B = {
    'intro_buttons': 'TOGAF Foundation practice exam, with car buttons. I will read each option. '
                     'Press next when you hear the one you want. Press previous to hear the question again.',
    'rescan': 'Here are the options again.',
}
for n, t in B.items():
    write(n, [say(t)])
for j in range(1, 5):
    write(f'confirm{j}', [say(f'You chose {NUM[j - 1]}.'), sil(0.25), say('Next to confirm. Previous to change.')])
for i, q in enumerate(qs):
    write(f's{i}', [say(f'Question {word(i + 1)}.'), sil(0.3), say(q['q'])])
    for j, o in enumerate(q['o'], start=1):
        write(f'o{i}_{j}', [say(f'{NUM[j - 1].capitalize()}. {o}')])
    print(f'buttons {i + 1}/{len(qs)}', flush=True)

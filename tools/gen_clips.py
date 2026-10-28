"""Render the spoken clips for a content pack with Kokoro (offline neural TTS).

Usage:
  pip install kokoro-onnx soundfile        (ffmpeg must be on PATH)
  mkdir -p models && cd models && \
    curl -LO https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx && \
    curl -LO https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
  python3 tools/gen_clips.py content/togaf-foundation [models]

Writes <pack>/clips/*.mp3 (40 kbps mono): intro, review, correct, wrong, reprompt, end,
score0..scoreN, and q<i> (question + numbered options) / e<i> (explanation) per question.
"""
import json, subprocess, sys, tempfile
from pathlib import Path
import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro

pack = Path(sys.argv[1] if len(sys.argv) > 1 else 'content/togaf-foundation')
models = Path(sys.argv[2] if len(sys.argv) > 2 else 'models')
out = pack / 'clips'
out.mkdir(exist_ok=True)
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
G = {
    'intro': 'TOGAF Foundation practice exam. After each question, say or tap one, two, three, or four. '
             'Say repeat to hear the question again.',
    'review': 'Reviewing the questions you missed.',
    'correct': 'Correct.',
    'wrong': 'Not quite.',
    'reprompt': 'Say one, two, three, or four. Or say repeat.',
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
    print(f'{i + 1}/{len(qs)}', flush=True)

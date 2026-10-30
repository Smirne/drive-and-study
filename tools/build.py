"""Build the static site in public/ from the app templates and a content pack.

Usage: python3 tools/build.py [content/togaf-foundation]

Outputs:
  public/drill.html    drill page; clips are served from public/audio/drill/<pack>/
  public/lessons.html  audio lessons player (episodes in public/audio/lessons/)
  public/index.html    home page (hand-written, not generated)

Serve over HTTPS so the browser allows the microphone (speech recognition).
"""
import json, sys
from pathlib import Path

pack = Path(sys.argv[1] if len(sys.argv) > 1 else 'content/togaf-foundation')
out = Path('public')

HEAD = ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
        '<style>:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}'
        'body{margin:0}[hidden]{display:none!important}</style></head><body>')
TAIL = '</body></html>'


def write(name, body):
    target = out / name
    target.write_text(HEAD + body + TAIL)
    return target


# Voice drill
qs = json.loads((pack / 'questions.json').read_text())
clip_dir = out / 'audio' / 'drill' / pack.name
clips = {f.stem: f'audio/drill/{pack.name}/{f.name}' for f in sorted(clip_dir.glob('*.mp3'))}
needed = ['intro', 'intro_buttons', 'review', 'correct', 'wrong', 'reprompt', 'rescan', 'end'] \
    + [f'confirm{j}' for j in range(1, 5)] + [f'score{i}' for i in range(len(qs) + 1)] \
    + [n for i, q in enumerate(qs) for n in (f'q{i}', f'e{i}', f's{i}', *[f'o{i}_{j}' for j in range(1, len(q['o']) + 1)])]
missing = [n for n in needed if n not in clips]
assert not missing, f'missing clips: {missing[:10]}... (run tools/gen_clips.py)'
drill = (Path('app/template.html').read_text()
         .replace('/*__QUESTIONS__*/[]', json.dumps(qs))
         .replace('/*__CLIPS__*/{}', json.dumps(clips)))
t = write('drill.html', drill)
print(f'{len(qs)} questions, {len(clips)} clips -> {t} ({t.stat().st_size // 1024} KB)')

# Audio lessons
eps = sorted((out / 'audio' / 'lessons').glob('ep*.mp3'))
assert eps, 'no lesson audio in public/audio/lessons (run tools/gen_lesson.py / gen_podcast.py)'
t = write('lessons.html', Path('app/lessons.html').read_text())
print(f'{len(eps)} lesson episodes -> {t}')

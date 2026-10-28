"""Build the self-contained web app (index.html) from app/template.html and a content pack.

Usage: python3 tools/build.py [content/togaf-foundation] [index.html]

Questions and every audio clip are embedded (base64 data URIs), so the output is a single
static file that works offline once loaded. Serve it over HTTPS so the browser allows the
microphone (speech recognition).
"""
import base64, json, sys
from pathlib import Path

pack = Path(sys.argv[1] if len(sys.argv) > 1 else 'content/togaf-foundation')
target = Path(sys.argv[2] if len(sys.argv) > 2 else 'index.html')

template = Path('app/template.html').read_text()
qs = json.loads((pack / 'questions.json').read_text())
clips = {f.stem: 'data:audio/mpeg;base64,' + base64.b64encode(f.read_bytes()).decode()
         for f in sorted((pack / 'clips').glob('*.mp3'))}
missing = [n for i in range(len(qs)) for n in (f'q{i}', f'e{i}') if n not in clips]
assert not missing, f'missing clips: {missing} (run tools/gen_clips.py)'

body = (template.replace('/*__QUESTIONS__*/[]', json.dumps(qs))
                .replace('/*__CLIPS__*/{}', json.dumps(clips)))
head = ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
        '<style>:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}'
        'body{margin:0}[hidden]{display:none!important}</style></head><body>')
target.write_text(head + body + '</body></html>')
print(f'{len(qs)} questions, {len(clips)} clips -> {target} ({target.stat().st_size // 1024} KB)')

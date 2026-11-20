"""Build the static site in public/ from the app templates and one or more content packs.

Usage: python3 tools/build.py [content/togaf-foundation content/eventstorming ...] [--allow-missing]
       (no pack arguments = every folder in content/ that has a pack.json)

Each pack has content/<pack>/pack.json (texts, storage keys, topic labels, lesson list, spoken
intros) plus questions.json / exams.json (from tools/parse.py) and optional lessons/.
A pack's "base" decides where its pages go:
  ""              -> public/drill.html, public/lessons.html          (/drill, /lessons)
  "eventstorming" -> public/eventstorming/drill.html, .../lessons.html (/eventstorming/drill, ...)
Drill clips are served from public/audio/drill/<pack>/, lessons from public/<audioDir>/ep<n>.mp3.
All asset paths in the pages are relative, so the pages also work from file:// in the tests.
public/index.html (home page) is hand-written.

Serve over HTTPS so the browser allows the microphone (speech recognition).
"""
import html, json, sys
from pathlib import Path

args = [a for a in sys.argv[1:] if not a.startswith('--')]
packs = [Path(a) for a in args] or sorted(p.parent for p in Path('content').glob('*/pack.json'))
out = Path('public')

HEAD = ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
        '<style>:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}'
        'body{margin:0}[hidden]{display:none!important}</style></head><body>')
TAIL = '</body></html>'


def write(path, body):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(HEAD + body + TAIL)
    return path


def fill(text, values):
    for k, v in values.items():
        assert k in text, f'placeholder {k} not in template'
        text = text.replace(k, v)
    assert '__P_' not in text and '__L_' not in text, 'unfilled placeholder'
    return text


def longest_session(qs, exams, cfg):
    """Longest numbered session: sizes the qnum<n> and score<n> clips."""
    practice = sum(q['id'].startswith(cfg['drill']['practicePrefix']) for q in qs)
    silent = {q['id'] for q in qs if q.get('na')}                # all-silent exams run in touch mode: no numbered clips
    return max([20, practice] + [len(e['questions']) for e in exams.values() if not silent.issuperset(e['questions'])])


def build(pack):
    cfg = json.loads((pack / 'pack.json').read_text())
    d, lc = cfg['drill'], cfg.get('lessons')
    base = cfg.get('base', '')
    up = '../' * len([p for p in base.split('/') if p])       # from the page folder back to public/
    page_dir = out / base if base else out
    href = lambda name: f'/{base}/{name}' if base else f'/{name}'

    # ---- drill ----
    qs = json.loads((pack / 'questions.json').read_text())
    exams = json.loads((pack / 'exams.json').read_text()) if (pack / 'exams.json').exists() else {}
    for k, e in exams.items():
        unknown = [i for i in e['questions'] if i not in {q['id'] for q in qs}]
        assert not unknown, f'{k}: unknown question ids {unknown}'
    clip_dir = out / 'audio' / 'drill' / pack.name
    clips = {f.stem: f'{up}audio/drill/{pack.name}/{f.name}' for f in sorted(clip_dir.glob('*.mp3'))}
    longest = longest_session(qs, exams, cfg)
    needed = ['intro', 'intro_buttons', 'review', 'correct', 'wrong', 'reprompt', 'rescan', 'end',
              'exam_intro', 'exam_intro_buttons', 'recorded', 'timeup', 'exam_pass', 'exam_fail'] \
        + (['p2_intro', 'p2_intro_buttons', 'p2_practice', 'p2_practice_buttons', 'worth0', 'worth1', 'worth3', 'worth5']
           + [f'points{i}' for i in range(41)] if any('g' in q for q in qs) else []) \
        + [f'qnum{n}' for n in range(1, longest + 1)] \
        + [f'confirm{j}' for j in range(1, 5)] + [f'score{i}' for i in range(longest + 1)] \
        + [n for i, q in enumerate(qs) if not q.get('na') for n in (f'q{i}', f'e{i}', f's{i}', *[f'o{i}_{j}' for j in range(1, len(q['o']) + 1)])]
    missing = [n for n in needed if n not in clips]
    if missing and '--allow-missing' in sys.argv:
        print(f'WARNING [{pack.name}]: {len(missing)} clips missing (allowed for testing)')
    else:
        assert not missing, f'[{pack.name}] missing clips: {missing[:10]}... (run tools/gen_clips.py)'
    pack_js = {k: d[k] for k in ('practicePrefix', 'practiceTitle', 'summaryTitle', 'filePrefix',
                                 'statsKey', 'historyKey', 'mediaTitle', 'topics')}
    drill = fill(Path('app/template.html').read_text(), {
        '__P_TITLE__': html.escape(d['title']), '__P_H1__': d['h1'], '__P_INTRO__': d['intro'],
        '__P_PRACTICE_LABEL__': html.escape(d['practiceLabel']), '__P_EXAMS_HEADING__': html.escape(d['examsHeading']),
        '__P_EXAMS_TEXT__': d['examsText'], '__P_SAY_EXAMPLE__': html.escape(d['sayExample']),
        '__P_LESSONS_HREF__': href('lessons') if lc else '/'})
    drill = (drill.replace('/*__MATCHER__*/', Path('app/matcher.js').read_text())
             .replace('/*__QUESTIONS__*/[]', json.dumps(qs))
             .replace('/*__EXAMS__*/{}', json.dumps(exams))
             .replace('/*__PACK__*/{}', json.dumps(pack_js, ensure_ascii=False))
             .replace('/*__CLIPS__*/{}', json.dumps(clips)))
    t = write(page_dir / 'drill.html', drill)
    print(f'[{pack.name}] {len(qs)} questions, {len(clips)} clips -> {t} ({t.stat().st_size // 1024} KB)')

    # ---- audio lessons ----
    if not lc:
        return
    n = len(lc['episodes'])
    eps = [out / lc['audioDir'] / f'ep{i}.mp3' for i in range(1, n + 1)]
    absent = [str(e) for e in eps if not e.exists()]
    if absent and '--allow-missing' in sys.argv:
        print(f'WARNING [{pack.name}]: {len(absent)} lesson episodes missing (allowed for testing)')
    else:
        assert not absent, f'[{pack.name}] missing lesson audio: {absent} (run tools/gen_lesson.py / gen_podcast.py)'
    lessons_js = {'title': lc['title'], 'artist': lc['artist'], 'posKey': lc['posKey'],
                  'audioSrc': up + lc['audioDir'], 'episodes': lc['episodes']}
    page = fill(Path('app/lessons.html').read_text(), {
        '__L_TITLE__': html.escape(lc['title']), '__L_EYEBROW__': lc['eyebrow'], '__L_H1__': lc['h1'],
        '__L_SUB__': lc['sub'], '__L_DRILL_HREF__': href('drill'), '__L_DRILL_LINK__': html.escape(lc['drillLink']),
        '__L_DRILL_SUB__': lc['drillSub']})
    page = page.replace('/*__LESSONS__*/{}', json.dumps(lessons_js, ensure_ascii=False))
    t = write(page_dir / 'lessons.html', page)
    print(f'[{pack.name}] {n} lesson episodes -> {t}')


for p in packs:
    build(p)

"""Parse practice-exam scripts into questions.json for a content pack.

Usage: python3 tools/parse.py content/togaf-foundation

Reads <pack>/source/*.txt (in natural order: ep9 before ep10). Each question block:

    Question <n>.
    Topic: <topic>            (optional; used for the per-topic breakdown of results)
    <question text>
    A. ...
    B. ...
    C. ...
    D. ...
    [THINK]
    The answer is <letter>... explanation...

Graded (Part 2 style) questions add a scenario and a grade per option:

    Question <n>.
    Topic: <topic>
    Scenario: <scenario text, one line>
    <question text>
    A. ... (four options)
    Grades: A=5 B=3 C=1 D=0
    [THINK]
    The best answer is A... explanation...

Java-style questions may add a code block (``` fence, before or after the question line), up to six
options (A-F), several right answers ("The answers are B and D."), and "Check: ..." lines read by
tools/verify_java.py. Questions with code, multiple answers or other than four options are silent
("na": shown, never read aloud), keep their option order, and get digits instead of letters in the
explanation (pack.json "silentSources" makes every question of the listed source files silent);
"a" is a list for multi-answer questions and "c" holds the code.

Graded questions keep the option order of the source (spread the best answers when writing them);
"a" is the best option, "g" the points per option in display order and "sc" the scenario.

Options of ungraded questions are re-ordered deterministically so correct answers are spread evenly over 1-4,
and letter references in the explanation ("option B", "The answer is C") are rewritten
to the spoken numbers used by the app ("option two").
"""
import json, re, sys
from pathlib import Path

NUM = {'A': 'one', 'B': 'two', 'C': 'three', 'D': 'four'}
# Target answer slot (0-based) per question; repeats for longer packs. Balanced 5/5/5/5 over 20.
TARGET = [1, 2, 0, 3, 1, 3, 2, 0, 2, 1, 0, 3, 3, 2, 0, 1, 3, 0, 2, 1]


def natural_key(p: Path):
    return [int(t) if t.isdigit() else t for t in re.split(r'(\d+)', p.name)]


def parse(pack: Path, keep_checks=False):
    qs = []
    cfg = pack / 'pack.json'
    silent_files = set(json.loads(cfg.read_text()).get('silentSources', [])) if cfg.exists() else set()
    for f in sorted((pack / 'source').glob('*.txt'), key=natural_key):
        blocks = re.split(r'\nQuestion \w+\.\n', f.read_text())[1:]
        for b in blocks:
            b = b.split('\n\nThat')[0].strip()
            lines = b.split('\n')
            topic = 'general'
            if lines[0].startswith('Topic:'):
                topic = lines.pop(0).split(':', 1)[1].strip()
            sc = lines.pop(0).split(':', 1)[1].strip() if lines[0].startswith('Scenario:') else None
            # optional code block (``` fence) before or right after the question line
            code, q = None, None
            while code is None or q is None:
                if lines[0].startswith('```'):
                    if code is not None: break
                    end = lines.index('```', 1)
                    code, lines = '\n'.join(lines[1:end]), lines[end + 1:]
                elif q is None:
                    q = lines.pop(0)
                else:
                    break
            opts = []
            while re.match(r'[A-F]\. ', lines[0]):
                opts.append(lines.pop(0)[3:])
            assert len(opts) >= 2, (f.stem, q)
            grades = None
            if lines[0].startswith('Grades:'):
                g = dict(x.split('=') for x in lines.pop(0).split(':', 1)[1].split())
                grades = [int(g[l]) for l in 'ABCD']
                assert sorted(grades) == [0, 1, 3, 5], grades
            checks = []
            while lines[0].startswith('Check:'):
                checks.append(lines.pop(0).split(':', 1)[1].strip())
            assert lines[0] == '[THINK]', (f.stem, q, lines[0])
            ex = ' '.join(lines[1:])
            qid = f'{f.stem}-{len([x for x in qs if x["id"].startswith(f.stem + "-")]) + 1}'
            if grades:
                best = 'ABCD'[grades.index(5)]
                assert re.match(r'The best answer is ' + best, ex), (qid, ex[:40])
                ex = re.sub(r'\b([Oo]ptions?|answer is) ([ABCD])\b', lambda m: m.group(1) + ' ' + NUM[m.group(2)], ex)
                qs.append({'id': qid, 'topic': topic, 'sc': sc, 'q': q, 'o': opts, 'a': grades.index(5) + 1, 'g': grades, 'e': ex})
                continue
            m = re.match(r'The answers are ([A-F](?:, [A-F])*,? and [A-F])\b', ex)
            letters = 'ABCDEF'[:len(opts)]
            if code or m or len(opts) != 4 or f.stem in silent_files:
                # silent question (shown, not read aloud): keep the source order, letters become digits
                ans = sorted(letters.index(x) + 1 for x in re.findall(r'[A-F]', m.group(1))) if m else \
                    letters.index(re.match(r'The answer is ([A-F])\b', ex).group(1)) + 1
                ex = re.sub(r'\b([Oo]ptions?|answers? (?:is|are)) ([A-F](?:(?:, |,? and |,? or )[A-F])*)\b',
                            lambda mm: mm.group(1) + ' ' + re.sub(r'[A-F]', lambda x: str(letters.index(x.group()) + 1), mm.group(2)), ex)
                item = {'id': qid, 'topic': topic, 'q': q, 'o': opts, 'a': ans, 'e': ex, 'na': True}
                if code: item['c'] = code
                if keep_checks: item['chk'] = checks
                qs.append(item)
                continue
            ans = re.match(r'The answer is ([ABCD])', ex).group(1)
            tgt = 'ABCD'[TARGET[len([x for x in qs if 'g' not in x and 'na' not in x]) % len(TARGET)]]
            perm = {l: l for l in 'ABCD'}
            perm[ans], perm[tgt] = tgt, ans
            i, j = 'ABCD'.index(ans), 'ABCD'.index(tgt)
            opts[i], opts[j] = opts[j], opts[i]
            ex = re.sub(r'\b([Oo]ptions?|answer is) ([ABCD])\b', lambda m: m.group(1) + ' ' + perm[m.group(2)], ex)
            ex = re.sub(r'\b([Oo]ptions?|answer is) ([ABCD])\b', lambda m: m.group(1) + ' ' + NUM[m.group(2)], ex)
            item = {'id': qid, 'topic': topic, 'q': q, 'o': opts, 'a': 'ABCD'.index(tgt) + 1, 'e': ex}
            if keep_checks: item['chk'] = checks
            qs.append(item)
    return qs


if __name__ == '__main__':
    pack = Path(sys.argv[1] if len(sys.argv) > 1 else 'content/togaf-foundation')
    qs = parse(pack)
    (pack / 'questions.json').write_text(json.dumps(qs, indent=1))
    print(f'{len(qs)} questions -> {pack / "questions.json"}')

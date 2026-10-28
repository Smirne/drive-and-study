"""Parse practice-exam scripts into questions.json for a content pack.

Usage: python3 tools/parse.py content/togaf-foundation

Reads <pack>/source/*.txt (in natural order: ep9 before ep10). Each question block:

    Question <n>.
    <question text>
    A. ...
    B. ...
    C. ...
    D. ...
    [THINK]
    The answer is <letter>... explanation...

Options are re-ordered deterministically so correct answers are spread evenly over 1-4,
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


def parse(pack: Path):
    qs = []
    for f in sorted((pack / 'source').glob('*.txt'), key=natural_key):
        blocks = re.split(r'\nQuestion \w+\.\n', f.read_text())[1:]
        for b in blocks:
            b = b.split('\n\nThat')[0].strip()
            lines = b.split('\n')
            q, opts = lines[0], [l[3:] for l in lines[1:5]]
            assert all(l[1:3] == '. ' for l in lines[1:5]), lines[1:5]
            assert lines[5] == '[THINK]', lines[5]
            ex = ' '.join(lines[6:])
            ans = re.match(r'The answer is ([ABCD])', ex).group(1)
            tgt = 'ABCD'[TARGET[len(qs) % len(TARGET)]]
            perm = {l: l for l in 'ABCD'}
            perm[ans], perm[tgt] = tgt, ans
            i, j = 'ABCD'.index(ans), 'ABCD'.index(tgt)
            opts[i], opts[j] = opts[j], opts[i]
            ex = re.sub(r'\b([Oo]ptions?|answer is) ([ABCD])\b', lambda m: m.group(1) + ' ' + perm[m.group(2)], ex)
            ex = re.sub(r'\b([Oo]ptions?|answer is) ([ABCD])\b', lambda m: m.group(1) + ' ' + NUM[m.group(2)], ex)
            qs.append({'q': q, 'o': opts, 'a': 'ABCD'.index(tgt) + 1, 'e': ex})
    return qs


if __name__ == '__main__':
    pack = Path(sys.argv[1] if len(sys.argv) > 1 else 'content/togaf-foundation')
    qs = parse(pack)
    (pack / 'questions.json').write_text(json.dumps(qs, indent=1))
    print(f'{len(qs)} questions -> {pack / "questions.json"}')

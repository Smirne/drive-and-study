"""Verify the code questions of a Java pack against a real JDK.

Usage: python3 tools/verify_java.py content/ocp-java25 [question-id-prefix ...]
Needs JDK 25 (JDK25_HOME or /usr/lib/jvm/java-25-openjdk-amd64). Each code question runs through the
source-file launcher (java File.java), so the first top-level class (or a compact source file) is run.

Check lines (one or more, before [THINK]):
    Check: output                 runs; stdout must equal the right option (backticks stripped), whitespace-normalised
    Check: output <text>          runs; stdout must equal <text> (use \\n for line breaks if it matters: whitespace is normalised anyway)
    Check: compile-error          compilation must fail
    Check: exception <Name>       compiles, then the run must end with an uncaught <Name>
    Check: options                every option is a snippet that replaces /*?*/ in the code: the right options must
                                  compile and run without an exception, the others must not compile
    Check: options-run            as options, but wrong options may also fail at run time (exception)
    Check: none                   not checked automatically (concept question, or nondeterministic output)
Code questions without a Check line fail verification.
"""
import os, re, subprocess, sys, tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from parse import parse  # noqa: E402

JAVA = Path(os.environ.get('JDK25_HOME', '/usr/lib/jvm/java-25-openjdk-amd64')) / 'bin' / 'java'


def norm(s):
    return ' '.join(s.replace('\\n', ' ').split())


def run(code, tmp):
    """Returns (kind, stdout, stderr): kind is 'ok', 'compile' or 'exception'."""
    m = re.search(r'^(?:public\s+)?(?:final\s+|abstract\s+|sealed\s+)*(?:class|record|enum|interface)\s+(\w+)', code, re.M)
    compact = re.search(r'^(?:static\s+)?void\s+main\s*\(', code, re.M)      # compact source file
    f = Path(tmp) / ('Q.java' if compact or not m else m.group(1) + '.java')
    f.write_text(code)
    env = dict(os.environ, JAVA_TOOL_OPTIONS='')
    p = subprocess.run([str(JAVA), str(f)], capture_output=True, text=True, timeout=60, cwd=tmp, env=env)
    err = '\n'.join(l for l in p.stderr.splitlines() if not l.startswith('Picked up'))
    if 'error: compilation failed' in err:
        return 'compile', p.stdout, err
    if p.returncode != 0 or 'Exception in thread' in err:
        return 'exception', p.stdout, err
    return 'ok', p.stdout, err


def strip(o):
    return o.replace('`', '')


def check(q, tmp):
    probs = []
    right = q['a'] if isinstance(q['a'], list) else [q['a']]
    for c in q.get('chk') or []:
        kind, _, arg = c.partition(' ')
        if kind == 'none':
            continue
        if kind in ('options', 'options-run'):
            assert '/*?*/' in q['c'], 'options check needs a /*?*/ placeholder'
            for j, o in enumerate(q['o'], 1):
                k, out, err = run(q['c'].replace('/*?*/', strip(o)), tmp)
                if j in right and k != 'ok':
                    probs.append(f'option {j} should work but got {k}: {err.strip().splitlines()[:2]}')
                if j not in right and (k == 'ok' or (kind == 'options' and k != 'compile')):
                    probs.append(f'option {j} should fail{" to compile" if kind == "options" else ""} but got {k}')
            continue
        k, out, err = run(q['c'], tmp)
        if kind == 'output':
            want = arg if arg else strip(q['o'][right[0] - 1])
            if k != 'ok' or norm(out) != norm(want):
                probs.append(f'expected output {want!r}, got {k}: {out.strip()!r} {err.strip().splitlines()[:2]}')
        elif kind == 'compile-error':
            if not all('ompil' in q['o'][j - 1] for j in right):
                probs.append('the right option should say that compilation fails')
            if k != 'compile':
                probs.append(f'expected a compile error, got {k}: {out.strip()!r}')
        elif kind == 'exception':
            if not all(arg in q['o'][j - 1] for j in right):
                probs.append(f'the right option should name {arg}')
            if k != 'exception' or arg not in err:
                probs.append(f'expected {arg}, got {k}: {out.strip()!r} {err.strip().splitlines()[:2]}')
        else:
            probs.append('unknown check ' + c)
    if q.get('c') and not q.get('chk'):
        probs.append('code question without a Check line')
    return probs


def main():
    pack = Path(sys.argv[1] if len(sys.argv) > 1 else 'content/ocp-java25')
    prefixes = sys.argv[2:]
    qs = [q for q in parse(pack, keep_checks=True) if not prefixes or q['id'].startswith(tuple(prefixes))]
    bad = checked = 0
    with tempfile.TemporaryDirectory() as tmp:
        for q in qs:
            if not q.get('chk') and not q.get('c'):
                continue
            work = Path(tmp) / q['id']                     # fresh directory per question
            work.mkdir()
            probs = check(q, str(work))
            checked += 1
            if probs:
                bad += 1
                print(f'FAIL {q["id"]}: {q["q"]}')
                for p in probs:
                    print('   ', p)
    print(f'{checked} checked, {bad} failing')
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()

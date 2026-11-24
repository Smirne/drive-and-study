"""Part 2 (graded scenarios): practice with per-option points, a mock exam scored in points, results and summary.
Runs in touch mode, so no audio is needed."""
import json, os
from playwright.sync_api import sync_playwright

pack = 'content/togaf-foundation'
QS = json.load(open(f'{pack}/questions.json'))
IDX = {q['id']: q for q in QS}
EX = json.load(open(f'{pack}/exams.json'))

with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={'width': 390, 'height': 844})
    errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script("HTMLMediaElement.prototype.play=function(){return Promise.resolve()};HTMLMediaElement.prototype.pause=function(){};")
    pg.goto('file://' + os.path.abspath('public/drill.html'))
    pg.click('#modeTouch')
    assert '8 scenarios · 90 min · pass 24/40 points' in pg.text_content('#exam-p2mock1')
    assert 'feedback after each' in pg.text_content('#exam-p2practice')

    # practice: pick the 5, 3, 1 and 0 options in turn, then best for the rest
    pg.click('#exam-p2practice')
    want = [5, 3, 1, 0]
    expected = 0
    for i, qid in enumerate(EX['p2practice']['questions']):
        q = IDX[qid]
        pg.wait_for_selector('#pad1:not([disabled])')
        assert pg.text_content('#qScen') == q['sc'] and pg.is_visible('#qScen')
        assert pg.text_content('#qText') == q['q']
        g = want[i] if i < 4 else 5
        pick = q['g'].index(g) + 1
        pg.click(f'#pad{pick}')
        expected += g
        pg.wait_for_selector('#bNext:not([hidden])')
        badges = [pg.text_content(f'#pad{j} .gr') for j in range(1, 5)]
        assert badges == [f'{x} pts' for x in q['g']], badges
        assert 'right' in pg.get_attribute(f"#pad{q['a']}", 'class')
        state = pg.text_content('#stateText')
        assert (state == 'Best answer · 5 points') if g == 5 else (f'{g} point' in state), state
        assert pg.text_content('#explain') == q['e']
        assert int(pg.text_content('#score')) == expected
        pg.click('#bNext')
    pg.wait_for_selector('#doneView:not([hidden])')
    print('practice:', pg.text_content('#doneScore'))
    assert pg.text_content('#doneScore') == f'{expected} of 80 points', pg.text_content('#doneScore')
    s = pg.evaluate('summaryText([lastAttempt])')
    assert '(3 of 5 points)' in s and '- best:' in s, s[:600]
    assert 'Part 2 · ' in s

    # review: the three non-best answers come back
    pg.click('#reviewWrong'); pg.wait_for_selector('#pad1:not([disabled])')
    assert pg.text_content('#qTot') == '3'
    pg.wait_for_timeout(1500); pg.reload()   # let Chromium commit file:// localStorage first

    # mock exam: 4 best (20) + 2 second best (6) = 26 points, 2 unanswered -> pass
    pg.click('#exam-p2mock1')
    ids = EX['p2mock1']['questions']
    for i, qid in enumerate(ids[:6]):
        q = IDX[qid]
        pg.wait_for_function(f"document.getElementById('qText').textContent === {json.dumps(q['q'])}", timeout=5000)
        pg.wait_for_selector('#pad1:not([disabled])')
        assert pg.is_hidden(f'#pad1 .gr'), 'no grades shown during an exam'
        pg.click(f"#pad{q['g'].index(5 if i < 4 else 3) + 1}")
    pg.wait_for_function(f"document.getElementById('qText').textContent === {json.dumps(IDX[ids[6]]['q'])}", timeout=5000)
    pg.click('#bEnd'); pg.click('#bEnd')
    pg.wait_for_selector('#doneView:not([hidden])')
    print('exam:', pg.text_content('#doneScore'), '|', pg.text_content('#doneStats'), '|', pg.text_content('#doneMeta'))
    assert pg.text_content('#doneScore') == '26 of 40 points'
    assert 'pass' in pg.text_content('#doneStats') and 'pass mark 24/40' in pg.text_content('#doneMeta')
    a = pg.evaluate('lastAttempt')
    assert a['graded'] and a['maxPoints'] == 40 and a['passed'] and a['score'] == 26
    csv = pg.evaluate('toCSV([lastAttempt])')
    assert csv.splitlines()[0].endswith('points,max_points')

    pg.wait_for_timeout(1500); pg.reload()   # let Chromium commit file:// localStorage first
    assert 'best 26/40' in pg.text_content('#exam-p2mock1')
    assert 'Part 2 mock 1: 26/40' in pg.text_content('#historyList')
    print('errors:', errs)
    assert not errs
    b.close()
print('OK')

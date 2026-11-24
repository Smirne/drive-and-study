"""Claude Certified Developer pack: spoken scenario set in touch mode, then a silent mock exam (pack.json silentSources)
started from voice mode, with choose-two questions, the practice pass mark, and separate saved results."""
import json, os
from playwright.sync_api import sync_playwright

pack = 'content/claude-dev'
QS = json.load(open(f'{pack}/questions.json'))
IDX = {q['id']: q for q in QS}
EX = json.load(open(f'{pack}/exams.json'))
assert all(IDX[i].get('na') for i in EX['mock1']['questions'] + EX['mock2']['questions']), 'mock questions are silent'
assert not any(IDX[i].get('na') for i in EX['set1']['questions'] + EX['set2']['questions']), 'concept questions are voiced'


def wrong_single(q):
    return (q['a'] % len(q['o'])) + 1


with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={'width': 390, 'height': 844})
    errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script("""HTMLMediaElement.prototype.play=function(){return Promise.resolve()};HTMLMediaElement.prototype.pause=function(){};
      if (!localStorage.getItem('drill-mode')) localStorage.setItem('drill-mode', 'voice');""")
    pg.goto('file://' + os.path.abspath('public/claude-dev/drill.html'))
    assert pg.title() == 'Claude Developer Drill', pg.title()
    assert pg.text_content('#startAll') == 'Concepts: all 50 questions with feedback'
    d1 = pg.text_content('#exam-mock1'); print('mock1 card:', d1)
    assert '60 questions · 120 min · pass 44 · touch only' in d1
    assert 'points' not in pg.text_content('#exam-set1')

    # concept set 2 in touch mode: every fourth wrong -> 18/25
    pg.click('#modeTouch')
    pg.click('#exam-set2')
    for i, qid in enumerate(EX['set2']['questions']):
        q = IDX[qid]
        pg.wait_for_selector('#pad1:not([disabled])')
        assert pg.text_content('#qText') == q['q']
        pg.click(f"#pad{q['a'] if i % 4 != 3 else wrong_single(q)}")
        pg.wait_for_selector('#bNext:not([hidden])')
        pg.click('#bNext')
    pg.wait_for_selector('#doneView:not([hidden])')
    print('set2:', pg.text_content('#doneScore'))
    assert pg.text_content('#doneScore') == '19 of 25 correct'

    # mock exam 2 from voice mode: forced touch, choose-two, pass at 44
    pg.click('#home'); pg.click('#modeVoice')
    pg.click('#exam-mock2')
    assert pg.get_attribute('#app', 'data-mode') == 'touch'
    right = multi = 0
    for i, qid in enumerate(EX['mock2']['questions']):
        q = IDX[qid]
        pg.wait_for_function(f"document.getElementById('pads').children.length === {len(q['o'])} && !document.getElementById('pad1').disabled", timeout=5000)
        assert pg.is_hidden('#qCode')
        ok = i % 5 != 2                                      # 48 right, 12 wrong
        if isinstance(q['a'], list):
            multi += 1
            picks = q['a'] if ok else [j for j in range(1, len(q['o']) + 1) if j not in q['a']][:2]
            for j in picks: pg.click(f'#pad{j}')
            pg.click('#bSubmit')
        else:
            pg.click(f"#pad{q['a'] if ok else wrong_single(q)}")
        right += ok
    pg.wait_for_selector('#doneView:not([hidden])')
    print('mock2:', pg.text_content('#doneScore'), '|', pg.text_content('#doneStats'), '| multi', multi)
    assert multi >= 10 and pg.text_content('#doneScore') == f'{right} of 60 correct' and 'pass' in pg.text_content('#doneStats')
    s = pg.evaluate('summaryText([lastAttempt])')
    assert s.startswith('# Claude Certified Developer (CCDV-F) practice results'), s[:80]
    pg.click('#home')
    assert pg.get_attribute('#app', 'data-mode') == 'voice'
    assert pg.evaluate("JSON.parse(localStorage.getItem('ccdv-history')).length") == 2
    print('errors:', errs)
    assert not errs
    b.close()
print('OK')

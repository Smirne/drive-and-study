"""EventStorming pack drill: concepts practice, graded facilitation scenarios, readiness check,
and separate saved results from the TOGAF pack. Runs in touch mode (no audio needed)."""
import json, os
from playwright.sync_api import sync_playwright

pack = 'content/eventstorming'
QS = json.load(open(f'{pack}/questions.json'))
IDX = {q['id']: q for q in QS}
EX = json.load(open(f'{pack}/exams.json'))
concepts = [q for q in QS if q['id'].startswith('concepts')]

with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={'width': 390, 'height': 844})
    errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    # a TOGAF result already saved on this device must not show up in the EventStorming page
    pg.add_init_script("""HTMLMediaElement.prototype.play=function(){return Promise.resolve()};HTMLMediaElement.prototype.pause=function(){};
      if (!localStorage.getItem('drill-history')) localStorage.setItem('drill-history', JSON.stringify([{attemptId:'t1', title:'Mock exam 1', score:30, total:40, date:'2026-11-01T10:00', items:[]}]));""")
    pg.goto('file://' + os.path.abspath('public/eventstorming/drill.html'))
    assert pg.title() == 'EventStorming Drill', pg.title()
    assert 'Mock exam 1' not in pg.text_content('#historyList')
    pg.click('#modeTouch')
    assert pg.text_content('#startAll') == 'Concepts: 30 questions with feedback'
    assert '12 scenarios' in pg.text_content('#exam-scenarios') and '20 questions · 20 min · pass 14' in pg.text_content('#exam-check')

    # concepts practice: all right except every fifth
    pg.click('#startAll')
    assert len(concepts) == 30
    for i, q in enumerate(concepts):
        pg.wait_for_selector('#pad1:not([disabled])')
        assert pg.text_content('#qText') == q['q'], (i, pg.text_content('#qText'))
        pg.click(f"#pad{q['a'] if i % 5 else (q['a'] % 4) + 1}")
        pg.wait_for_selector('#bNext:not([hidden])')
        pg.click('#bNext')
    pg.wait_for_selector('#doneView:not([hidden])')
    print('concepts:', pg.text_content('#doneScore'))
    assert pg.text_content('#doneScore') == '24 of 30 correct'
    topics = pg.text_content('#doneTopics'); print('topics:', topics[:120])
    assert 'Running a Big Picture' in topics and 'Process Modeling' in topics
    s = pg.evaluate('summaryText([lastAttempt])')
    assert s.startswith('# EventStorming practice results'), s[:60]
    pg.reload()

    # facilitation scenarios: best answer everywhere except one second-best -> 58/60
    pg.click('#exam-scenarios')
    for i, qid in enumerate(EX['scenarios']['questions']):
        q = IDX[qid]
        pg.wait_for_selector('#pad1:not([disabled])')
        assert pg.text_content('#qScen') == q['sc']
        pg.click(f"#pad{q['g'].index(3 if i == 4 else 5) + 1}")
        pg.wait_for_selector('#bNext:not([hidden])')
        assert pg.text_content('#explain') == q['e']
        pg.click('#bNext')
    pg.wait_for_selector('#doneView:not([hidden])')
    print('scenarios:', pg.text_content('#doneScore'))
    assert pg.text_content('#doneScore') == '58 of 60 points'
    pg.reload()

    # readiness check: 15 right -> pass mark 14
    pg.click('#exam-check')
    for i, qid in enumerate(EX['check']['questions']):
        q = IDX[qid]
        pg.wait_for_function(f"document.getElementById('qText').textContent === {json.dumps(q['q'])}", timeout=5000)
        pg.wait_for_selector('#pad1:not([disabled])')
        pg.click(f"#pad{q['a'] if i < 15 else (q['a'] % 4) + 1}")
    pg.wait_for_selector('#doneView:not([hidden])')
    print('check:', pg.text_content('#doneScore'), '|', pg.text_content('#doneStats'))
    assert pg.text_content('#doneScore') == '15 of 20 correct' and 'pass' in pg.text_content('#doneStats')

    pg.reload()
    hist = pg.text_content('#historyList'); print('history:', hist[:160])
    assert 'Readiness check: 15/20' in hist and 'Mock exam 1' not in hist
    assert pg.evaluate("JSON.parse(localStorage.getItem('drill-history')).length") == 1, 'TOGAF history untouched'
    assert pg.evaluate("JSON.parse(localStorage.getItem('es-history')).length") == 3
    print('errors:', errs)
    assert not errs
    b.close()
print('OK')

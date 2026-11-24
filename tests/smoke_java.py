"""Java 25 pack drill: spoken concept set in touch mode, then a code-based mock exam started from voice
mode (silent questions force touch mode for the session), with code blocks and "choose two" questions."""
import json, os
from playwright.sync_api import sync_playwright

pack = 'content/ocp-java25'
QS = json.load(open(f'{pack}/questions.json'))
IDX = {q['id']: q for q in QS}
EX = json.load(open(f'{pack}/exams.json'))


def wrong_single(q):
    return (q['a'] % len(q['o'])) + 1


with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={'width': 390, 'height': 844})
    errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script("""HTMLMediaElement.prototype.play=function(){return Promise.resolve()};HTMLMediaElement.prototype.pause=function(){};
      if (!localStorage.getItem('drill-mode')) localStorage.setItem('drill-mode', 'buttons');""")
    pg.goto('file://' + os.path.abspath('public/java/drill.html'))
    assert pg.title() == 'Java 25 Drill', pg.title()
    assert pg.text_content('#startAll') == 'Concepts: all 50 questions with feedback'
    d1 = pg.text_content('#exam-mock1'); print('mock1 card:', d1)
    assert '50 questions · 120 min · pass 34 · touch only' in d1
    assert 'touch only' not in pg.text_content('#exam-set1')

    # concept set 1 in touch mode: all right except every fifth -> 20/25
    pg.click('#modeTouch')
    pg.click('#exam-set1')
    for i, qid in enumerate(EX['set1']['questions']):
        q = IDX[qid]
        pg.wait_for_selector('#pad1:not([disabled])')
        assert pg.text_content('#qText') == q['q'] and pg.is_hidden('#qCode') and pg.is_hidden('#bSubmit')
        pg.click(f"#pad{q['a'] if i % 5 else wrong_single(q)}")
        pg.wait_for_selector('#bNext:not([hidden])')
        pg.click('#bNext')
    pg.wait_for_selector('#doneView:not([hidden])')
    print('set1:', pg.text_content('#doneScore'))
    assert pg.text_content('#doneScore') == '20 of 25 correct'

    # mock exam 1, started in buttons mode: runs silently in touch mode, then the mode comes back
    pg.click('#home')
    pg.click('#modeButtons')
    assert pg.get_attribute('#app', 'data-mode') == 'buttons'
    pg.click('#exam-mock1')
    assert pg.get_attribute('#app', 'data-mode') == 'touch'
    right = 0
    multi_seen = code_seen = 0
    for i, qid in enumerate(EX['mock1']['questions']):
        q = IDX[qid]
        pg.wait_for_function(f"document.getElementById('pads').children.length === {len(q['o'])} && !document.getElementById('pad1').disabled", timeout=5000)
        if q.get('c'):
            code_seen += 1
            assert pg.text_content('#qCode') == q['c'], qid
        else:
            assert pg.is_hidden('#qCode')
        ok = i % 7 != 3                                      # 43 right, 7 wrong
        if isinstance(q['a'], list):
            multi_seen += 1
            assert pg.is_visible('#bSubmit') and pg.is_disabled('#bSubmit')
            picks = q['a'] if ok else [j for j in range(1, len(q['o']) + 1) if j not in q['a']][:len(q['a'])]
            pg.click(f'#pad{picks[0]}')
            assert pg.is_disabled('#bSubmit') and pg.text_content('#bSubmit') == 'Choose 1 more'
            pg.click(f'#pad{picks[1]}')
            pg.click(f'#pad{picks[1]}'); pg.click(f'#pad{picks[1]}')    # toggle off and on again
            assert pg.is_enabled('#bSubmit') and pg.text_content('#bSubmit') == 'Submit'
            pg.click('#bSubmit')
        else:
            pg.click(f"#pad{q['a'] if ok else wrong_single(q)}")
        right += ok
    pg.wait_for_selector('#doneView:not([hidden])')
    print('mock1:', pg.text_content('#doneScore'), '|', pg.text_content('#doneStats'), '| multi', multi_seen, 'code', code_seen)
    assert multi_seen >= 3 and code_seen >= 40
    assert pg.text_content('#doneScore') == f'{right} of 50 correct' and 'pass' in pg.text_content('#doneStats')
    s = pg.evaluate('summaryText([lastAttempt])')
    assert s.startswith('# Java SE 25 (1Z0-831) practice results') and '```java' in s, s[:200]
    csv = pg.evaluate('toCSV([lastAttempt])')
    assert ' & ' in csv, 'multi answers appear as "1 & 4" in the CSV'
    pg.click('#home')
    assert pg.get_attribute('#app', 'data-mode') == 'buttons', 'mode restored after a silent session'
    assert pg.evaluate("localStorage.getItem('drill-mode')") == 'buttons'

    # review of the mistakes includes silent questions: touch again, with explanations shown after Submit
    pg.wait_for_timeout(1500); pg.reload()   # let Chromium commit file:// localStorage first
    hist = pg.text_content('#historyList'); print('history:', hist[:120])
    assert 'Mock exam 1' in hist
    assert pg.evaluate("JSON.parse(localStorage.getItem('java-history')).length") == 2
    assert pg.evaluate("localStorage.getItem('drill-history')") is None
    print('errors:', errs)
    assert not errs
    b.close()
print('OK')

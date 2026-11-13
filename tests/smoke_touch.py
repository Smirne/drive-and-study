"""Touch mode: silent practice (tap, explanation, Next), review, and a full mock exam by tap.
Fails if any audio is played or any clip is requested."""
import json, os, sys
from playwright.sync_api import sync_playwright

pack = 'content/togaf-foundation'
QS = json.load(open(f'{pack}/questions.json'))
IDX = {q['id']: q for q in QS}
practice = [q for q in QS if q['id'].startswith('ep')]
exam = [IDX[i] for i in json.load(open(f'{pack}/exams.json'))['mock6']['questions']]

with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={'width': 390, 'height': 844})
    errs, mp3 = [], []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.on('request', lambda r: r.url.endswith('.mp3') and mp3.append(r.url))
    pg.add_init_script("""window.__plays=0; HTMLMediaElement.prototype.play=function(){window.__plays++;return Promise.resolve()};
      HTMLMediaElement.prototype.pause=function(){};""")
    pg.goto('file://' + os.path.abspath('public/drill.html'))
    pg.click('#modeTouch')
    assert pg.get_attribute('#modeTouch', 'aria-checked') == 'true'
    assert pg.is_hidden('#bRepeat') and pg.is_hidden('#bPause') and pg.is_hidden('#bVoice')

    # practice: every 4th answer wrong, one skipped
    pg.click('#startAll')
    for i, q in enumerate(practice):
        pg.wait_for_selector('#pad1:not([disabled])')
        assert pg.text_content('#qText') == q['q'], (i, pg.text_content('#qText'))
        if i == 5:
            pg.click('#bSkip')
        else:
            ans = q['a'] if i % 4 else (q['a'] % 4) + 1
            pg.click(f'#pad{ans}')
        pg.wait_for_selector('#bNext:not([hidden])')
        assert not pg.is_hidden('#explain') and pg.text_content('#explain') == q['e']
        assert 'right' in pg.get_attribute(f"#pad{q['a']}", 'class')
        if i == len(practice) - 1:
            assert pg.text_content('#bNext') == 'See results'
        pg.keyboard.press('Enter') if i % 2 else pg.click('#bNext')
    pg.wait_for_selector('#doneView:not([hidden])')
    print('practice:', pg.text_content('#doneScore'), '|', pg.text_content('#doneMeta'))
    assert pg.text_content('#doneScore') == '14 of 20 correct', pg.text_content('#doneScore')
    assert 'touch' in pg.text_content('#doneMeta')

    # review of mistakes
    pg.click('#reviewWrong'); pg.wait_for_selector('#pad1:not([disabled])')
    assert pg.text_content('#qTot') == '6', pg.text_content('#qTot')
    pg.reload()                                             # mode is remembered
    assert pg.get_attribute('#modeTouch', 'aria-checked') == 'true'

    # mock exam 6: no feedback, a tap records and moves on
    pg.click('#exam-mock6')
    for i, q in enumerate(exam):
        pg.wait_for_function(f"document.getElementById('qText').textContent === {json.dumps(q['q'])}", timeout=5000)
        pg.wait_for_selector('#pad1:not([disabled])')
        ans = q['a'] if i < 30 else (q['a'] % 4) + 1        # 30 right, 10 wrong
        pg.click(f'#pad{ans}')
        assert pg.is_hidden('#explain') and pg.is_hidden('#bNext')
    pg.wait_for_selector('#doneView:not([hidden])')
    print('exam:', pg.text_content('#doneScore'), '|', pg.text_content('#doneStats'))
    assert pg.text_content('#doneScore') == '30 of 40 correct'
    assert 'pass' in pg.text_content('#doneStats')
    summary = pg.evaluate("summaryText([lastAttempt])")
    assert 'answered with touch' in summary and 'Mock exam 6' in summary

    plays = pg.evaluate('window.__plays')
    print('audio plays:', plays, '| mp3 requests:', len(mp3), '| errors:', errs)
    assert plays == 0 and not mp3 and not errs
    b.close()
print('OK')

"""Mock exam: no feedback during the exam, timer, results by topic, downloads, summary, review, time-up, history."""
import csv, io, json, os
from playwright.sync_api import sync_playwright

qs = json.load(open('content/togaf-foundation/questions.json'))
exams = json.load(open('content/togaf-foundation/exams.json'))
IDX = {q['id']: i for i, q in enumerate(qs)}
STUB = r"""
HTMLMediaElement.prototype.play = function () {
  const src = this.src, h = this.onended;
  if (!this.loop) setTimeout(() => { if (this.src === src && this.onended === h && h) h(); }, 20);
  return Promise.resolve();
};
HTMLMediaElement.prototype.pause = function () {};
delete window.SpeechRecognition; delete window.webkitSpeechRecognition;
window.DRILL_TIMING = Object.assign({}, window.__examMs ? { examMs: window.__examMs } : {});
"""


def ready(pg, n, timeout=10000):
    # question n on screen and the app waiting for an answer
    pg.wait_for_function(f"""document.getElementById('qNum').textContent=='{n}' && document.getElementById('pad1')
      && !document.getElementById('pad1').disabled
      && /^(Reading question|Tap)/.test(document.getElementById('stateText').textContent)""", timeout=timeout)


def page(ctx, exam_ms=None):
    pg = ctx.new_page()
    errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    if exam_ms:
        pg.add_init_script(f"window.__examMs = {exam_ms};")
    pg.add_init_script(STUB)
    pg.goto('file://' + os.path.abspath('public/drill.html'))
    return pg, errs


with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(permissions=['clipboard-read', 'clipboard-write'], accept_downloads=True, viewport={'width': 390, 'height': 844})

    # ---- A: full mock exam 1 by keyboard: first 30 right, last 10 wrong ----
    pg, errs = page(ctx)
    pg.click('#exam-mock1')
    order = [IDX[i] for i in exams['mock1']['questions']]
    leaked = False
    for n, qi in enumerate(order, start=1):
        ready(pg, n)
        if n == 1:
            print('during exam: timer', pg.text_content('#timer'), '| score hidden', pg.is_hidden('#scoreBox'), '| end button', pg.is_visible('#bEnd'))
        a = qs[qi]['a']
        pg.keyboard.press(str(a if n <= 30 else a % 4 + 1))
        pg.wait_for_function(f"document.getElementById('stateText').textContent.startsWith('Answer') || document.getElementById('qNum').textContent!='{n}' || !document.getElementById('doneView').hidden")
        leaked |= pg.locator('.pad.right, .pad.wrong').count() > 0 or pg.is_visible('#explain')
    pg.wait_for_selector('#doneView:not([hidden])')
    print('feedback leaked during exam:', leaked)
    print('result:', pg.text_content('#doneTitle'), '|', pg.text_content('#doneScore'), '|', pg.text_content('#doneStats'), '|', pg.text_content('#doneMeta'))
    topics = pg.locator('#doneTopics .topic')
    print('topics shown:', topics.count(), '| weakest:', topics.first.text_content())
    with pg.expect_download() as d:
        pg.click('#dlCsv')
    rows = list(csv.reader(io.StringIO(open(d.value.path()).read())))
    print('CSV:', d.value.suggested_filename, '| rows', len(rows) - 1, '| correct', sum(r[15] == 'yes' for r in rows[1:]), '| answered_by', rows[1][17])
    with pg.expect_download() as d:
        pg.click('#dlJson')
    js = json.load(open(d.value.path()))
    print('JSON:', js['title'], js['score'], '/', js['total'], '| passed', js['passed'], '| items', len(js['items']))
    pg.click('#copySummary')
    pg.wait_for_function("document.getElementById('copiedOne').textContent.startsWith('Copied')")
    summary = pg.evaluate('navigator.clipboard.readText()')
    print('summary:', summary.splitlines()[2], '|', summary.splitlines()[3][:60], '| missed listed:', summary.count('- my answer:'))
    assert not leaked and js['score'] == 30 and js['passed'] is True and len(rows) == 41

    # ---- review of the 10 mistakes, with feedback ----
    pg.click('#reviewWrong')
    ready(pg, 1)
    print('review session: questions', pg.text_content('#qTot'), '| score visible', pg.is_visible('#scoreBox'))
    qi = IDX[js['items'][30]['id']]
    pg.keyboard.press(str(qs[qi]['a']))
    pg.wait_for_function("document.getElementById('score').textContent=='1'")
    print('review gives feedback: score after a right answer =', pg.text_content('#score'))
    assert errs == [], errs

    # ---- B: time runs out in mock exam 2 ----
    pg2, errs2 = page(ctx, exam_ms=2500)
    pg2.click('#exam-mock2')
    ready(pg2, 1); pg2.keyboard.press('1')
    pg2.wait_for_selector('#doneView:not([hidden])', timeout=15000)
    print('time-up:', pg2.text_content('#doneScore'), '|', pg2.text_content('#doneMeta'))
    with pg2.expect_download() as d:
        pg2.click('#dlJson')
    j2 = json.load(open(d.value.path()))
    print('time-up items:', len(j2['items']), '| timed out:', sum(i['how'] == 'timeout' for i in j2['items']), '| ended:', j2['ended'])
    assert j2['ended'] == 'time' and len(j2['items']) == 40

    # ---- C: history and export on the start screen ----
    pg2.click('#home')
    print('history rows:', pg2.locator('#historyList .h').count(), '| mock1 button:', pg2.text_content('#exam-mock1 .best').replace('\n', ' '))
    with pg2.expect_download() as d:
        pg2.click('#exportAll')
    allrows = list(csv.reader(io.StringIO(open(d.value.path()).read())))
    print('export all rows:', len(allrows) - 1, '| attempts:', len({r[0] for r in allrows[1:]}))
    assert errs2 == [], errs2
    b.close()
print('exam tests passed')

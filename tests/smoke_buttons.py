"""Car-buttons (scanning) mode, driven only through Media Session next/previous like a steering wheel."""
import json, os
from playwright.sync_api import sync_playwright

qs = json.load(open('content/togaf-foundation/questions.json'))
STUB = r"""
window.__h = {};
if (navigator.mediaSession) {
  navigator.mediaSession.setActionHandler = (a, f) => { window.__h[a] = f; };
}
// every clip "plays" for 30 ms, except explanations (e<i>.mp3), which play until stopped,
// so "next skips the explanation" is tested deterministically; the keep-alive loop never ends
HTMLMediaElement.prototype.play = function () {
  // the timer only ends the clip it was started for (a real element never ends a clip it stopped)
  const src = this.src, h = this.onended;
  if (!this.loop && !/\/e\d+\.mp3$/.test(src)) setTimeout(() => { if (this.src === src && this.onended === h && h) h(); }, 30);
  return Promise.resolve();
};
HTMLMediaElement.prototype.pause = function () {};
delete window.SpeechRecognition; delete window.webkitSpeechRecognition;
"""


def state(pg):
    return pg.text_content('#stateText')


def wait_state(pg, prefix, timeout=15000):
    pg.wait_for_function(f"document.getElementById('stateText').textContent.startsWith({json.dumps(prefix)})", timeout=timeout)


def wait_q(pg, n, timeout=15000):
    pg.wait_for_function(f"document.getElementById('qNum').textContent=='{n}' && document.getElementById('pad1') && !document.getElementById('pad1').disabled", timeout=timeout)


def press(pg, which):
    pg.evaluate(f"window.__h['{which}']({{action: '{which}'}})")


def skip_explanation(pg, next_q):
    pg.wait_for_function("!document.getElementById('explain').hidden && document.getElementById('stateText').textContent.includes('explaining')")
    press(pg, 'nexttrack')
    wait_q(pg, next_q)


with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 390, 'height': 844})
    errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script(STUB)
    pg.goto('file://' + os.path.abspath('public/drill.html'))
    pg.click('#modeButtons')
    print('mode hint:', pg.text_content('#modeHint')[:60], '| mic test hidden:', pg.is_hidden('#micTest'))
    pg.click('#startAll')
    a = [q['a'] for q in qs]

    # Q1: next on the right option, next to confirm, next skips the explanation
    wait_q(pg, 1); wait_state(pg, f'Option {a[0]}'); press(pg, 'nexttrack')
    wait_state(pg, f'Chose {a[0]}'); press(pg, 'nexttrack')
    skip_explanation(pg, 2); print('Q1 choose+confirm -> score', pg.text_content('#score'))

    # Q2: choose a wrong option, previous to change, then choose the right one
    wrong = a[1] % 4 + 1
    wait_state(pg, f'Option {wrong}'); press(pg, 'nexttrack')
    wait_state(pg, f'Chose {wrong}'); press(pg, 'previoustrack')
    wait_state(pg, f'Option {a[1]}'); press(pg, 'nexttrack')
    wait_state(pg, f'Chose {a[1]}'); press(pg, 'nexttrack')
    skip_explanation(pg, 3); print('Q2 change answer -> score', pg.text_content('#score'))

    # Q3: no press: options read twice, then it waits; next restarts the options
    wait_state(pg, 'Next: options again', timeout=30000); print('Q3 idle state:', state(pg))
    press(pg, 'nexttrack')
    wait_state(pg, f'Option {a[2]}'); press(pg, 'nexttrack')
    wait_state(pg, f'Chose {a[2]}'); press(pg, 'nexttrack')
    skip_explanation(pg, 4); print('Q3 after idle -> score', pg.text_content('#score'))

    # Q4: previous during the options goes back to the question, then answer wrong
    wait_state(pg, 'Option 2'); press(pg, 'previoustrack')
    wait_state(pg, 'Option 1'); print('Q4 previous at option 2 -> restarted at:', state(pg))
    wrong = a[3] % 4 + 1
    wait_state(pg, f'Option {wrong}'); press(pg, 'nexttrack')
    wait_state(pg, f'Chose {wrong}'); press(pg, 'nexttrack')
    skip_explanation(pg, 5); print('Q4 wrong answer -> score', pg.text_content('#score'))

    # Q5: a tap on a pad still works in buttons mode
    wait_state(pg, 'Option 1'); pg.click(f'#pad{a[4]}')
    skip_explanation(pg, 6); print('Q5 tap -> score', pg.text_content('#score'))

    log = pg.text_content('#diagLog')
    print('log: keep-alive', 'keep-alive playing' in log, '| confirmed', log.count('confirmed'), '| button presses', log.count('BUTTON'))
    print('errors:', errs)
    assert pg.text_content('#score') == '4', pg.text_content('#score')
    assert not errs
    b.close()

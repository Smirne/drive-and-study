import json, sys
from playwright.sync_api import sync_playwright
qs=json.load(open('content/togaf-foundation/questions.json'))
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={'width':390,'height':844})
    errs=[]; pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script("""HTMLMediaElement.prototype.play=function(){setTimeout(()=>this.onended&&this.onended(),30);return Promise.resolve()};
      HTMLMediaElement.prototype.pause=function(){}; delete window.SpeechRecognition; delete window.webkitSpeechRecognition;""")
    pg.goto('file://'+__import__('os').path.abspath('public/drill.html'))
    pg.click('#startAll')
    for i,q in enumerate(qs):
        pg.wait_for_selector('#pad1:not([disabled])')
        assert pg.text_content('#qText')==q['q'], (i, pg.text_content('#qText'))
        ans = q['a'] if i%4 else (q['a']%4)+1   # every 4th answered wrong
        pg.keyboard.press(str(ans))
        pg.wait_for_function(f"document.getElementById('qNum').textContent!='{i+1}' || !document.getElementById('doneView').hidden", timeout=5000)
    pg.wait_for_selector('#doneView:not([hidden])')
    print('done:', pg.text_content('#doneScore'), '|', pg.text_content('#again'))
    pg.click('#again'); pg.wait_for_selector('#pad1:not([disabled])')
    print('review tot:', pg.text_content('#qTot'))
    print('errors:', errs)
    b.close()

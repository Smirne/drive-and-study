import json, os
from playwright.sync_api import sync_playwright
qs=json.load(open('content/togaf-foundation/questions.json'))
FAKE = """
HTMLMediaElement.prototype.play=function(){ window.__plays=(window.__plays||[]); window.__plays.push(this.src.length);
  setTimeout(()=>this.onended&&this.onended(),20); return Promise.resolve() };
HTMLMediaElement.prototype.pause=function(){};
window.__script=[]; window.__starts=0;
class FakeSR { start(){ window.__starts++; const step = window.__script.length ? window.__script.shift() : {t:'nospeech'};
    setTimeout(()=>{ this.onaudiostart&&this.onaudiostart();
      if(step.t==='say'){ const alt=[{transcript:step.text}]; const res=[alt]; res[0].isFinal=true;
        const r0=Object.assign([...alt],{isFinal:true}); this.onresult&&this.onresult({resultIndex:0,results:[r0]}); }
      else if(step.t==='nospeech'){ this.onerror&&this.onerror({error:'no-speech'}); }
      else if(step.t==='blocked'){ this.onerror&&this.onerror({error:'not-allowed'}); }
      this.onend&&this.onend(); }, 15); }
  abort(){} stop(){} }
window.SpeechRecognition=FakeSR;
"""
def page(b):
    pg=b.new_page(viewport={'width':390,'height':844}); errs=[]
    pg.on('pageerror', lambda e: errs.append(str(e))); pg.add_init_script(FAKE)
    pg.goto('file://'+os.path.abspath('index.html')); return pg, errs
def waitq(pg, n): pg.wait_for_function(f"document.getElementById('qNum').textContent=='{n}' && document.getElementById('pad1') && !document.getElementById('pad1').disabled", timeout=8000)
with sync_playwright() as p:
    b=p.chromium.launch()
    pg,errs=page(b)
    print('secure:', pg.evaluate('isSecureContext'), '| note:', pg.text_content('#voiceNote')[:60])
    # mic test
    pg.evaluate("__script.push({t:'say',text:'number three'})"); pg.click('#micTest')
    pg.wait_for_function("document.getElementById('micResult').textContent.startsWith('Heard')"); print('mic test:', pg.text_content('#micResult'))
    # run: prime consumes one step (nospeech default). Q1 voice correct, Q2: silence x3 -> reprompt then say wrong, Q3: garbage then correct
    a=[q['a'] for q in qs]; W=['one','two','three','four']
    pg.evaluate(f"__script.push({{t:'nospeech'}}, {{t:'say',text:'I think {W[a[0]-1]}'}})")
    pg.click('#startAll')
    waitq(pg,2); print('Q1 by voice -> score', pg.text_content('#score'))
    wrong = W[a[1]%4]
    pg.evaluate(f"__script.push({{t:'nospeech'}},{{t:'nospeech'}},{{t:'nospeech'}},{{t:'say',text:'{wrong}'}})")
    waitq(pg,3); print('Q2 silence x3 then wrong -> score', pg.text_content('#score'))
    pg.evaluate(f"__script.push({{t:'say',text:'banana'}},{{t:'say',text:'two or three'}},{{t:'say',text:'{W[a[2]-1]}'}})")
    waitq(pg,4); print('Q3 garbage, ambiguous, then right -> score', pg.text_content('#score'))
    # Q4: exhaust auto-listen -> Tap to talk appears; press it, then say answer
    pg.evaluate("for(let i=0;i<12;i++)__script.push({t:'nospeech'})")
    pg.wait_for_selector('#bMic:not([hidden])', timeout=15000); print('Q4 tap-to-talk shown, state:', pg.text_content('#stateText'))
    pg.evaluate("__script.length=0"); pg.evaluate(f"__script.push({{t:'say',text:'{W[a[3]-1]}'}})"); pg.click('#bMic')
    waitq(pg,5); print('Q4 via tap-to-talk -> score', pg.text_content('#score'))
    # Q5: say repeat, then skip
    pg.evaluate("__script.push({t:'say',text:'repeat'},{t:'say',text:'skip'})")
    waitq(pg,6); print('Q5 repeat+skip -> score', pg.text_content('#score'))
    # Q6: mic blocked -> falls back to tap
    pg.evaluate("__script.push({t:'blocked'})")
    pg.wait_for_function("document.getElementById('stateText').textContent==='Tap 1–4'", timeout=8000)
    print('Q6 blocked -> state:', pg.text_content('#stateText'), '| voice btn:', pg.text_content('#bVoice'))
    pg.keyboard.press(str(a[5])); waitq(pg,7); print('Q6 by key -> score', pg.text_content('#score'))
    print('errors:', errs); b.close()

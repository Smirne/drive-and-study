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
      else if(step.t==='err'){ this.onerror&&this.onerror({error:step.code}); }
      else if(step.t==='nomatch'){ this.onnomatch&&this.onnomatch({}); }
      this.onend&&this.onend(); }, 15); }
  abort(){} stop(){} }
window.SpeechRecognition=FakeSR;
window.DRILL_TIMING={firstWindowMs:300, laterWindowMs:200, minAttemptMs:10, restartPauseMs:10};
"""
def page(b):
    pg=b.new_page(viewport={'width':390,'height':844}); errs=[]
    pg.on('pageerror', lambda e: errs.append(str(e))); pg.add_init_script(FAKE)
    pg.goto('file://'+os.path.abspath('public/drill.html')); return pg, errs
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
    # Q7: voice back on; mic busy twice (car system), then answer by voice
    pg.click('#bVoice')
    pg.evaluate(f"__script.push({{t:'err',code:'audio-capture'}},{{t:'err',code:'audio-capture'}},{{t:'say',text:'{W[a[6]-1]}'}})")
    waitq(pg,8); print('Q7 mic busy x2 then voice -> score', pg.text_content('#score'))
    # Q8: page hidden while waiting (Android Auto takes the screen), then visible again -> listening resumes
    pg.evaluate("for(let i=0;i<12;i++)__script.push({t:'nospeech'})")
    pg.wait_for_selector('#bMic:not([hidden])', timeout=20000)
    pg.evaluate("__script.length=0")
    pg.evaluate("Object.defineProperty(document,'visibilityState',{configurable:true,get:()=>'hidden'}); document.dispatchEvent(new Event('visibilitychange'))")
    pg.evaluate(f"__script.push({{t:'say',text:'{W[a[7]-1]}'}})")
    pg.evaluate("Object.defineProperty(document,'visibilityState',{configurable:true,get:()=>'visible'}); document.dispatchEvent(new Event('visibilitychange'))")
    waitq(pg,9); print('Q8 hidden/visible -> resumed by voice, score', pg.text_content('#score'))
    # Q9: page hidden mid-listen (Android Auto took the screen): Chrome then refuses with not-allowed.
    # Voice must stay on, and listening resumes when the page is visible again.
    pg.evaluate("Object.defineProperty(document,'visibilityState',{configurable:true,get:()=>'hidden'})")
    pg.evaluate("__script.push({t:'blocked'})")
    pg.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
    pg.wait_for_timeout(2500)
    print('Q9 hidden -> voice btn:', pg.text_content('#bVoice'))
    pg.evaluate(f"__script.length=0; __script.push({{t:'say',text:'{W[a[8]-1]}'}})")
    pg.evaluate("Object.defineProperty(document,'visibilityState',{configurable:true,get:()=>'visible'}); document.dispatchEvent(new Event('visibilitychange'))")
    waitq(pg,10); print('Q9 resumed by voice after hidden -> score', pg.text_content('#score'), '| voice btn:', pg.text_content('#bVoice'))
    # Q10: "nomatch" (speech heard, no words) reprompts at once instead of waiting for 3 silences
    pg.evaluate(f"__script.push({{t:'nomatch'}},{{t:'say',text:'number {W[a[9]-1]}'}})")
    waitq(pg,11); print('Q10 nomatch then "number N" -> score', pg.text_content('#score'))
    # Q11: answer by saying the option's content instead of a number
    said = qs[10]['o'][a[10]-1].rstrip('.')
    pg.evaluate("__script.push(" + json.dumps({'t': 'say', 'text': said}) + ")")
    waitq(pg,12); print('Q11 by content', repr(said[:40]), '-> score', pg.text_content('#score'))
    log = pg.text_content('#diagLog')
    print('content match logged:', 'matched by content' in log)
    print('log has page hidden:', 'page hidden' in log, '| resume:', 'resume listening' in log, '| audio-capture:', 'rec error: audio-capture' in log)
    print('errors:', errs); b.close()

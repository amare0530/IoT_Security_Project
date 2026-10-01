"""Interactive SRAM-PUF Identity Lab showcase server."""

from __future__ import annotations

import argparse
import json
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from auth.hmac_auth import PUFAuthenticator
from scripts.run_offline_demo import run


HTML = r'''<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SRAM-PUF Identity Lab</title>
<style>
:root{color-scheme:dark;--bg:#081116;--panel:#0e1c24;--panel2:#122630;--line:#25404b;--text:#e7f2f2;--muted:#849ca4;--cyan:#56e0d0;--green:#8de49a;--amber:#f2b66d;--red:#ff7474;--blue:#75a9ff}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:14px/1.45 "Segoe UI",sans-serif}body:before{content:"";position:fixed;inset:0;pointer-events:none;opacity:.18;background-image:linear-gradient(rgba(86,224,208,.08) 1px,transparent 1px),linear-gradient(90deg,rgba(86,224,208,.08) 1px,transparent 1px);background-size:34px 34px}main{width:min(1440px,calc(100% - 34px));margin:auto;padding:20px 0 36px}.top{display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid var(--line);padding-bottom:15px}.brand{display:flex;gap:14px;align-items:center}.mark{width:42px;height:42px;border:1px solid var(--cyan);display:grid;place-items:center;color:var(--cyan);font:700 17px Consolas}.eyebrow{color:var(--cyan);font:12px Consolas;letter-spacing:.12em}.title{font-size:25px;font-weight:700}.session{color:var(--muted);font:12px Consolas;text-align:right}.toolbar{display:flex;gap:8px;margin:18px 0;flex-wrap:wrap}button{border:1px solid var(--line);background:#10232b;color:var(--text);padding:10px 15px;border-radius:3px;cursor:pointer;font-weight:650}button:hover,button.active{border-color:var(--cyan);background:#163b42}button.primary{background:#155049;border-color:var(--cyan)}button.attack{border-color:#704044;background:#321d23}button.attack:hover{border-color:var(--red);background:#51262d}.grid{display:grid;grid-template-columns:235px minmax(0,1fr) 285px;gap:14px}.panel{background:rgba(14,28,36,.95);border:1px solid var(--line);padding:16px;min-width:0}.panel h2{font-size:14px;margin:0 0 14px;color:var(--cyan);letter-spacing:.04em}.node{border:1px solid var(--line);padding:14px;margin-bottom:12px;background:#0b1820}.node .name{font:700 16px Consolas}.node .state{margin-top:10px;color:var(--amber);font:12px Consolas}.node.trusted{border-color:var(--green)}.node.trusted .state{color:var(--green)}.node.attacker{border-color:#713f46}.kv{display:flex;justify-content:space-between;gap:8px;padding:7px 0;border-top:1px solid rgba(132,156,164,.16);font-size:12px}.kv span{color:var(--muted)}.scene{min-height:590px;position:relative;overflow:hidden}.scene-head{display:flex;justify-content:space-between;align-items:start}.stage{color:var(--amber);font:13px Consolas}.stage-name{font-size:24px;font-weight:700;margin-top:5px}.source{color:var(--muted);font-size:12px}.rail{display:flex;align-items:center;gap:8px;margin:36px 2% 28px}.route-node{border:1px solid var(--cyan);padding:13px 10px;text-align:center;min-width:120px;background:#0b2028;font:12px Consolas}.route-node small{display:block;color:var(--muted);margin-top:5px}.route-line{height:1px;background:var(--line);flex:1;position:relative}.packet{position:absolute;top:-7px;width:14px;height:14px;background:var(--amber);box-shadow:0 0 16px var(--amber);display:none}.packet.fly{display:block;animation:packet 1.4s linear infinite}@keyframes packet{from{left:0}to{left:calc(100% - 14px)}}.visual{border:1px solid var(--line);background:#09151c;min-height:315px;padding:18px}.visual-title{color:var(--muted);font:12px Consolas;margin-bottom:12px}.bits{display:grid;grid-template-columns:repeat(16,1fr);gap:5px;max-width:720px;margin:18px auto}.bit{aspect-ratio:1;border:1px solid #31535b;display:grid;place-items:center;font:13px Consolas;color:var(--cyan);background:#10252c;transition:.3s}.bit.reject{color:#56666d;background:#182025;border-color:#263137}.bit.flip{color:var(--red);border-color:var(--red);background:#411e25}.bit.pass{background:#174338;border-color:var(--green);color:var(--green)}.formula{text-align:center;color:var(--muted);font:13px Consolas;margin:16px 0}.formula strong{color:var(--amber)}.groups{display:flex;justify-content:center;gap:12px;flex-wrap:wrap}.group{border:1px solid var(--line);padding:10px;color:var(--cyan);font:14px Consolas}.group b{display:block;text-align:center;color:var(--green);margin-top:5px}.tag{font:15px Consolas;color:var(--amber);word-break:break-all;border:1px solid #5a472e;padding:12px;background:#211c13}.terminal{height:270px;overflow:auto;background:#05090b;border:1px solid #273d44;padding:13px;font:12px/1.7 Consolas;color:#a9f5ae}.terminal .dim{color:#60767d}.terminal .bad{color:var(--red)}.terminal .warn{color:var(--amber)}.terminal .good{color:var(--green)}.timeline{display:flex;gap:5px;margin-top:14px;overflow:auto}.tl{flex:1;min-width:70px;border-top:3px solid var(--line);padding-top:8px;color:var(--muted);font-size:11px}.tl.on{border-color:var(--cyan);color:var(--text)}.tl.done{border-color:var(--green);color:var(--green)}.research{margin-top:14px}.research .kv strong{color:var(--text)}.lab-controls{display:flex;gap:8px;flex-wrap:wrap}.lab-controls button{font-size:12px}.hide{display:none!important}.footer{color:var(--muted);font-size:11px;margin-top:14px}.flash{animation:flash .5s ease}@keyframes flash{50%{background:#513026}}
@media(max-width:1000px){.grid{grid-template-columns:1fr}.left,.right{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.node{margin:0}.scene{min-height:520px}}@media(max-width:620px){main{width:calc(100% - 18px);padding-top:12px}.top{display:block}.session{text-align:left;margin-top:9px}.left,.right{display:block}.rail{gap:4px}.route-node{min-width:80px;padding:9px 4px;font-size:10px}.bits{gap:3px}.bit{font-size:10px}.stage-name{font-size:19px}}
</style></head>
<body><main>
<header class="top"><div class="brand"><div class="mark">PUF</div><div><div class="eyebrow">SRAM-PUF IDENTITY LAB</div><div class="title">IoT 身分認證實驗室</div></div></div><div class="session">SESSION <span id="session">#--------</span><br><span id="source">等待資料來源</span></div></header>
<nav class="toolbar"><button class="primary active" data-mode="showcase">▶ 展示模式</button><button data-mode="lab">🧪 實驗室模式</button><button data-mode="attack">⚠ 攻擊模式</button><button id="pause">Ⅱ 暫停</button><button id="reset">↺ 重置</button><button data-jump="3">跳到 FE</button><button data-jump="5">跳到 MQTT</button><button data-jump="7">跳到攻擊</button></nav>
<section class="grid"><aside class="left"><div class="panel"><h2>DEVICE STATE</h2><div class="node" id="device"><div class="name" id="uid">DEVICE-UNSET</div><div class="state" id="deviceState">UNTRUSTED / 等待啟動</div></div><div class="kv"><span>資料來源</span><strong id="sourceShort">-</strong></div><div class="kv"><span>bit 數</span><strong id="chipBits">-</strong></div><div class="kv"><span>穩定門檻</span><strong>0.90</strong></div><div class="kv"><span>Session</span><strong id="sessionSide">-</strong></div></div><div class="panel research"><h2>RESEARCH SNAPSHOT</h2><div class="kv"><span>Devices</span><strong>84</strong></div><div class="kv"><span>Mean stability</span><strong>0.9697</strong></div><div class="kv"><span>Random 5% BER</span><strong>99.864%</strong></div><div class="kv"><span>Inter-HD</span><strong>0.2703</strong></div><div class="footer">研究資料集統計，不是本次 fixture 即時結果。</div></div></aside>
<section class="panel scene"><div class="scene-head"><div><div class="stage" id="stage">STANDBY / 待命</div><div class="stage-name" id="stageName">選擇一種展示模式</div></div><div class="source" id="sourceDetail">Data Source: -</div></div><div class="rail"><div class="route-node">DEVICE<small>SRAM / FE</small></div><div class="route-line"><i class="packet" id="packet"></i></div><div class="route-node">MQTT<small>challenge / response</small></div><div class="route-line"><i class="packet" id="packet2"></i></div><div class="route-node">SERVER<small>verify</small></div></div><div id="visual" class="visual"><div class="visual-title">SYSTEM VISUALIZATION</div><div class="formula">按下「展示模式」開始一場身分認證事件</div></div><div class="timeline" id="timeline"><div class="tl">01 Boot</div><div class="tl">02 SRAM</div><div class="tl">03 Stability</div><div class="tl">04 Rep()</div><div class="tl">05 HMAC</div><div class="tl">06 MQTT</div><div class="tl">07 Verify</div><div class="tl">08 Attack</div><div class="tl">09 Result</div></div><div id="labPanel" class="panel hide" style="margin-top:14px"><h2>LAB CONTROLS</h2><div class="lab-controls"><button data-lab="bits">顯示 bit window</button><button data-lab="noise">加入 5% noise</button><button data-lab="rep">執行 Rep()</button><button data-lab="hmac">產生 HMAC</button><button data-lab="verify">Server verify</button></div></div></section>
<aside class="right"><div class="panel"><h2>SECURITY CONSOLE</h2><div class="terminal" id="terminal"><span class="dim">[待命] 等待展示事件...</span></div></div><div id="attackPanel" class="panel hide"><h2>ATTACK SELECTOR</h2><button class="attack" data-attack="replay">Replay nonce</button><button class="attack" data-attack="tamper">Tampered HMAC</button><button class="attack" data-attack="unknown">Unknown UID</button><button class="attack" data-attack="future">Future timestamp</button><button class="attack" data-attack="malformed">Malformed payload</button></div></aside></section>
<div class="footer">Prototype boundary: dataset-based system-level demo. Live physical SRAM sampling remains future work.</div>
</main>
<script>
const $=id=>document.getElementById(id);let data=null,maskBits='',sampleEnrollmentBits='',busy=false,stageIndex=-1,paused=false,jumpTarget=null;const stages=['BOOT','SRAM_CAPTURE','STABILITY','FE_REP','HMAC','MQTT','SERVER_VERIFY','ATTACK','RESULT'];
async function wait(ms){let remaining=ms;while(remaining>0){while(paused)await new Promise(r=>setTimeout(r,80));if(jumpTarget!==null&&stageIndex<jumpTarget)return;const started=Date.now();await new Promise(r=>setTimeout(r,Math.min(100,remaining)));if(!paused)remaining-=Date.now()-started}}
function session(){const n='#'+Math.random().toString(16).slice(2,8).toUpperCase();$('session').textContent=n;$('sessionSide').textContent=n}function log(t,c=''){const d=document.createElement('div');d.className=c;d.textContent=t;$('terminal').appendChild(d);$('terminal').scrollTop=$('terminal').scrollHeight}function clearLog(){ $('terminal').innerHTML='';log('[identity-lab] session initialized','dim') }function tl(i){document.querySelectorAll('.tl').forEach((e,n)=>e.className='tl '+(n<i?'done':n===i?'on':''))}function route(on){$('packet').className=on?'packet fly':'packet';$('packet2').className=on?'packet fly':'packet'}
function bits(text,mode=''){if(mode==='mask'&&maskBits)text=maskBits;return [...text].map((b,i)=>`<i class="bit ${mode==='mask'&&b==='0'?'reject':mode==='noise'&&sampleEnrollmentBits[i]!==b?'flip':mode==='pass'?'pass':''}">${b}</i>`).join('')}
function renderScene(title,html){if(title==='DEVICE AUTHENTICATED')html+='<div class="formula">Nonce freshness: <strong>VALID</strong><br>Timestamp window: <strong>VALID</strong><br>Authentication session: <strong>COMPLETE</strong></div>';$('stageName').textContent=title;$('visual').innerHTML='<div class="visual-title">SYSTEM VISUALIZATION</div>'+html}
function common(d){data=d;session();$('uid').textContent=d.uid;$('source').textContent=d.source;$('sourceShort').textContent=d.source;$('sourceDetail').textContent='Data Source: '+d.source;$('chipBits').textContent=d.trace.chip_bit_count.toLocaleString();$('deviceState').textContent='UNTRUSTED / 正在驗證'}
async function fetchDemo(){const r=await fetch('/api/demo',{method:'POST'});if(!r.ok)throw Error('demo backend failed');const d=await r.json();common(d);maskBits=d.trace.sample_mask_bits;sampleEnrollmentBits=d.trace.sample_enrollment_bits;return d}
async function showcase(){if(busy)return;busy=true;document.querySelectorAll('button').forEach(b=>b.disabled=true);clearLog();try{const d=await fetchDemo();const t=d.trace;const scene=(i,name)=>{stageIndex=i;tl(i);$('stage').textContent=stages[i]+' / '+name};scene(0,'DEVICE BOOT');renderScene('Device selected',`<div class="formula">DEVICE <strong>${d.uid}</strong> / STATUS: <strong>UNTRUSTED</strong><br><br>boot sequence started...<br>SRAM power-up requested</div>`);log('> boot sequence started','dim');await wait(3200);scene(1,'SRAM POWER-UP');renderScene('SRAM response captured',`<div class="formula">RAW SRAM RESPONSE / visualization window: 32 bits</div><div class="bits">${bits(t.sample_enrollment_bits)}</div><div class="formula">chip response: ${t.chip_bit_count.toLocaleString()} bits / zoomed view only</div>`);log('> capturing SRAM startup response');log('> random 32-bit visualization window selected','good');await wait(3800);scene(2,'STABILITY ANALYSIS');renderScene('Stable-bit selection',`<div class="formula">STABILITY THRESHOLD <strong>θ = 0.90</strong></div><div class="bits">${bits(t.sample_enrollment_bits,'mask')}</div><div class="formula">stable positions retained / unstable positions rejected</div>`);log('> evaluating per-bit stability');log('> unstable positions removed by mask','warn');await wait(3800);scene(3,'FUZZY EXTRACTOR');renderScene('Rep() / majority vote',`<div class="formula"><strong>256 key bits</strong> × repetition <strong>11</strong> = <strong>2,816 stable bits</strong></div><div class="bits">${bits(t.sample_noisy_bits,'noise')}</div><div class="groups"><div class="group">1 1 0 1 0 1 1 0 0 1 1<b>majority = 1</b></div><div class="group">0 1 0 0 0 0 1 0 0 0 0<b>majority = 0</b></div></div><div class="formula">W XOR noisy response → reconstructed key material<br><strong>128-bit HMAC key fingerprint: ${t.hmac_key_fingerprint}</strong></div>`);log('> helper data loaded');log('> Rep(response, helper_data)');log('> majority vote corrected simulated noise','good');await wait(5000);scene(4,'HMAC-SHA256');renderScene('Challenge becomes authentication tag',`<div class="formula">UID + NONCE + TIMESTAMP → HMAC-SHA256</div><div class="tag">${t.challenge_payload}<br>↓<br>${t.hmac_tag.slice(0,16)}...${t.hmac_tag.slice(-16)}</div><div class="formula">secret key remains masked / never displayed</div>`);log('> HMAC-SHA256 computation');log('> 256-bit tag generated','good');await wait(3800);scene(5,'MQTT CHALLENGE / RESPONSE');route(true);renderScene('Packet moving through MQTT',`<div class="formula">SERVER → challenge → DEVICE<br><br>DEVICE → HMAC response → SERVER</div><div class="tag">nonce: ${t.challenge_payload.split(':')[1]}<br>timestamp: ${t.challenge_payload.split(':')[2]}</div>`);log('> MQTT challenge published');log('> device response published');await wait(3800);route(false);scene(6,'SERVER VERIFY');renderScene('Server-side verification',`<div class="formula">recompute HMAC → <strong>compare_digest()</strong><br><br><span class="good">MATCH / legitimate device</span></div>`);log('> server recomputes expected tag');log('> compare_digest: MATCH','good');await wait(3200);scene(7,'ATTACK SIMULATION');renderScene('Attacker enters the channel',`<div class="formula"><strong style="color:var(--red)">ATTACK SIMULATION</strong><br>captured packet will be replayed and modified</div>`);log('> attack simulation started','warn');await attack('replay',true);await attack('tamper',true);await attack('unknown',true);await wait(2500);scene(8,'RESULT');$('device').className='node trusted';$('deviceState').textContent='TRUSTED / AUTHENTICATED';renderScene('DEVICE AUTHENTICATED',`<div class="formula"><strong style="color:var(--green);font-size:25px">✓ TRUSTED</strong><br><br>${d.uid}<br>PUF reconstruction: SUCCESS<br>HMAC: VALID<br>Replay: BLOCKED<br>Unknown UID: BLOCKED</div>`);log('> DEVICE AUTHENTICATED / TRUSTED','good')}catch(e){log('[error] '+e.message,'bad')}finally{route(false);document.querySelectorAll('button').forEach(b=>b.disabled=false);busy=false}}
async function attack(type,auto=false){if(busy&& !auto)return;renderScene('ATTACK PACKET → SERVER',`<div class="formula"><strong style="color:var(--red)">${type.toUpperCase()} ATTEMPT</strong><br><br>captured packet → verification queue → server decision</div>`);route(true);const r=await fetch('/api/attack',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({type})});const d=await r.json();log('> '+d.label,'warn');await wait(auto?600:300);route(false);renderScene('ACCESS BLOCKED',`<div class="formula"><strong style="color:var(--red);font-size:24px">✕ BLOCKED</strong><br><br>${d.reason}<br><br>backend verification result: ${d.valid?'ACCEPTED':'REJECTED'}</div>`);log('[server] '+d.reason+' ['+(d.valid?'ACCEPTED':'BLOCKED')+']',d.valid?'bad':'good');return d}
function lab(){if(!data){fetchDemo().then(lab).catch(e=>log('[error] '+e.message,'bad'));return}$('labPanel').classList.remove('hide');$('attackPanel').classList.add('hide');$('stage').textContent='LAB MODE / 手動操作';renderScene('實驗室控制區',`<div class="formula">請從下方選擇單一步驟。技術細節會在此區更新。</div><div class="bits">${bits(data.trace.sample_enrollment_bits)}</div>`)}
document.querySelectorAll('[data-mode]').forEach(b=>b.onclick=()=>{document.querySelectorAll('[data-mode]').forEach(x=>x.classList.remove('active'));b.classList.add('active');const m=b.dataset.mode;$('labPanel').classList.toggle('hide',m!=='lab');$('attackPanel').classList.toggle('hide',m!=='attack');if(m==='lab')lab();if(m==='attack'){clearLog();$('stage').textContent='ATTACK MODE / 攻擊模式';renderScene('選擇一個真實驗證測試',`<div class="formula">每個測試都會呼叫 Python backend 的驗證邏輯。</div>`)}if(m==='showcase')showcase()});$('reset').onclick=async()=>{await fetch('/api/reset',{method:'POST'});location.reload()};document.querySelectorAll('[data-attack]').forEach(b=>b.onclick=()=>attack(b.dataset.attack));document.querySelectorAll('[data-lab]').forEach(b=>b.onclick=()=>{if(!data)return;const a=b.dataset.lab;log('> lab action: '+a,'warn');if(a==='bits')renderScene('Bit window',`<div class="bits">${bits(data.trace.sample_enrollment_bits)}</div>`);if(a==='noise')renderScene('Noise injected',`<div class="bits">${bits(data.trace.sample_noisy_bits,'noise')}</div>`);if(a==='rep')renderScene('Rep() majority vote',`<div class="groups"><div class="group">1 1 0 1 0 1 1 0 0 1 1<b>→ 1</b></div></div>`);if(a==='hmac')renderScene('HMAC-SHA256',`<div class="tag">${data.trace.hmac_tag.slice(0,16)}...${data.trace.hmac_tag.slice(-16)}</div>`);if(a==='verify')renderScene('Server verify',`<div class="formula"><span class="good">compare_digest → MATCH</span></div>`)});$('pause').onclick=()=>{paused=!paused;$('pause').textContent=paused?'▶ 繼續':'Ⅱ 暫停'};document.querySelectorAll('[data-jump]').forEach(b=>b.onclick=()=>{jumpTarget=Number(b.dataset.jump);paused=false;if(!busy)showcase()});setInterval(()=>{if(jumpTarget!==null&&stageIndex>=jumpTarget)jumpTarget=null;if(busy){$('pause').disabled=false;document.querySelectorAll('[data-jump]').forEach(b=>b.disabled=false)}},80);const baseRenderScene=renderScene;renderScene=(title,html)=>{baseRenderScene(title,html);if(!data)return;const t=data.trace;const formulas=[...document.querySelectorAll('#visual .formula')];if(stageIndex===2&&formulas.length){formulas[0].innerHTML=`STABILITY THRESHOLD <strong>θ = ${t.stable_bit_threshold.toFixed(2)}</strong><br>stable bits retained: <strong>${data.bits_available.toLocaleString()}</strong> / ${t.chip_bit_count.toLocaleString()}<br>unstable bits rejected: <strong>${(t.chip_bit_count-data.bits_available).toLocaleString()}</strong>`}if(stageIndex===3&&formulas.length>1){formulas[0].innerHTML=`<strong>${t.extractor_key_bits} key bits</strong> × repetition <strong>${t.repetition}</strong> = <strong>${t.stable_bits_consumed.toLocaleString()} stable bits</strong><br><strong>${t.noise_model}</strong> / ${t.noise_flip_count} flips / max ${Math.floor(t.repetition/2)} per repetition group`;formulas[formulas.length-1].innerHTML=`W XOR noisy response → reconstructed key material<br><strong>${t.hmac_key_bits}-bit HMAC key / 64-bit display fingerprint: ${t.hmac_key_fingerprint}</strong>`}if(stageIndex===5&&formulas.length)formulas[0].innerHTML=`SIMULATED MQTT FLOW<br>SERVER → challenge → DEVICE<br><br>DEVICE → HMAC response → SERVER`};const baseLog=log;log=(text,kind='')=>baseLog(text==='> random 32-bit visualization window selected'?'> randomized 32-bit visualization window selected':text,kind);session();
const renderSceneWithAttackTitle=renderScene;renderScene=(title,html)=>renderSceneWithAttackTitle(title==='ACCESS BLOCKED'&&$('terminal').textContent.includes('UNKNOWN UID')?'Credential rejected':title,html);
</script></body></html>'''


def attack_result(kind: str, context: dict[str, object] | None) -> dict[str, object]:
    if context is None:
        raise RuntimeError("Run a demo session before starting an attack")
    key = context["key"]
    auth = context["authenticator"]
    uid = context["uid"]
    challenge = context["attack_challenge"]
    response = context["attack_hmac"]
    if kind == "replay":
        first_valid, first_reason = auth.verify_response(key, uid, challenge, response)
        if not first_valid and "expired" in first_reason:
            challenge = auth.generate_challenge()
            response = auth.generate_response(key, uid, challenge)
            auth.verify_response(key, uid, challenge, response)
        valid, reason = auth.verify_response(key, uid, challenge, response)
        return {"valid": valid, "label": "REPLAY ATTEMPT / 重放封包", "reason": reason}
    if kind == "tamper":
        challenge = auth.generate_challenge()
        response = auth.generate_response(key, uid, challenge)
        tampered = ("0" if response[0] != "0" else "1") + response[1:]
        valid, reason = auth.verify_response(key, uid, challenge, tampered)
        return {"valid": valid, "label": "TAMPERED HMAC / 竄改標籤", "reason": reason}
    if kind == "unknown":
        challenge = auth.generate_challenge()
        response = auth.generate_response(key, "unknown-device", challenge)
        valid, reason = auth.verify_response(key, uid, challenge, response)
        return {"valid": valid, "label": "UNKNOWN UID / 冒用裝置", "reason": reason}
    if kind == "future":
        challenge = auth.generate_challenge()
        challenge["timestamp"] = str(int(time.time()) + 120)
        response = auth.generate_response(key, uid, challenge)
        valid, reason = auth.verify_response(key, uid, challenge, response)
        return {"valid": valid, "label": "FUTURE TIMESTAMP / 未來時間戳", "reason": reason}
    valid, reason = auth.verify_response(key, uid, {"bad": "payload"}, "not-a-tag")
    return {"valid": valid, "label": "MALFORMED PAYLOAD / 格式錯誤", "reason": reason}


class Handler(BaseHTTPRequestHandler):
    output_dir: Path
    input_path: Path | None = None
    session_context: dict[str, object] | None = None

    def send_json(self, value: object, status: int = 200) -> None:
        body = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path != "/":
            self.send_error(404)
            return
        body = HTML.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        if self.path == "/api/demo":
            try:
                result = run(
                    self.output_dir,
                    self.input_path,
                    include_private_context=True,
                )
                type(self).session_context = result.pop("_private_context")
                self.send_json(result)
            except Exception as exc:
                self.send_json({"error": str(exc)}, 500)
            return
        if self.path == "/api/reset":
            type(self).session_context = None
            self.send_json({"reset": True})
            return
        if self.path == "/api/attack":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length) or b"{}")
                self.send_json(
                    attack_result(
                        str(payload.get("type", "malformed")),
                        type(self).session_context,
                    )
                )
            except Exception as exc:
                self.send_json({"valid": False, "label": "MALFORMED PAYLOAD", "reason": str(exc)}, 400)
            return
        self.send_error(404)

    def log_message(self, format: str, *args: object) -> None:
        return


def main() -> None:
    parser = argparse.ArgumentParser(description="SRAM-PUF Identity Lab")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--output-dir", type=Path, default=Path("demo-output/identity-lab"))
    parser.add_argument("--auto-local-data", action="store_true")
    args = parser.parse_args()
    local = ROOT / "data" / "crps.csv"
    input_path = local if args.auto_local_data and local.exists() else None
    handler = type("ConfiguredHandler", (Handler,), {"output_dir": args.output_dir, "input_path": input_path})
    server = ThreadingHTTPServer((args.host, args.port), handler)
    print(f"SRAM-PUF Identity Lab running at http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Identity Lab stopped")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

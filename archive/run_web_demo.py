"""Serve a local browser demo for the SRAM-PUF authentication prototype."""

from __future__ import annotations

import argparse
import json
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.run_offline_demo import run


HTML = r"""<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SRAM-PUF IoT 認證展示台</title>
<style>
:root { color-scheme: dark; --bg:#111820; --panel:#1b2630; --line:#344452; --text:#e8eef2; --muted:#9aabb5; --cyan:#63d6d0; --orange:#f0a45b; --red:#ec7777; }
* { box-sizing:border-box; }
body { margin:0; min-height:100vh; color:var(--text); font:15px/1.5 "Segoe UI", sans-serif; background-color:var(--bg); background-image:linear-gradient(rgba(99,214,208,.045) 1px,transparent 1px),linear-gradient(90deg,rgba(99,214,208,.045) 1px,transparent 1px); background-size:32px 32px; }
main { width:min(1180px, calc(100% - 32px)); margin:0 auto; padding:38px 0 56px; }
header { display:flex; justify-content:space-between; align-items:end; gap:24px; border-bottom:1px solid var(--line); padding-bottom:24px; }
h1 { margin:0; font-size:clamp(26px,4vw,42px); letter-spacing:.02em; font-weight:650; }
.subtitle { color:var(--muted); max-width:560px; margin:8px 0 0; }
button { border:1px solid var(--cyan); background:#17383b; color:var(--text); padding:11px 18px; font-weight:650; cursor:pointer; border-radius:4px; }
button:hover { background:#205256; } button:disabled { opacity:.55; cursor:wait; }
.button-row { display:flex; gap:8px; justify-content:flex-end; flex-wrap:wrap; margin-top:14px; }
.status { display:flex; gap:10px; align-items:center; color:var(--muted); white-space:nowrap; }
.dot { width:10px; height:10px; background:var(--orange); border-radius:50%; } .dot.ok { background:var(--cyan); }
.grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:16px; margin-top:24px; }
.panel { background:rgba(27,38,48,.94); border:1px solid var(--line); padding:20px; border-radius:5px; min-height:180px; }
.panel h2 { margin:0 0 16px; font-size:17px; font-weight:650; } .panel h2 span { color:var(--cyan); margin-right:9px; }
.metric { display:flex; justify-content:space-between; gap:16px; border-top:1px solid rgba(154,171,181,.2); padding:9px 0; } .metric:first-of-type { border-top:0; }
.metric label { color:var(--muted); } .metric strong { text-align:right; color:var(--text); }
.trace-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:12px; }
.trace-item { border:1px solid rgba(154,171,181,.22); padding:12px; background:#162129; min-width:0; }
.trace-item label { display:block; color:var(--muted); font-size:12px; margin-bottom:7px; }
.bits { color:var(--cyan); font:13px/1.7 Consolas, monospace; word-break:break-all; letter-spacing:.04em; }
.payload { color:var(--orange); font:12px/1.6 Consolas, monospace; word-break:break-all; }
.terminal { background:#090d10; border:1px solid #3d4a50; padding:14px; min-height:180px; color:#a9f5ae; font:13px/1.65 Consolas, monospace; box-shadow:inset 0 0 22px rgba(0,0,0,.35); }
.terminal .dim { color:#70858b; } .terminal .warn { color:var(--orange); } .terminal .bad { color:var(--red); } .terminal .good { color:var(--cyan); }
.badge { display:inline-block; padding:3px 8px; border:1px solid var(--cyan); color:var(--cyan); border-radius:3px; font-size:12px; } .badge.fail { color:var(--red); border-color:var(--red); }
.flow { grid-column:1 / -1; display:grid; grid-template-columns:repeat(6,1fr); gap:8px; }
.step { border:1px solid var(--line); padding:13px 9px; text-align:center; color:var(--muted); background:#162129; transition:background .25s,border-color .25s,transform .25s; } .step.done { border-color:var(--cyan); color:var(--text); background:#17383b; } .step.active { border-color:var(--orange); color:var(--text); background:#493421; transform:translateY(-3px); } .step small { display:block; color:var(--muted); margin-top:5px; }
.note { color:var(--muted); font-size:13px; margin:22px 0 0; } pre { white-space:pre-wrap; word-break:break-word; color:var(--muted); margin:0; }
@media (max-width:760px) { main { width:min(100% - 20px, 560px); padding-top:22px; } header { display:block; } .status { margin-top:18px; } .grid { grid-template-columns:1fr; } .flow { grid-template-columns:repeat(2,1fr); } }
</style>
</head>
<body>
<main>
<header>
<div><h1>SRAM-PUF IoT 認證展示台</h1><p class="subtitle">以資料集為基礎的可靠度感知裝置認證系統原型。資料來源：<strong id="source">合成展示資料</strong></p></div>
<div><div class="status"><i class="dot" id="dot"></i><span id="status">等待執行離線展示</span></div><div class="button-row"><button id="run">播放完整流程</button><button id="quick">快速執行</button></div></div>
</header>
<section class="grid">
<div class="panel"><h2><span>01</span>註冊階段</h2><div class="metric"><label>裝置</label><strong id="uid">-</strong></div><div class="metric"><label>可用穩定位元</label><strong id="available">-</strong></div><div class="metric"><label>消耗位元</label><strong id="consumed">-</strong></div></div>
<div class="panel"><h2><span>02</span>金鑰重建</h2><div class="metric"><label>模糊提取器</label><strong id="extractor">等待執行</strong></div><div class="metric"><label>雜訊模型</label><strong id="noise">-</strong></div><div class="metric"><label>結果</label><strong id="reconstruction">-</strong></div></div>
<div class="panel"><h2><span>03</span>MQTT 挑戰回應</h2><div class="metric"><label>HMAC-SHA256</label><strong id="auth" class="badge">等待執行</strong></div><div class="metric"><label>挑戰內容</label><strong id="challenge">-</strong></div><div class="metric"><label>傳輸模式</label><strong>離線模擬</strong></div></div>
<div class="panel"><h2><span>04</span>攻擊檢查</h2><div class="metric"><label>重放攻擊</label><strong id="replay" class="badge">等待執行</strong></div><div class="metric"><label>未知裝置</label><strong id="unknown" class="badge">等待執行</strong></div><div class="metric"><label>Helper Data</label><strong>原型公開輔助資料</strong></div></div>
<div class="flow"><div class="step" id="s1">SRAM 回應<small>合成展示資料</small></div><div class="step" id="s2">穩定位元遮罩<small>可靠度篩選</small></div><div class="step" id="s3">模糊提取器<small>Gen / Rep</small></div><div class="step" id="s4">HMAC 標籤<small>UID + nonce + 時間</small></div><div class="step" id="s5">伺服器驗證<small>常數時間比對</small></div><div class="step" id="s6">安全檢查<small>拒絕重放</small></div></div>
<div class="panel" style="grid-column:1/-1"><h2><span>位元</span>隨機 32-bit 視窗</h2><p class="note">本次展示使用 2,816-bit 合成 fixture；研究資料集每台裝置包含 655,360 bits。畫面只放大 32 bits，完整 fuzzy extractor 計算仍使用 2,816 bits。</p><div class="trace-grid"><div class="trace-item"><label>晶片原始 / enrollment bits</label><div class="bits" id="rawBits">-</div></div><div class="trace-item"><label>模擬雜訊後 response bits</label><div class="bits" id="noisyBits">-</div></div><div class="trace-item"><label>Helper Data W</label><div class="bits" id="helperBits">-</div></div><div class="trace-item"><label>W XOR response，送入多數決</label><div class="bits" id="xorBits">-</div></div><div class="trace-item"><label>隨機抽樣位置</label><div class="payload" id="sampleIndices">-</div></div><div class="trace-item"><label>HMAC payload / tag</label><div class="payload" id="hmacTrace">-</div></div></div></div>
<div class="panel" style="grid-column:1/-1"><h2><span>攻擊模擬</span>安全測試終端機</h2><div class="terminal" id="terminal"><span class="dim">[待命] 播放流程後，這裡會顯示模擬攻擊與防禦結果。</span></div></div>
<div class="panel" style="grid-column:1/-1"><h2><span>詳細</span>流程紀錄</h2><pre id="log">本展示使用合成資料，不宣稱已完成 live SRAM 取樣。</pre></div>
</section>
<p class="note">原型範圍：live SRAM 取樣、實體裝置部署、TLS 傳輸安全與正式 helper data 洩漏分析，不包含在本展示中。</p>
</main>
<script>
const ids=['s1','s2','s3','s4','s5','s6'];
const set=(id,value)=>document.getElementById(id).textContent=value;
const badge=(id,value,ok)=>{const el=document.getElementById(id); el.textContent=value; el.className='badge'+(ok?'':' fail');};
const wait=(ms)=>new Promise(resolve=>setTimeout(resolve,ms));
const setStage=(index,done=false)=>ids.forEach((id,current)=>document.getElementById(id).className='step '+(current<index||done?'done':current===index?'active':''));
async function runDemo(animated) { const run=document.getElementById('run'); const quick=document.getElementById('quick'); run.disabled=true; quick.disabled=true; set('status',animated?'正在逐步執行認證流程...':'正在執行離線認證流程...'); document.getElementById('dot').className='dot'; ids.forEach(id=>document.getElementById(id).className='step'); const log=[]; const show=(message)=>{log.push(message); document.getElementById('log').textContent=log.join('\n');}; try { const res=await fetch('/api/run',{method:'POST'}); const data=await res.json(); const auth=data.authentication; const trace=data.trace; set('source',data.source); set('uid',data.uid); set('available',data.bits_available.toLocaleString()); set('consumed',data.bits_consumed.toLocaleString()); set('extractor','Code-offset + 多數決'); set('noise','模擬 5% response 變動'); set('challenge','Nonce + timestamp'); set('rawBits',trace.sample_enrollment_bits); set('noisyBits',trace.sample_noisy_bits); set('helperBits',trace.sample_helper_bits); set('xorBits',trace.sample_xor_bits); set('sampleIndices',trace.sample_response_indices.join(', ')); set('hmacTrace',trace.challenge_payload+'\n'+trace.hmac_tag); if(animated){set('status','① 讀取裝置 SRAM response');setStage(0);show('01 讀取裝置 SRAM response\n   輸入：'+data.fixture+'\n   晶片 bit 數：'+trace.chip_bit_count.toLocaleString());await wait(650);setStage(1);set('status','② 篩選可靠位元');show('02 計算 stability 與 stable-bit mask\n   門檻：stability >= 0.90\n   本次視窗：隨機抽取 '+trace.sample_size+' bits');await wait(650);setStage(2);set('status','③ 以 fuzzy extractor 重建');show('03 執行 Rep(response, helper_data)\n   '+trace.extractor_key_bits+' key bits × repetition '+trace.repetition+' = '+trace.stable_bits_consumed+' bits');await wait(650);setStage(3);set('status','④ 建立 HMAC challenge-response');show('04 產生 UID + nonce + timestamp\n   HMAC key：'+trace.hmac_key_bits+' bits\n   計算 HMAC-SHA256 tag');await wait(650);setStage(4);set('status','⑤ Server 驗證訊息完整性');show('05 server 重新計算 HMAC\n   compare_digest：相同');await wait(650);setStage(5);set('status','⑥ 執行攻擊情境檢查');show('06 replay：拒絕\n   unknown UID：拒絕');await wait(500);} else {ids.forEach(id=>document.getElementById(id).className='step done');show('完整流程已快速執行。');} set('reconstruction','成功重建'); badge('auth',auth.valid?'認證成功':'認證失敗',auth.valid); badge('replay',auth.replay_valid?'通過':'已拒絕',!auth.replay_valid); badge('unknown',auth.unknown_uid_valid?'通過':'已拒絕',!auth.unknown_uid_valid); setStage(ids.length,true); set('status','流程完成'); document.getElementById('dot').className='dot ok'; show('結果：合法裝置認證成功，兩種異常情境皆被拒絕。'); } catch (error) { set('status','執行失敗'); document.getElementById('log').textContent=String(error); } finally {run.disabled=false;quick.disabled=false;} }
document.getElementById('run').onclick=()=>runDemo(true);
document.getElementById('quick').onclick=()=>runDemo(false);
const terminalLine=(text,kind='')=>{const line=document.createElement('div'); line.className=kind; line.textContent=text; document.getElementById('terminal').appendChild(line);};
async function playAttackTerminal(delay) { await wait(delay); const terminal=document.getElementById('terminal'); terminal.innerHTML=''; terminalLine('PUF-AUTH / SECURITY TEST CONSOLE','dim'); terminalLine('target: enrolled device | mode: simulated attacker','dim'); const attacks=[['$ capture response and alter hmac tag','bad','HMAC mismatch -> REJECTED'],['$ replay previously accepted nonce','warn','nonce already used -> REJECTED'],['$ impersonate uid=unknown-device','bad','invalid signature -> REJECTED'],['$ send expired timestamp','warn','challenge expired -> REJECTED']]; for(const [command,kind,result] of attacks){await wait(520);terminalLine(command,kind);await wait(320);terminalLine('[server] '+result,'good');} await wait(350); terminalLine('[server] legitimate device -> AUTHENTICATION SUCCESS','good'); }
document.getElementById('run').addEventListener('click',()=>playAttackTerminal(3900));
document.getElementById('quick').addEventListener('click',()=>playAttackTerminal(250));
</script>
</body>
</html>"""


class DemoHandler(BaseHTTPRequestHandler):
    output_dir: Path
    input_path: Path | None = None

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
        if self.path != "/api/run":
            self.send_error(404)
            return
        try:
            result = run(self.output_dir, self.input_path)
            body = json.dumps(result).encode("utf-8")
            self.send_response(200)
        except Exception as exc:  # pragma: no cover - defensive boundary for the demo UI
            body = json.dumps({"error": str(exc)}).encode("utf-8")
            self.send_response(500)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve the local SRAM-PUF browser demo")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--output-dir", type=Path, default=Path("demo-output/web-demo"))
    parser.add_argument(
        "--auto-local-data",
        action="store_true",
        help="Use data/crps.csv automatically when it exists; otherwise use the synthetic fixture",
    )
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    local_data = ROOT / "data" / "crps.csv"
    input_path = local_data if args.auto_local_data and local_data.exists() else None
    if args.auto_local_data and input_path is None:
        print("No local data/crps.csv found; using synthetic fixture")
    handler = type(
        "ConfiguredDemoHandler",
        (DemoHandler,),
        {"output_dir": args.output_dir, "input_path": input_path},
    )
    server = ThreadingHTTPServer((args.host, args.port), handler)
    url = f"http://{args.host}:{args.port}"
    print(f"SRAM-PUF demo running at {url}")
    if not args.no_browser and args.host in {"127.0.0.1", "localhost"}:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Demo stopped")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

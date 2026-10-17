/**
 * e2e_chat_height.mjs — verify the /chat (DietChat) page occupies exactly 100vh
 * (empty state, no chatbot reply) with NO page scroll. Reuses the zero-dep CDP
 * harness pattern from e2e_assessment.mjs.
 *
 * Run: node e2e_chat_height.mjs   (backend :8000 + frontend :3000 must be up)
 */
import { spawn } from 'node:child_process';
import { existsSync, mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const APP = 'http://localhost:3000';
const API = 'http://localhost:8000/api/v1';
const PORT = 9334;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function api(method, path, { token, body } = {}) {
  const res = await fetch(API + path, {
    method,
    headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: 'Bearer ' + token } : {}) },
    body: body ? JSON.stringify(body) : undefined,
  });
  const text = await res.text();
  let json = {};
  try { json = JSON.parse(text); } catch { /* ignore */ }
  return { status: res.status, json };
}

const email = `height_check_${Date.now()}@test.local`;
const password = 'Test1234!';
const reg = await api('POST', '/auth/register', { body: { name: 'Height Check', email, password, age: 45, gender: 0 } });
console.log('API register:', reg.status);
if (reg.status !== 200) { console.log('ABORT:', JSON.stringify(reg.json).slice(0, 200)); process.exit(1); }
const token = reg.json.access_token;
const refresh = reg.json.refresh_token || '';
const user = reg.json.user || { id: reg.json.user?.id, name: 'Height Check' };

// ── Chrome/Edge via CDP ──
const CHROME_CANDIDATES = [
  join(process.env.ProgramFiles || 'C:\\Program Files', 'Google\\Chrome\\Application\\chrome.exe'),
  join(process.env['ProgramFiles(x86)'] || 'C:\\Program Files (x86)', 'Google\\Chrome\\Application\\chrome.exe'),
  join(process.env.LOCALAPPDATA || '', 'Google\\Chrome\\Application\\chrome.exe'),
  join(process.env.ProgramFiles || 'C:\\Program Files', 'Microsoft\\Edge\\Application\\msedge.exe'),
  join(process.env['ProgramFiles(x86)'] || 'C:\\Program Files (x86)', 'Microsoft\\Edge\\Application\\msedge.exe'),
];
const chromePath = CHROME_CANDIDATES.find((p) => p && existsSync(p));
if (!chromePath) { console.log('ABORT: no Chrome/Edge'); process.exit(1); }
console.log('browser:', chromePath);

const profileDir = mkdtempSync(join(tmpdir(), 'chat-height-chrome-'));
spawn(chromePath, [
  '--headless=new', `--remote-debugging-port=${PORT}`, `--user-data-dir=${profileDir}`,
  '--no-first-run', '--no-default-browser-check', '--disable-gpu', '--disable-extensions',
  '--disable-background-networking', '--window-size=1440,1000', 'about:blank',
], { stdio: 'ignore' });

async function cdpEndpoint() {
  for (let i = 0; i < 60; i++) {
    try { const r = await fetch(`http://127.0.0.1:${PORT}/json/version`); if (r.ok) return (await r.json()).webSocketDebuggerUrl; }
    catch { /* not up yet */ }
    await sleep(300);
  }
  throw new Error('CDP not reachable');
}

class CDP {
  constructor(ws) {
    this.ws = ws; this.id = 0; this.pending = new Map(); this.handlers = new Map();
    ws.onmessage = (ev) => {
      const m = JSON.parse(ev.data);
      if (m.id && this.pending.has(m.id)) {
        const { res, rej } = this.pending.get(m.id); this.pending.delete(m.id);
        m.error ? rej(new Error(JSON.stringify(m.error))) : res(m.result);
      } else if (m.method) { for (const h of (this.handlers.get(m.method) || [])) h(m.params, m.sessionId); }
    };
  }
  send(method, params = {}, sessionId) {
    const id = ++this.id; const payload = { id, method, params };
    if (sessionId) payload.sessionId = sessionId;
    return new Promise((res, rej) => { this.pending.set(id, { res, rej }); this.ws.send(JSON.stringify(payload)); });
  }
  on(method, h) { if (!this.handlers.has(method)) this.handlers.set(method, []); this.handlers.get(method).push(h); }
}

const endpoint = await cdpEndpoint();
const ws = new WebSocket(endpoint);
await new Promise((res, rej) => { ws.onopen = res; ws.onerror = () => rej(new Error('ws error')); });
const cdp = new CDP(ws);
const { targetId } = await cdp.send('Target.createTarget', { url: 'about:blank' });
const { sessionId } = await cdp.send('Target.attachToTarget', { targetId, flatten: true });
await cdp.send('Page.enable', {}, sessionId);
await cdp.send('Runtime.enable', {}, sessionId);

async function evaluate(expression) {
  const r = await cdp.send('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true }, sessionId);
  if (r.exceptionDetails) throw new Error('eval error: ' + JSON.stringify(r.exceptionDetails).slice(0, 300));
  return r.result.value;
}
async function goto(url) {
  let done; const loaded = new Promise((res) => { done = res; });
  cdp.on('Page.loadEventFired', () => done());
  await cdp.send('Page.navigate', { url }, sessionId);
  await Promise.race([loaded, sleep(15000)]);
  await sleep(500);
}
async function waitFor(expr, timeout = 15000) {
  const t0 = Date.now();
  while (Date.now() - t0 < timeout) { try { if (await evaluate(expr)) return true; } catch { /* retry */ } await sleep(250); }
  return false;
}

// Seed auth into localStorage, then open /chat
await goto(`${APP}/login`);
await evaluate(`(() => {
  localStorage.setItem('access_token', ${JSON.stringify(token)});
  localStorage.setItem('refresh_token', ${JSON.stringify(refresh)});
  localStorage.setItem('user', ${JSON.stringify(JSON.stringify(user))});
  return true;
})()`);
await goto(`${APP}/chat`);
const emptyOk = await waitFor(`/Your AI Diet Advisor/.test(document.body.innerText)`, 15000);
console.log('empty state rendered:', emptyOk);
await sleep(600);

const m = await evaluate(`(() => {
  const de = document.documentElement;
  const el = document.querySelector('[class*="calc(100vh"]');
  const r = el ? el.getBoundingClientRect() : null;
  return {
    innerHeight: window.innerHeight,
    innerWidth: window.innerWidth,
    docScrollHeight: de.scrollHeight,
    bodyScrollHeight: document.body.scrollHeight,
    pageScrolls: de.scrollHeight > window.innerHeight + 1,
    chatFound: !!el,
    chatHeight: r ? Math.round(r.height) : null,
    chatTop: r ? Math.round(r.top) : null,
    chatBottom: r ? Math.round(r.bottom) : null,
    expectedChatHeight: window.innerHeight - 48,
    inputVisible: (() => { const i = document.querySelector('#chat-input'); if (!i) return false; const ir = i.getBoundingClientRect(); return ir.bottom <= window.innerHeight + 1 && ir.top >= -1; })(),
  };
})()`);

console.log('\n=== MEASUREMENTS ===');
console.log(JSON.stringify(m, null, 2));
console.log('\n=== VERDICT ===');
const exact = m.chatFound && Math.abs(m.chatHeight - m.expectedChatHeight) <= 2;
console.log('chat container ~ (100vh - 3rem):', exact ? 'PASS' : 'FAIL', '(' + m.chatHeight + ' vs ' + m.expectedChatHeight + ')');
console.log('page does not scroll (fits 100vh):', !m.pageScrolls ? 'PASS' : 'FAIL');
console.log('input visible in viewport:', m.inputVisible ? 'PASS' : 'FAIL');

try { ws.close(); } catch { /* ignore */ }
process.exit(0);

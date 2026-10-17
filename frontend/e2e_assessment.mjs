/**
 * e2e_assessment.mjs — REAL-BROWSER end-to-end smoke (zero npm deps).
 *
 * Kyun: API-level e2e (`e2e_api_smoke.py`) backend contract verify karta hai par UI/DOM nahi.
 * Purana browser e2e file disk pe nahi tha aur koi puppeteer/playwright dep bhi nahi.
 * Solution: Chrome ko **DevTools Protocol** se drive karo — Node >=21 ke built-in `WebSocket`
 * aur `fetch` se, koi install nahi.
 *
 * Kya karta hai (real Chrome, headless): API se user+predict setup → UI login → HealthForm
 * fields/screening sections render check → Dashboard 16 cards (labels) → Simulator run →
 * SHAP page → DietChat round-trip + "New Chat" reset → console errors check → screenshots.
 *
 * Run: node frontend/e2e_assessment.mjs   (backend :8000 + frontend :3000 chalu hone chahiye)
 * Exit code 0 = ALL PASS.
 */
import { spawn } from 'node:child_process';
import { existsSync, mkdirSync, mkdtempSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const APP = 'http://localhost:3000';
const API = 'http://localhost:8000/api/v1';
const PORT = 9333;
const ROOT = join(import.meta.dirname, '..');
const LOGS = join(ROOT, 'logs');
mkdirSync(LOGS, { recursive: true });

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const fails = [];
const consoleErrors = [];
function check(name, ok, detail = '') {
  console.log((ok ? 'PASS ' : 'FAIL ') + name + (detail ? ' | ' + detail : ''));
  if (!ok) fails.push(name);
}

// ─────────────────────────── API setup (data for the UI) ───────────────────────────
const SCREENINGS = {
  diabetes: { freq_urination: 'yes', excess_thirst: 'yes', weight_loss: 'yes' },
  heart: { chest_pain: 'yes', short_breath: 'yes', palpitations: 'yes' },
  hypertension: { headaches: 'yes', dizziness: 'yes', blurred_vision: 'yes' },
  obesity: { sugary_diet: 'yes', freq_hunger: 'yes', hard_lose_weight: 'yes' },
  stroke: { tia_symptoms: 'yes', speech_difficulty: 'yes', irregular_heartbeat: 'yes' },
  sleep_apnea: { snoring: 'yes', wake_tired: 'yes', witnessed_apnea: 'yes', daytime_sleepy: 'yes' },
  gad7: { answers: [2, 2, 2, 2, 2, 2, 2] },
  ckd: { ankle_swelling: 'yes', urination_changes: 'yes', ckd_fatigue: 'yes' },
  liver: { jaundice: 'yes', abdominal_pain: 'yes', liver_fatigue: 'yes' },
  metabolic_syndrome: { doctor_high_bp: 'yes', doctor_high_sugar: 'yes', frequent_thirst_urination: 'yes' },
  thyroid: { fatigue: 'yes', weight_change: 'yes', temperature_issues: 'yes', hair_skin: 'yes' },
  pcos: { irregular_periods: 'yes', weight_gain: 'yes', excess_hair: 'yes', acne: 'yes' },
  anemia: { frequent_fatigue: 'yes', pale_cold: 'yes', lightheadedness: 'yes', brittle_nails: 'yes' },
  burnout: { work_hours: 55, job_satisfaction: 2, exhaustion: [2, 2, 2] },
  colorectal: { blood_in_stool: 'yes', bowel_change: 'yes', colorectal_weight_loss: 'yes' },
  lung_cancer_exposure: { passive_smoke: 'yes', persistent_cough: 'yes', coughing_blood: 'yes', breath_shortness: 'yes' },
};

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

const email = `browser_e2e_${Date.now()}@test.local`;
const password = 'Test1234!';
let token, uid, predictionId, labels = [];

{
  const reg = await api('POST', '/auth/register', { body: { name: 'Browser E2E', email, password, age: 45, gender: 0 } });
  check('API register', reg.status === 200, reg.status);
  token = reg.json.access_token; uid = reg.json.user?.id;

  const pred = await api('POST', '/predict', {
    token,
    body: {
      name: 'Browser E2E', age: 45, gender: 0, height: 160, weight: 82, sleep_hours: 5,
      exercise_level: 0, smoking: true, alcohol: 5, family_history: [1, 1, 1, 1], phq9: [3, 3, 3, 3, 3, 3, 3, 3, 3],
      bp_systolic: 145, bp_diastolic: 92, waist_circumference: 95, diet_quality: 'poor',
      screening_responses: SCREENINGS,
    },
  });
  predictionId = pred.json.prediction_id;
  check('API predict 16 rows', (pred.json.disease_risk_results || []).length === 16,
    `n=${(pred.json.disease_risk_results || []).length}`);

  const dz = await api('GET', '/diseases', { token });
  const list = Array.isArray(dz.json) ? dz.json : (dz.json.diseases || []);
  labels = list.map((d) => d.label).filter(Boolean);
  check('API diseases labels', labels.length === 16, `n=${labels.length}`);
}

// ─────────────────────────── Chrome via CDP ───────────────────────────
const CHROME_CANDIDATES = [
  join(process.env.ProgramFiles || 'C:\\Program Files', 'Google\\Chrome\\Application\\chrome.exe'),
  join(process.env['ProgramFiles(x86)'] || 'C:\\Program Files (x86)', 'Google\\Chrome\\Application\\chrome.exe'),
  join(process.env.LOCALAPPDATA || '', 'Google\\Chrome\\Application\\chrome.exe'),
  join(process.env.ProgramFiles || 'C:\\Program Files', 'Microsoft\\Edge\\Application\\msedge.exe'),
  join(process.env['ProgramFiles(x86)'] || 'C:\\Program Files (x86)', 'Microsoft\\Edge\\Application\\msedge.exe'),
];
const chromePath = CHROME_CANDIDATES.find((p) => p && existsSync(p));
check('Chrome/Edge binary found', !!chromePath, chromePath);

if (!chromePath) { console.log('\nRESULT: 1 FAIL (no browser)'); process.exit(1); }

const profileDir = mkdtempSync(join(tmpdir(), 'e2e-chrome-'));
const chrome = spawn(chromePath, [
  '--headless=new', `--remote-debugging-port=${PORT}`, `--user-data-dir=${profileDir}`,
  '--no-first-run', '--no-default-browser-check', '--disable-gpu', '--disable-extensions',
  '--disable-background-networking', '--window-size=1440,1000', 'about:blank',
], { stdio: 'ignore' });

async function cdpEndpoint() {
  for (let i = 0; i < 60; i++) {
    try {
      const r = await fetch(`http://127.0.0.1:${PORT}/json/version`);
      if (r.ok) return (await r.json()).webSocketDebuggerUrl;
    } catch { /* not up yet */ }
    await sleep(300);
  }
  throw new Error('Chrome CDP endpoint not reachable');
}

class CDP {
  constructor(ws) {
    this.ws = ws; this.id = 0; this.pending = new Map(); this.handlers = new Map();
    ws.onmessage = (ev) => {
      const m = JSON.parse(ev.data);
      if (m.id && this.pending.has(m.id)) {
        const { res, rej } = this.pending.get(m.id); this.pending.delete(m.id);
        m.error ? rej(new Error(JSON.stringify(m.error))) : res(m.result);
      } else if (m.method) {
        for (const h of (this.handlers.get(m.method) || [])) h(m.params, m.sessionId);
      }
    };
  }
  send(method, params = {}, sessionId) {
    const id = ++this.id;
    const payload = { id, method, params };
    if (sessionId) payload.sessionId = sessionId;
    return new Promise((res, rej) => { this.pending.set(id, { res, rej }); this.ws.send(JSON.stringify(payload)); });
  }
  on(method, h) {
    if (!this.handlers.has(method)) this.handlers.set(method, []);
    this.handlers.get(method).push(h);
  }
}

const endpoint = await cdpEndpoint();
const ws = new WebSocket(endpoint);
await new Promise((res, rej) => { ws.onopen = res; ws.onerror = (e) => rej(new Error('ws error')); });
const cdp = new CDP(ws);

const { targetId } = await cdp.send('Target.createTarget', { url: 'about:blank' });
const { sessionId } = await cdp.send('Target.attachToTarget', { targetId, flatten: true });
await cdp.send('Page.enable', {}, sessionId);
await cdp.send('Runtime.enable', {}, sessionId);
await cdp.send('Log.enable', {}, sessionId);
await cdp.send('Network.enable', {}, sessionId);

// Console/page error capture (ignoring known cosmetic favicon 404s)
cdp.on('Runtime.consoleAPICalled', (p) => {
  if (p.type === 'error') {
    const t = (p.args || []).map((a) => a.value ?? a.description ?? '').join(' ');
    if (!/vite\.svg|favicon/i.test(t)) consoleErrors.push('console.error: ' + t.slice(0, 200));
  }
}, sessionId);
cdp.on('Runtime.exceptionThrown', (p) => {
  consoleErrors.push('exception: ' + (p.exceptionDetails?.exception?.description || p.exceptionDetails?.text || '').slice(0, 200));
}, sessionId);
cdp.on('Log.entryAdded', (p) => {
  if (p.entry?.level === 'error' && !/vite\.svg|favicon/i.test(p.entry.text || '')) {
    consoleErrors.push('log: ' + (p.entry.text || '').slice(0, 200));
  }
}, sessionId);

async function evaluate(expression) {
  const r = await cdp.send('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true }, sessionId);
  if (r.exceptionDetails) throw new Error('eval error: ' + JSON.stringify(r.exceptionDetails).slice(0, 300));
  return r.result.value;
}

async function goto(url) {
  let done;
  const loaded = new Promise((res) => { done = res; });
  const handler = () => done();
  cdp.on('Page.loadEventFired', handler);
  await cdp.send('Page.navigate', { url }, sessionId);
  await Promise.race([loaded, sleep(15000)]);
  await sleep(400); // React mount
}

async function waitFor(expr, timeout = 20000, label = expr) {
  const t0 = Date.now();
  while (Date.now() - t0 < timeout) {
    try { if (await evaluate(expr)) return true; } catch { /* retry */ }
    await sleep(250);
  }
  console.log(`   (timed out waiting: ${label})`);
  return false;
}

function setInput(sel, val) {
  return `(() => { const el = document.querySelector(${JSON.stringify(sel)}); if (!el) return false;
    const proto = el.tagName === 'TEXTAREA' ? window.HTMLTextAreaElement.prototype
      : el.tagName === 'SELECT' ? window.HTMLSelectElement.prototype : window.HTMLInputElement.prototype;
    const set = Object.getOwnPropertyDescriptor(proto, 'value').set;
    set.call(el, ${JSON.stringify(String(val))});
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
    return true; })()`;
}
function clickSel(sel) {
  return `(() => { const el = document.querySelector(${JSON.stringify(sel)}); if (!el) return false; el.click(); return true; })()`;
}
function clickText(text) {
  return `(() => { const t = ${JSON.stringify(text)};
    const el = [...document.querySelectorAll('button, a')].find((b) => (b.innerText || '').includes(t));
    if (!el) return false; el.click(); return true; })()`;
}
// React controlled input: native setter + event, PHIR state sahi set hone tak wait (race fix)
async function fill(sel, val) {
  await evaluate(setInput(sel, val));
  await waitFor(`(() => { const e = document.querySelector(${JSON.stringify(sel)});
    return !!e && String(e.value) === ${JSON.stringify(String(val))}; })()`, 5000, 'fill ' + sel);
  await sleep(150);
}
const bodyText = `document.body.innerText`;
async function screenshot(name) {
  try {
    const { data } = await cdp.send('Page.captureScreenshot', { format: 'png' }, sessionId);
    writeFileSync(join(LOGS, `e2e_${name}.png`), Buffer.from(data, 'base64'));
  } catch { /* best effort */ }
}

// ─────────────────────────── 1) Login via UI ───────────────────────────
await goto(`${APP}/login`);
check('login page renders', await waitFor(`!!document.querySelector('#login-email')`, 20000, '#login-email'));
await fill('#login-email', email);
await fill('#login-password', password);
await evaluate(clickSel('button[type=submit]'));
const loggedIn = await waitFor(`location.pathname === '/' && /Health Assessment/.test(document.body.innerText)`, 30000, 'redirect to HealthForm');
check('UI login → HealthForm', loggedIn, await evaluate(`location.pathname`));

// screening catalogs async load hote hain — sections render hone tak wait karo
await waitFor(`document.querySelectorAll('[role=radiogroup]').length >= 10`, 25000, 'screening sections');

// ─────────────────────────── 2) HealthForm UI ───────────────────────────
const hf = await evaluate(`(() => {
  const ids = ['hf-name','hf-age','hf-gender','hf-height','hf-weight','hf-sleep','hf-exercise','hf-alcohol','bp_systolic','bp_diastolic','waist_circumference'];
  const missing = ids.filter((id) => !document.getElementById(id));
  const screeningGroups = document.querySelectorAll('[role=radiogroup]').length;
  const submit = !!document.querySelector('button[type=submit]');
  return { missing, screeningGroups, submit };
})()`);
check('HealthForm fields render', hf.missing.length === 0, `missing=${JSON.stringify(hf.missing)}`);
check('HealthForm screening/phq9 sections render', hf.screeningGroups >= 10, `radiogroups=${hf.screeningGroups}`);
check('HealthForm submit button', hf.submit === true);
await screenshot('healthform');

// ─────────────────────────── 3) Dashboard — 16 cards ───────────────────────────
await goto(`${APP}/dashboard`);
const dashOk = await waitFor(`/Health Dashboard/.test(document.body.innerText)`, 30000, 'Health Dashboard h1');
check('Dashboard renders', dashOk);
const missingLabels = await evaluate(`(() => { const t = document.body.innerText; return ${JSON.stringify(labels)}.filter((l) => !t.includes(l)); })()`);
check('Dashboard shows all 16 disease labels', missingLabels.length === 0, `missing=${JSON.stringify(missingLabels)}`);
const hasRiskNumbers = await evaluate(`/\\d+%/.test(document.body.innerText) && /Biological Age/i.test(document.body.innerText)`);
check('Dashboard shows risk % + bio age', hasRiskNumbers);
await screenshot('dashboard');

// ─────────────────────────── 4) Simulator ───────────────────────────
await goto(`${APP}/simulator`);
check('Simulator renders', await waitFor(`/Future Health Simulator/.test(document.body.innerText)`, 30000, 'Simulator h1'));
await evaluate(clickText('Run Simulation'));
const simOk = await waitFor(`/Projected Results/.test(document.body.innerText) && /Biological Age/.test(document.body.innerText)`, 30000, 'simulation results');
check('Simulator run → results', simOk);
const simLabels = await evaluate(`(() => { const t = document.body.innerText; return ${JSON.stringify(labels)}.filter((l) => t.includes(l)).length; })()`);
check('Simulator disease comparison rows', simLabels >= 10, `labels shown=${simLabels}`);
await screenshot('simulator');

// ─────────────────────────── 5) SHAP page ───────────────────────────
await goto(`${APP}/shap/${predictionId}`);
check('SHAP page renders', await waitFor(`!!document.querySelector('#shap-disease')`, 30000, '#shap-disease'));
const shapRows = await evaluate(`document.body.innerText.split('\\n').filter((l) => l.trim().length > 1).length > 20`);
check('SHAP page shows content', shapRows === true);
await screenshot('shap');

// ─────────────────────────── 6) DietChat round-trip + New Chat ───────────────────────────
await goto(`${APP}/chat`);
check('DietChat renders', await waitFor(`!!document.querySelector('#chat-input')`, 30000, '#chat-input'));
const emptyState = await evaluate(`/Your AI Diet Advisor/.test(document.body.innerText)`);
check('DietChat empty state', emptyState === true);
await fill('#chat-input', 'Generate my diet plan');
await evaluate(clickSel('button[aria-label="Send message"]'));
const gotReply = await waitFor(`(() => { const log = document.querySelector('[aria-label="Chat messages"]'); const hasNew = !!document.querySelector('button[aria-label="Start a new chat session"]'); return hasNew && log && log.innerText.length > 60; })()`, 60000, 'assistant reply');
const replyLen = await evaluate(`(() => { const r = document.querySelector('[aria-label="Chat messages"]'); return r ? r.innerText.length : 0; })()`);
check('DietChat assistant reply', gotReply, `reply chars=${replyLen}`);
await screenshot('chat_reply');
await evaluate(clickSel('button[aria-label="Start a new chat session"]'));
const reset = await waitFor(`/Your AI Diet Advisor/.test(document.body.innerText) && !document.querySelector('button[aria-label="Start a new chat session"]')`, 8000, 'New Chat reset');
check('DietChat New Chat resets', reset, await evaluate(`document.body.innerText.slice(-40)`));

// ─────────────────────────── 7) Console errors ───────────────────────────
check('No JS console errors', consoleErrors.length === 0, consoleErrors.slice(0, 3).join(' ;; '));

// ─────────────────────────── teardown ───────────────────────────
try { ws.close(); } catch { /* ignore */ }
try { chrome.kill(); } catch { /* ignore */ }

console.log('\nRESULT:', fails.length === 0 ? 'ALL PASS' : `${fails.length} FAIL: ${fails.join(', ')}`);
process.exit(fails.length === 0 ? 0 : 1);

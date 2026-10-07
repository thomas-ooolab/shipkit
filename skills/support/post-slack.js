#!/usr/bin/env node
// post-slack.js — post ONE Slack message as the user, optionally with files/images attached.
//
//   usage: node post-slack.js <channel_id> <thread_ts|-> [file ...]   < message text on stdin
//          node post-slack.js --self-test
//
// <thread_ts> is the ROOT; `-` only for a top-level DM. No files -> chat.postMessage. With files ->
// Slack's external upload flow (files.getUploadURLExternal -> POST bytes -> files.completeUploadExternal),
// the text becoming the initial_comment, so text and files land as ONE message in the thread.
//   exit 0  posted — prints `OK ts=<ts|->` (ts is `-` when Slack's reply doesn't carry one yet)
//   exit 2  bad usage (missing args, or nothing to post).
//   exit 3  $SLACK_REVIEW_TOKEN unset (user token; files need the files:write scope).
//   exit 4  Slack rejected a call — prints `SLACK_ERROR: <error>` (msg_too_long, missing_scope, …).
//   exit 5  a file is unusable (missing, not a regular file, empty, or looks like a secret) — nothing posted.
//
// Text goes via stdin and the token via env, so neither lands in argv / shell history. Never prints the token.
// SLACK_API_BASE exists only so --self-test can point at a local mock.

'use strict';

const fs = require('fs');
const path = require('path');

const API = process.env.SLACK_API_BASE || 'https://slack.com/api';
// ponytail: filename blocklist, not a content scan — the caller still decides what is relevant to attach.
// Secrets/credentials, plus DB dumps (production data / PII).
const SECRET_NAME = /^\.env|\.pem$|\.key$|\.p12$|id_rsa|id_ed25519|credentials|secret|^settings(\.local)?\.json$|\.sql$|\.dump$/i;

class Fail extends Error { constructor(code, msg) { super(msg); this.code = code; } }

const slack = async (api, token, method, body) => {
  const res = await fetch(`${api}/${method}`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json; charset=utf-8' },
    body: JSON.stringify(body),
  });
  const j = await res.json();
  if (!j.ok) throw new Fail(4, `SLACK_ERROR: ${j.error}`);
  return j;
};

function checkFile(f) {
  let st;
  try { st = fs.statSync(f); } catch { throw new Fail(5, `FILE_ERROR: ${f} does not exist`); }
  if (!st.isFile() || st.size === 0) throw new Fail(5, `FILE_ERROR: ${f} is not a non-empty regular file`);
  if (SECRET_NAME.test(path.basename(f))) throw new Fail(5, `FILE_ERROR: ${f} looks like a secret, credential or DB-dump file — not attaching`);
  return st.size;
}

// Returns the posted message ts, or '-' when unknown. The waiter ignores my own messages by account id,
// so a '-' just means last_seen_ts stays where it was.
async function post({ api = API, token, channel, thread, text, files = [] }) {
  const sizes = files.map(checkFile); // validate everything before posting anything
  if (!files.length) {
    const j = await slack(api, token, 'chat.postMessage', { channel, ...(thread && { thread_ts: thread }), text });
    return j.ts;
  }
  const ids = [];
  for (const [i, f] of files.entries()) {
    // getUploadURLExternal takes form fields, not JSON.
    const q = new URLSearchParams({ filename: path.basename(f), length: String(sizes[i]) });
    const r = await (await fetch(`${api}/files.getUploadURLExternal`, {
      method: 'POST', headers: { Authorization: `Bearer ${token}` }, body: q,
    })).json();
    if (!r.ok) throw new Fail(4, `SLACK_ERROR: ${r.error}`);
    const up = await fetch(r.upload_url, { method: 'POST', body: fs.readFileSync(f) });
    if (!up.ok) throw new Fail(4, `SLACK_ERROR: upload of ${path.basename(f)} failed (HTTP ${up.status})`);
    ids.push({ id: r.file_id, title: path.basename(f) });
  }
  const j = await slack(api, token, 'files.completeUploadExternal', {
    files: ids, channel_id: channel, ...(thread && { thread_ts: thread }), ...(text && { initial_comment: text }),
  });
  const shares = Object.values(j.files?.[0]?.shares?.public ?? j.files?.[0]?.shares?.private ?? {})[0];
  return shares?.[0]?.ts ?? '-';
}

async function main() {
  const [channel, thread, ...files] = process.argv.slice(2);
  const token = process.env.SLACK_REVIEW_TOKEN;
  if (!token) { console.error('SLACK_REVIEW_TOKEN is not set — export the user token (xoxp-…, scopes chat:write, files:write).'); process.exit(3); }
  if (!channel || !thread) { console.error('usage: post-slack.js <channel_id> <thread_ts|-> [file ...] < text'); process.exit(2); }
  const text = fs.readFileSync(0, 'utf8').trim();
  if (!text && !files.length) { console.error('nothing to post: empty text and no files'); process.exit(2); }
  try {
    const ts = await post({ token, channel, thread: thread === '-' ? '' : thread, text, files });
    console.log(`OK ts=${ts}`);
  } catch (e) {
    if (!(e instanceof Fail)) throw e;
    console.error(e.message);
    process.exit(e.code);
  }
}

async function selfTest() {
  const assert = require('assert');
  const http = require('http');
  const os = require('os');
  const calls = [];
  const srv = http.createServer((req, res) => {
    let b = ''; req.on('data', (d) => (b += d)); req.on('end', () => {
      const m = req.url.slice(1);
      calls.push({ m, b });
      res.setHeader('Content-Type', 'application/json');
      if (m === 'upload') return res.end('OK');
      const out = {
        'chat.postMessage': { ok: true, ts: '1.000001' },
        'files.getUploadURLExternal': { ok: true, file_id: 'F1', upload_url: `http://127.0.0.1:${srv.address().port}/upload` },
        'files.completeUploadExternal': { ok: true, files: [{ id: 'F1', shares: { public: { C1: [{ ts: '2.000002' }] } } }] },
      }[m] ?? { ok: false, error: 'unknown_method' };
      res.end(JSON.stringify(out));
    });
  });
  await new Promise((r) => srv.listen(0, '127.0.0.1', r));
  const api = `http://127.0.0.1:${srv.address().port}`;
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'post-slack-'));
  const png = path.join(dir, 'shot.png'); fs.writeFileSync(png, 'pngbytes');
  const env = path.join(dir, '.env'); fs.writeFileSync(env, 'X=1');
  const sql = path.join(dir, 'prod_users.sql'); fs.writeFileSync(sql, 'x');
  const dump = path.join(dir, 'users.DUMP'); fs.writeFileSync(dump, 'x');
  const base = { api, token: 't', channel: 'C1', thread: '9.000009', text: 'hi' };

  assert.strictEqual(await post(base), '1.000001', 'text only -> chat.postMessage');
  assert.deepStrictEqual(calls.map((c) => c.m), ['chat.postMessage']);

  calls.length = 0;
  assert.strictEqual(await post({ ...base, files: [png] }), '2.000002', 'with file -> external upload, ts from shares');
  assert.deepStrictEqual(calls.map((c) => c.m), ['files.getUploadURLExternal', 'upload', 'files.completeUploadExternal']);
  const done = JSON.parse(calls[2].b);
  assert.strictEqual(done.initial_comment, 'hi'); assert.strictEqual(done.thread_ts, '9.000009'); assert.strictEqual(done.channel_id, 'C1');

  calls.length = 0;
  for (const bad of [env, sql, dump, path.join(dir, 'nope.png'), dir]) {
    await assert.rejects(post({ ...base, files: [png, bad] }), (e) => e.code === 5, `rejects ${path.basename(bad)}`);
  }
  assert.strictEqual(calls.length, 0, 'a bad file posts nothing, not even the good one');

  await assert.rejects(post({ ...base, api: api + '/x' }), (e) => e.code === 4, 'Slack error -> exit 4');
  srv.close(); fs.rmSync(dir, { recursive: true });
  console.log('self-test ok');
}

if (process.argv[2] === '--self-test') selfTest(); else main();

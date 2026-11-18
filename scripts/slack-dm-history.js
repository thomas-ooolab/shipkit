#!/usr/bin/env node
// slack-dm-history.js — read the recent history of the user's DM with one person, so a DM draft takes its voice from it.
//
//   usage: node slack-dm-history.js <name | U… id | email> [n=20]
//          node slack-dm-history.js --self-test
//
// Resolves the person (a U…/W… id as is; an email by users.lookupByEmail; a name by users.list, accents and word order ignored),
// finds the DM (conversations.list types=im, else conversations.open) and prints the last n messages, oldest first:
//   HISTORY channel=D… person=<name> (<U…>) messages=<k> from_me=<k>
//   <YYYY-MM-DD HH:MM> me|<name>: <text>
// Uses $SLACK_REVIEW_TOKEN (the user token, never printed). A DM draft is shown to the user only after this printed HISTORY
// in the same turn (references/humanize-text.md step 0). Take the form of address from the `me` lines.
//   exit 0  HISTORY printed
//   exit 2  bad usage
//   exit 3  $SLACK_REVIEW_TOKEN unset
//   exit 4  Slack rejected a call — `SLACK_ERROR: <error>`
//   exit 6  person not found — `NOT_FOUND: <who>`
//   exit 7  ambiguous — `AMBIGUOUS: <who>` then one `CANDIDATE <U…> <name>` per match; re-run with the id
//   exit 8  scope missing — `SCOPE_MISSING: <needed>` (users:read, users:read.email, im:read, im:history)
//   exit 9  no DM yet, or it holds no message — `NO_HISTORY: <why>`: nothing to take a voice from, ask the user how to address the person
// SLACK_API_BASE exists only so --self-test can point at a local mock.

'use strict';

const API = process.env.SLACK_API_BASE || 'https://slack.com/api';
class Fail extends Error { constructor(code, msg) { super(msg); this.code = code; } }

const call = async (api, token, method, params = {}) => {
  const res = await fetch(`${api}/${method}`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8' },
    body: new URLSearchParams(params),
  });
  const j = await res.json();
  if (j.ok) return j;
  if (j.error === 'missing_scope') throw new Fail(8, `SCOPE_MISSING: ${j.needed || 'see the app scopes'}`);
  throw new Fail(4, `SLACK_ERROR: ${j.error}`);
};

const norm = (s) => String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/đ/gi, 'd').toLowerCase().replace(/[^a-z0-9@. ]+/g, ' ').trim();
const names = (u) => [u.real_name, u.profile && u.profile.real_name, u.profile && u.profile.display_name, u.name].filter(Boolean);
const label = (u) => (u.profile && u.profile.real_name) || u.real_name || u.name;

async function resolve(api, token, who) {
  if (/^[UW][A-Z0-9]{6,}$/.test(who)) {
    const u = (await call(api, token, 'users.info', { user: who })).user;
    return { id: u.id, name: label(u) };
  }
  if (who.includes('@')) {
    try { const u = (await call(api, token, 'users.lookupByEmail', { email: who })).user; return { id: u.id, name: label(u) }; }
    catch (e) { if (e.message === 'SLACK_ERROR: users_not_found') throw new Fail(6, `NOT_FOUND: ${who}`); throw e; }
  }
  const want = norm(who).split(/\s+/).filter(Boolean);
  const exact = [], loose = [];
  let cursor = '';
  do {
    const r = await call(api, token, 'users.list', { limit: '200', ...(cursor ? { cursor } : {}) });
    for (const u of r.members || []) {
      if (u.deleted || u.is_bot) continue;
      const cands = names(u).map(norm);
      if (cands.some((c) => c === want.join(' '))) exact.push(u);
      else if (cands.some((c) => want.every((w) => c.split(/\s+/).includes(w)))) loose.push(u);
    }
    cursor = (r.response_metadata && r.response_metadata.next_cursor) || '';
  } while (cursor);
  const hit = exact.length ? exact : loose;
  if (!hit.length) throw new Fail(6, `NOT_FOUND: ${who}`);
  if (hit.length > 1) throw new Fail(7, `AMBIGUOUS: ${who}\n${hit.map((u) => `CANDIDATE ${u.id} ${label(u)}`).join('\n')}`);
  return { id: hit[0].id, name: label(hit[0]) };
}

async function findDm(api, token, userId) {
  try {
    let cursor = '';
    do {
      const r = await call(api, token, 'conversations.list', { types: 'im', limit: '200', ...(cursor ? { cursor } : {}) });
      const d = (r.channels || []).find((c) => c.user === userId);
      if (d) return d.id;
      cursor = (r.response_metadata && r.response_metadata.next_cursor) || '';
    } while (cursor);
    throw new Fail(9, 'NO_HISTORY: there is no DM with this person yet');
  } catch (e) {
    if (e.code !== 8) throw e;  // no im:read: conversations.open returns the existing DM's id
    return (await call(api, token, 'conversations.open', { users: userId })).channel.id;
  }
}

const when = (ts) => new Date(Number(ts) * 1000).toLocaleString('sv-SE').slice(0, 16);

async function run(who, n, token, api = API) {
  const p = await resolve(api, token, who);
  const channel = await findDm(api, token, p.id);
  const me = (await call(api, token, 'auth.test')).user_id;
  const msgs = ((await call(api, token, 'conversations.history', { channel, limit: String(n) })).messages || []).filter((m) => m.text).reverse();
  if (!msgs.length) throw new Fail(9, `NO_HISTORY: the DM ${channel} holds no message`);
  const out = [`HISTORY channel=${channel} person=${p.name} (${p.id}) messages=${msgs.length} from_me=${msgs.filter((m) => m.user === me).length}`];
  for (const m of msgs) out.push(`${when(m.ts)} ${m.user === me ? 'me' : p.name}: ${m.text.replace(/\n/g, '\n    ')}`);
  return out.join('\n');
}

async function main() {
  const [who, nArg] = process.argv.slice(2);
  const n = Number(nArg || 20);
  if (!who || !Number.isInteger(n) || n < 1 || n > 200) { console.error('usage: slack-dm-history.js <name | U… id | email> [n=20, 1..200]'); process.exit(2); }
  const token = process.env.SLACK_REVIEW_TOKEN;
  if (!token) { console.error('SLACK_REVIEW_TOKEN is not set — export the user token (xoxp-…, scopes users:read, im:read, im:history).'); process.exit(3); }
  try { console.log(await run(who, n, token)); } catch (e) { if (!(e instanceof Fail)) throw e; console.error(e.message); process.exit(e.code); }
}

async function selfTest() {
  const assert = require('assert');
  const http = require('http');
  const users = [
    { id: 'U0000001', name: 'thang.nguyen', real_name: 'Nguyễn Văn Thắng', profile: { display_name: 'Thang' } },
    { id: 'U0000002', name: 'lan', real_name: 'Trần Thị Lan' },
    { id: 'U0000003', name: 'minh.a', real_name: 'Lê Minh' },
    { id: 'U0000004', name: 'minh.b', real_name: 'Phạm Minh' },
    { id: 'U0000005', name: 'nodm', real_name: 'Chưa Nhắn' },
    { id: 'U0000006', name: 'empty', real_name: 'Rỗng' },
    { id: 'U0000007', name: 'old', real_name: 'Cũ Nghỉ', deleted: true },
  ];
  let mode = 'ok';
  const calls = [];
  const srv = http.createServer((req, res) => {
    let b = ''; req.on('data', (d) => (b += d)); req.on('end', () => {
      const m = req.url.slice(1), q = Object.fromEntries(new URLSearchParams(b));
      calls.push({ m, q, auth: req.headers.authorization });
      res.setHeader('Content-Type', 'application/json');
      const out = (o) => res.end(JSON.stringify(o));
      if (mode === 'noscope' && m === 'users.list') return out({ ok: false, error: 'missing_scope', needed: 'users:read' });
      if (m === 'users.list') return out(q.cursor ? { ok: true, members: users.slice(4), response_metadata: {} } : { ok: true, members: users.slice(0, 4), response_metadata: { next_cursor: 'c2' } });
      if (m === 'users.info') return out({ ok: true, user: users.find((u) => u.id === q.user) });
      if (m === 'users.lookupByEmail') return q.email === 'thang@x.vn' ? out({ ok: true, user: users[0] }) : out({ ok: false, error: 'users_not_found' });
      if (m === 'auth.test') return out({ ok: true, user_id: 'UME' });
      if (m === 'conversations.list') {
        if (mode === 'noim') return out({ ok: false, error: 'missing_scope', needed: 'im:read' });
        return out({ ok: true, channels: [{ id: 'D1', user: 'U0000001' }, { id: 'D6', user: 'U0000006' }], response_metadata: {} });
      }
      if (m === 'conversations.open') return out({ ok: true, channel: { id: 'D1' } });
      if (m === 'conversations.history') {
        if (q.channel === 'D6') return out({ ok: true, messages: [] });
        return out({ ok: true, messages: [{ user: 'U0000001', ts: '1700000300', text: 'ok anh nhé' }, { user: 'UME', ts: '1700000200', text: 'em gửi anh\nbản mới' }, { user: 'UME', ts: '1700000100', text: 'chào anh Thắng' }] });
      }
      out({ ok: false, error: 'unknown_method' });
    });
  });
  await new Promise((r) => srv.listen(0, '127.0.0.1', r));
  const api = `http://127.0.0.1:${srv.address().port}`;
  const fails = async (p, code, re) => { try { await p; } catch (e) { assert(e instanceof Fail && e.code === code && re.test(e.message), `${e.code} ${e.message}`); return; } assert.fail(`expected exit ${code}`); };
  const out = await run('Thang Nguyen', 5, 'tok', api);                     // accents and word order ignored; paginated list
  assert(out.startsWith('HISTORY channel=D1 person=Nguyễn Văn Thắng (U0000001) messages=3 from_me=2'), out);
  assert(out.indexOf('chào anh Thắng') < out.indexOf('ok anh nhé') && /me: em gửi anh\n {4}bản mới/.test(out), out);   // oldest first, `me` vs the person
  assert(calls.every((c) => c.auth === 'Bearer tok') && !out.includes('tok'));
  assert((await run('U0000001', 5, 'tok', api)).includes('(U0000001)') && (await run('thang@x.vn', 5, 'tok', api)).includes('(U0000001)'));
  assert((await run('thang', 5, 'tok', api)).includes('(U0000001)'));                // the display name alone
  await fails(run('Minh', 5, 'tok', api), 7, /AMBIGUOUS: Minh\nCANDIDATE U0000003 Lê Minh\nCANDIDATE U0000004 Phạm Minh/);
  await fails(run('Nobody Here', 5, 'tok', api), 6, /NOT_FOUND: Nobody Here/);
  await fails(run('nobody@x.vn', 5, 'tok', api), 6, /NOT_FOUND/);
  await fails(run('Cũ Nghỉ', 5, 'tok', api), 6, /NOT_FOUND/);               // a deactivated account is not a DM partner
  await fails(run('Chưa Nhắn', 5, 'tok', api), 9, /NO_HISTORY: there is no DM/);
  await fails(run('Rỗng', 5, 'tok', api), 9, /NO_HISTORY: the DM D6 holds no message/);
  mode = 'noim'; assert((await run('Thang', 5, 'tok', api)).includes('channel=D1'));   // no im:read → conversations.open
  mode = 'noscope'; await fails(run('Thang', 5, 'tok', api), 8, /SCOPE_MISSING: users:read/);
  srv.close();
  console.log('self-test ok');
}

if (process.argv[2] === '--self-test') selfTest(); else main();

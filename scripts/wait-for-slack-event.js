#!/usr/bin/env node
// wait-for-slack-event.js — push twin of wait-for-slack-reply.sh: block until someone OTHER than me
// posts in ONE Slack thread, learning about it from a Socket Mode event instead of polling.
//
//   usage: node wait-for-slack-event.js <channel_id> <thread_ts> <after_ts> <my_user_id> [max_minutes]
//          node wait-for-slack-event.js --self-test
//
// Same contract as wait-for-slack-reply.sh, so the caller treats both alike. <thread_ts> is the ROOT.
//   exit 0  new message from someone else — prints `NEW 1 latest_ts=<ts> author=<user>`; the CALLER
//           reads the thread (conversations.replies) and decides what to answer.
//   exit 2  nothing new within <max_minutes> (default 60) — relaunch; not a failure.
//   exit 3  $SLACK_APP_TOKEN (xapp-…, connections:write) or $SLACK_REVIEW_TOKEN unset.
//   exit 4  Slack rejected a call (bad token/scope, thread not found, not in channel).
//   exit 6  <thread_ts> is a REPLY, not the root — re-run with the root ts printed in the error.
//
// Needs Node >= 22 (global WebSocket). Events arrive "on behalf of the user" (user-scope
// message.channels/groups/im/mpim), so every channel the user is in is covered without inviting a bot.
// Slack allows ~10 concurrent socket connections per app: one process per watched thread fits that.
// Never prints either token or the wss URL (it embeds a one-time ticket).
// SLACK_API_BASE exists only so a self-check can point at a local mock.

'use strict';

const API = process.env.SLACK_API_BASE || 'https://slack.com/api';
const OK_SUBTYPES = [undefined, 'thread_broadcast', 'file_share', 'bot_message'];

// Slack ts "1759650000.123456" -> integer microseconds (a double can't hold all 16 digits safely).
const micros = (ts) => { const [s, u = ''] = String(ts).split('.'); return BigInt(s) * 1000000n + BigInt(u.padEnd(6, '0')); };

// Is `ev` a new reply from someone else in the watched thread? Pure, so --self-test can pin it.
function isNew(ev, { channel, root, me, after }) {
  if (!ev || ev.type !== 'message' || !OK_SUBTYPES.includes(ev.subtype)) return false;
  if (ev.channel !== channel || ev.thread_ts !== root || ev.ts === root) return false;
  if (ev.user === me) return false;
  return micros(ev.ts) > micros(after);
}

// One Socket Mode envelope -> what to do. Every envelope with an id must be acked or Slack redelivers.
function handle(env, ctx) {
  const ack = env.envelope_id ? { envelope_id: env.envelope_id } : null;
  if (env.type === 'hello') return { ack, catchUp: true };
  if (env.type === 'disconnect') return { ack, reconnect: true };
  if (env.type === 'events_api') return { ack, hit: isNew(env.payload && env.payload.event, ctx) ? env.payload.event : null };
  return { ack };
}

// Replies that landed before the socket was up (or during a reconnect) never produce an event.
async function catchUp(ctx) {
  try {
    const q = new URLSearchParams({ channel: ctx.channel, ts: ctx.root, limit: '200' });
    const r = await (await fetch(`${API}/conversations.replies?${q}`, {
      headers: { Authorization: `Bearer ${process.env.SLACK_REVIEW_TOKEN}` }, signal: AbortSignal.timeout(20000),
    })).json();
    if (!r.ok) return { error: r.error };
    const m = r.messages || [];
    if (m[0] && (m[0].thread_ts || m[0].ts) !== m[0].ts) return { notRoot: m[0].thread_ts };
    const fresh = m.slice(1).filter((x) => micros(x.ts) > micros(ctx.after) && x.user !== ctx.me);
    return { hit: fresh.length ? fresh[fresh.length - 1] : null };
  } catch { return {}; } // one transient network failure must never end the wait
}

const finish = (code, msg) => { if (msg) (code === 0 ? console.log : console.error)(msg); process.exit(code); };
const found = (ev) => finish(0, `NEW 1 latest_ts=${ev.ts} author=${ev.user || '?'}`);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// One socket lifetime; resolves when it closes so the caller can reconnect.
async function session(ctx) {
  let open;
  try {
    open = await (await fetch(`${API}/apps.connections.open`, {
      method: 'POST', headers: { Authorization: `Bearer ${process.env.SLACK_APP_TOKEN}` }, signal: AbortSignal.timeout(20000),
    })).json();
  } catch { return; }
  if (!open.ok) finish(4, `SLACK_ERROR: ${open.error} (invalid_auth / not_allowed_token_type = SLACK_APP_TOKEN must be an app-level xapp- token with connections:write; Socket Mode must be on).`);

  await new Promise((resolve) => {
    const ws = new WebSocket(open.url);
    ws.onclose = ws.onerror = () => resolve();
    ws.onmessage = async (e) => {
      let env; try { env = JSON.parse(e.data); } catch { return; }
      const act = handle(env, ctx);
      if (act.ack) ws.send(JSON.stringify(act.ack));
      if (act.hit) found(act.hit);
      if (act.reconnect) ws.close();
      if (act.catchUp) {
        const c = await catchUp(ctx);
        if (c.error) finish(4, `SLACK_ERROR: ${c.error} (thread_not_found = wrong channel/ts; not_in_channel, missing_scope, invalid_auth = token/access).`);
        if (c.notRoot) finish(6, `WRONG_TS: ${ctx.root} is a reply, not the thread root. Re-run with root ts ${c.notRoot}.`);
        if (c.hit) found(c.hit);
      }
    };
  });
}

async function main() {
  const [channel, root, after, me, maxMin = '60'] = process.argv.slice(2);
  if (!channel || !root || !after || !me) finish(4, 'usage: node wait-for-slack-event.js <channel_id> <thread_ts> <after_ts> <my_user_id> [max_minutes]');
  if (!process.env.SLACK_APP_TOKEN || !process.env.SLACK_REVIEW_TOKEN) {
    finish(3, 'NO_TOKEN: export SLACK_APP_TOKEN (app-level xapp- token, Socket Mode) and SLACK_REVIEW_TOKEN (the user token).');
  }
  const ctx = { channel, root, after, me };
  const deadline = Date.now() + Number(maxMin) * 60000;
  setTimeout(() => finish(2, `TIMEOUT after ${maxMin}m: nothing new from anyone else.`), Number(maxMin) * 60000);
  while (Date.now() < deadline) { await session(ctx); await sleep(2000); } // ponytail: fixed 2s backoff, add jitter if many watchers reconnect at once
}

function selfTest() {
  const assert = require('node:assert/strict');
  const ctx = { channel: 'C1', root: '100.000001', me: 'UME', after: '100.000001' };
  const ev = (o) => ({ type: 'message', channel: 'C1', thread_ts: '100.000001', ts: '100.000002', user: 'UOTHER', ...o });
  assert.ok(isNew(ev(), ctx), 'reply from someone else');
  assert.ok(isNew(ev({ user: undefined, subtype: 'bot_message' }), ctx), 'bot reply counts, like the poll script');
  assert.ok(!isNew(ev({ user: 'UME' }), ctx), 'my own reply');
  assert.ok(!isNew(ev({ channel: 'C2' }), ctx), 'other channel');
  assert.ok(!isNew(ev({ thread_ts: '999.000001' }), ctx), 'other thread');
  assert.ok(!isNew(ev({ thread_ts: undefined }), ctx), 'top-level channel post');
  assert.ok(!isNew(ev({ ts: '100.000001' }), ctx), 'the root itself');
  assert.ok(!isNew(ev({ subtype: 'message_changed' }), ctx), 'edit event');
  assert.ok(!isNew(ev({ ts: '100.000002' }), { ...ctx, after: '100.000002' }), 'already handled (equal ts)');
  assert.ok(isNew(ev({ ts: '1759650000.123457' }), { ...ctx, after: '1759650000.123456' }), '16-digit ts ordering');
  assert.deepEqual(handle({ type: 'hello' }, ctx), { ack: null, catchUp: true });
  assert.deepEqual(handle({ type: 'disconnect', envelope_id: 'e0' }, ctx), { ack: { envelope_id: 'e0' }, reconnect: true });
  assert.equal(handle({ type: 'events_api', envelope_id: 'e1', payload: { event: ev() } }, ctx).hit.ts, '100.000002');
  assert.equal(handle({ type: 'events_api', envelope_id: 'e2', payload: { event: ev({ user: 'UME' }) } }, ctx).hit, null);
  assert.deepEqual(handle({ type: 'slash_commands', envelope_id: 'e3' }, ctx), { ack: { envelope_id: 'e3' } });
  console.log('self-test ok');
}

if (process.argv[2] === '--self-test') selfTest(); else main();

#!/usr/bin/env node
// observe-slack.js — stream the user's Slack notifications, one stdout line each, until killed.
// For `/developer` without a URL: run it under the Monitor tool; each line is one thing to look at.
//
//   usage: node observe-slack.js            (needs SLACK_APP_TOKEN + SLACK_REVIEW_TOKEN)
//          node observe-slack.js --self-test
//
// Line format (ids only — message text is untrusted, the caller reads it through the Slack API):
//   EVENT <dm|mention|thread> channel=<C…> ts=<ts> thread_ts=<root ts|-> user=<U…|?>
//     dm       a DM / group DM to me
//     mention  a message that @mentions me
//     thread   a reply in a thread I started or already posted in
// Own messages are never reported (they only mark a thread as "joined"). One line per message.
// Events come from Slack Socket Mode, subscribed on behalf of the user, so every channel the user is
// in is covered. Needs Node >= 22 (global WebSocket). Never prints a token or the wss URL.
// Not replayed: messages posted while the socket was down (reconnects take ~2s; Slack drops the rest).
// SLACK_API_BASE exists only so a self-check can point at a local mock.

'use strict';

const API = process.env.SLACK_API_BASE || 'https://slack.com/api';
const OK_SUBTYPES = [undefined, 'thread_broadcast', 'file_share', 'bot_message'];
const key = (c, t) => `${c}:${t}`;

// -> 'dm' | 'mention' | 'thread' | 'check' (thread reply, participation unknown) | 'own' | null. Pure.
function classify(ev, me, mine) {
  if (!ev || ev.type !== 'message' || !OK_SUBTYPES.includes(ev.subtype)) return null;
  if (ev.user === me) return 'own';
  if (ev.channel_type === 'im' || ev.channel_type === 'mpim') return 'dm';
  if (typeof ev.text === 'string' && ev.text.includes(`<@${me}>`)) return 'mention';
  if (ev.thread_ts && ev.thread_ts !== ev.ts) {
    return ev.parent_user_id === me || mine.has(key(ev.channel, ev.thread_ts)) ? 'thread' : 'check';
  }
  return null;
}

const line = (kind, ev) => `EVENT ${kind} channel=${ev.channel} ts=${ev.ts} thread_ts=${ev.thread_ts && ev.thread_ts !== ev.ts ? ev.thread_ts : '-'} user=${ev.user || '?'}`;

async function slack(method, token, params) {
  const r = await fetch(`${API}/${method}${params ? `?${new URLSearchParams(params)}` : ''}`, {
    method: params ? 'GET' : 'POST', headers: { Authorization: `Bearer ${token}` }, signal: AbortSignal.timeout(20000),
  });
  return r.json();
}

async function main() {
  const { SLACK_APP_TOKEN: app, SLACK_REVIEW_TOKEN: user } = process.env;
  if (!app || !user) { console.error('NO_TOKEN: export SLACK_APP_TOKEN (xapp-, Socket Mode) and SLACK_REVIEW_TOKEN (the user token).'); process.exit(3); }
  const who = await slack('auth.test', user, {}).catch(() => ({}));
  if (!who.ok) { console.error(`SLACK_ERROR: auth.test ${who.error || 'failed'} (SLACK_REVIEW_TOKEN invalid?)`); process.exit(4); }
  const me = who.user_id;
  const mine = new Set();     // "channel:root" of threads I started or posted in
  const notMine = new Set();  // threads already looked up and found without me (saves API calls)
  const seen = new Set();     // channel:ts already reported — Slack redelivers, one message can match twice

  async function onEvent(ev) {
    let kind = classify(ev, me, mine);
    if (kind === 'own') { if (ev.thread_ts) mine.add(key(ev.channel, ev.thread_ts)); return; }
    if (kind === 'check') {
      const k = key(ev.channel, ev.thread_ts);
      if (notMine.has(k)) return;
      try {
        const r = await slack('conversations.replies', user, { channel: ev.channel, ts: ev.thread_ts, limit: '200' });
        if (r.ok && (r.messages || []).some((m) => m.user === me)) { mine.add(k); kind = 'thread'; }
        else if (r.ok) { notMine.add(k); return; }
        else return;
      } catch { return; }
    }
    if (!kind || kind === 'check') return;
    const id = key(ev.channel, ev.ts);
    if (seen.has(id)) return;
    seen.add(id); if (seen.size > 2000) seen.delete(seen.values().next().value);
    console.log(line(kind, ev));
  }

  for (;;) { // one iteration = one socket lifetime
    const open = await slack('apps.connections.open', app).catch(() => ({ retry: true }));
    if (!open.ok && !open.retry) { console.error(`SLACK_ERROR: ${open.error} (SLACK_APP_TOKEN must be an app-level xapp- token with connections:write; Socket Mode on).`); process.exit(4); }
    if (open.ok) {
      await new Promise((resolve) => {
        const ws = new WebSocket(open.url);
        ws.onclose = ws.onerror = () => resolve();
        ws.onmessage = (e) => {
          let env; try { env = JSON.parse(e.data); } catch { return; }
          if (env.envelope_id) ws.send(JSON.stringify({ envelope_id: env.envelope_id })); // unacked → redelivered
          if (env.type === 'disconnect') ws.close();
          else if (env.type === 'events_api') onEvent(env.payload && env.payload.event);
        };
      });
    }
    await new Promise((r) => setTimeout(r, 2000)); // ponytail: fixed backoff, add jitter if it ever flaps
  }
}

function selfTest() {
  const assert = require('node:assert/strict');
  const me = 'UME';
  const mine = new Set([key('C1', '50.000001')]);
  const ev = (o) => ({ type: 'message', channel: 'C1', ts: '100.000002', user: 'UOTHER', text: 'hi', ...o });
  assert.equal(classify(ev({ channel_type: 'im' }), me, mine), 'dm');
  assert.equal(classify(ev({ channel_type: 'mpim' }), me, mine), 'dm');
  assert.equal(classify(ev({ text: 'hey <@UME> got a sec?' }), me, mine), 'mention');
  assert.equal(classify(ev({ text: 'hey <@UMEOTHER>' }), me, mine), null, 'someone else with a similar id');
  assert.equal(classify(ev({ channel_type: 'im', text: '<@UME>' }), me, mine), 'dm', 'dm wins over mention');
  assert.equal(classify(ev({ thread_ts: '50.000001' }), me, mine), 'thread', 'thread I posted in');
  assert.equal(classify(ev({ thread_ts: '60.000001', parent_user_id: 'UME' }), me, mine), 'thread', 'thread I started');
  assert.equal(classify(ev({ thread_ts: '60.000001' }), me, mine), 'check', 'unknown thread -> look up');
  assert.equal(classify(ev({ thread_ts: '100.000002' }), me, mine), null, 'the root itself is not a reply');
  assert.equal(classify(ev(), me, mine), null, 'plain channel chatter');
  assert.equal(classify(ev({ user: 'UME', thread_ts: '60.000001' }), me, mine), 'own');
  assert.equal(classify(ev({ subtype: 'message_changed' }), me, mine), null, 'edits');
  assert.equal(classify(ev({ user: undefined, subtype: 'bot_message', channel_type: 'im' }), me, mine), 'dm', 'bots count');
  assert.equal(line('mention', ev({ channel_type: undefined })), 'EVENT mention channel=C1 ts=100.000002 thread_ts=- user=UOTHER');
  assert.equal(line('thread', ev({ thread_ts: '50.000001', user: undefined })), 'EVENT thread channel=C1 ts=100.000002 thread_ts=50.000001 user=?');
  assert.ok(!line('dm', ev({ text: 'SECRET' })).includes('SECRET'), 'text never leaves the script');
  console.log('self-test ok');
}

if (process.argv[2] === '--self-test') selfTest(); else main();

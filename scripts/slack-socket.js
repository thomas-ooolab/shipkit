// slack-socket.js — the Socket Mode plumbing shared by wait-for-slack-event.js and skills/developer/observe-slack.js.
// Needs Node >= 22 (global WebSocket). Never logs the app token or the wss URL (it embeds a one-time ticket).
'use strict';

// Message subtypes that count as a real post (everything else — edits, joins, deletes — is noise).
const OK_SUBTYPES = [undefined, 'thread_broadcast', 'file_share', 'bot_message'];

// One socket lifetime. Opens the connection with the app-level token and hands every envelope to
// onEnvelope(env, ws) — acking (`ws.send({envelope_id})`) and closing on `disconnect` are the caller's job,
// because the two callers react differently. Resolves when the socket closes:
//   {}              closed normally (the caller sleeps and calls again)
//   {retry: true}   apps.connections.open failed on the network — transient
//   {error: '...'}  Slack rejected the app token (invalid_auth, not_allowed_token_type) — not transient
async function session({ api, appToken, onEnvelope }) {
  let open;
  try {
    open = await (await fetch(`${api}/apps.connections.open`, {
      method: 'POST', headers: { Authorization: `Bearer ${appToken}` }, signal: AbortSignal.timeout(20000),
    })).json();
  } catch { return { retry: true }; }
  if (!open.ok) return { error: open.error };
  await new Promise((resolve) => {
    const ws = new WebSocket(open.url);
    ws.onclose = ws.onerror = () => resolve();
    ws.onmessage = (e) => {
      let env; try { env = JSON.parse(e.data); } catch { return; }
      onEnvelope(env, ws);
    };
  });
  return {};
}

const ack = (ws, env) => { if (env.envelope_id) ws.send(JSON.stringify({ envelope_id: env.envelope_id })); };

module.exports = { OK_SUBTYPES, session, ack };

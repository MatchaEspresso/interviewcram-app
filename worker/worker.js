// InterviewCram chat proxy (Cloudflare Worker).
// The app POSTs {context, messages} to /api/chat with `Authorization: Bearer <access code>`.
// This adds the tutor prompt and forwards to OpenRouter, so the API key never reaches the browser.
// Secrets (wrangler secret put): OPENROUTER_API_KEY, APP_TOKEN. Vars in wrangler.toml: MODELS, ALLOWED_ORIGINS.

const SYSTEM = `You are a friendly, sharp coding-interview tutor inside InterviewCram, a phone app for drilling LeetCode patterns and Python syntax. The learner is prepping for SWE/MLE intern interviews and is asking about the flashcard shown in <card>.

- Keep answers short: they're reading on a phone. Usually 2-6 sentences; use a small code block only when it helps. No headings.
- If the card says the learner has NOT answered yet, help them understand the question (terms, what's being asked, a nudge) but do not reveal or strongly hint at the correct option unless they explicitly ask for the answer.
- If they have answered, explain why the right answer is right and, if they picked wrong, what was off about their choice.
- Python 3 for all code. Use \`backticks\` for inline code and \`\`\` fences for blocks.
- If the card itself seems wrong, say so plainly.
- Only help with the card, coding interviews and programming. Politely decline anything else.`;

const MAX_BODY = 48_000;
const MAX_TURNS = 24;
const OPENROUTER = 'https://openrouter.ai/api/v1/chat/completions';
const OPENROUTER_MODELS = 'https://openrouter.ai/api/v1/models';

// Constant-time compare so the access code can't be guessed from response timing.
function sameToken(a, b) {
  if (typeof a !== 'string' || typeof b !== 'string' || a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

function corsHeaders(request, env) {
  const origin = request.headers.get('Origin') || '';
  const allowed = String(env.ALLOWED_ORIGINS || '').split(',').map((s) => s.trim()).filter(Boolean);
  return {
    'Access-Control-Allow-Origin': allowed.includes(origin) ? origin : allowed[0] || '',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    'Access-Control-Max-Age': '86400',
    Vary: 'Origin',
  };
}

// OpenRouter's public model list, fetched once per Worker instance. A configured ID that isn't listed
// (renamed or retired) is dropped, so one stale ID doesn't fail every request.
let catalog = null;
async function availableModels(wanted) {
  if (!catalog) {
    catalog = fetch(OPENROUTER_MODELS)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`models ${r.status}`))))
      .then((d) => new Set((d.data || []).map((m) => m.id)))
      .catch((e) => { catalog = null; console.warn('Could not load the OpenRouter model list:', e.message); return null; });
  }
  const known = await catalog;
  if (!known) return wanted;
  const missing = wanted.filter((id) => !known.has(id));
  if (missing.length) console.warn('Not on OpenRouter, skipped:', missing.join(', '));
  return wanted.filter((id) => known.has(id));
}

async function askModel(env, context, messages) {
  const wanted = String(env.MODELS || '').split(',').map((s) => s.trim()).filter(Boolean);
  const models = (await availableModels(wanted)).slice(0, 3); // OpenRouter's fallback list takes a few models, not many
  if (!models.length) throw Object.assign(new Error('None of the models in MODELS exist on OpenRouter. Update MODELS in wrangler.toml.'), { status: 500 });
  const body = {
    messages: [{ role: 'system', content: `${SYSTEM}\n\n<card>\n${context}\n</card>` }, ...messages],
    max_tokens: 900,
    temperature: 0.3,
  };
  if (models.length > 1) body.models = models; // OpenRouter tries them in order
  else body.model = models[0];
  const res = await fetch(OPENROUTER, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${env.OPENROUTER_API_KEY}`,
      'Content-Type': 'application/json',
      'HTTP-Referer': 'https://matchaespresso.github.io/interviewcram-app/',
      'X-Title': 'InterviewCram',
    },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (res.status === 429) throw Object.assign(new Error('The model’s rate limit is used up for now. Try again in a bit.'), { status: 429 });
  if (res.status === 401 || res.status === 403) throw Object.assign(new Error('OpenRouter rejected the Worker’s API key.'), { status: 502 });
  if (res.status === 402) throw Object.assign(new Error('OpenRouter account is out of credits.'), { status: 502 });
  if (!res.ok) throw Object.assign(new Error((data.error && data.error.message) || `OpenRouter error ${res.status}.`), { status: 502 });
  const reply = data.choices && data.choices[0] && data.choices[0].message && data.choices[0].message.content;
  if (!reply || !String(reply).trim()) throw Object.assign(new Error('The model returned an empty answer. Try again.'), { status: 502 });
  return String(reply).trim();
}

export default {
  async fetch(request, env) {
    const cors = corsHeaders(request, env);
    const json = (status, obj) => new Response(JSON.stringify(obj), {
      status, headers: { ...cors, 'Content-Type': 'application/json', 'Cache-Control': 'no-store' },
    });
    const { pathname } = new URL(request.url);

    if (request.method === 'OPTIONS') return new Response(null, { status: 204, headers: cors });
    if (pathname === '/api/health' && request.method === 'GET') return json(200, { ok: true });
    if (pathname !== '/api/chat' || request.method !== 'POST') return json(404, { error: 'Not found.' });
    if (!env.OPENROUTER_API_KEY || !env.APP_TOKEN) return json(500, { error: 'The Worker is missing its OPENROUTER_API_KEY or APP_TOKEN secret.' });

    const token = (request.headers.get('Authorization') || '').replace(/^Bearer\s+/i, '');
    if (!sameToken(token, env.APP_TOKEN)) return json(401, { error: 'Wrong or missing access code.' });

    let context, messages;
    try {
      const raw = await request.text();
      if (!raw || raw.length > MAX_BODY) return json(413, { error: 'Message too long.' });
      const data = JSON.parse(raw);
      context = String(data.context || '').slice(0, 12_000);
      messages = (Array.isArray(data.messages) ? data.messages : []).slice(-MAX_TURNS).map((m) => ({
        role: m && m.role === 'user' ? 'user' : 'assistant',
        content: String((m && m.content) || '').slice(0, 4_000),
      }));
    } catch (e) {
      return json(400, { error: 'Bad request.' });
    }
    if (!messages.length || messages[messages.length - 1].role !== 'user' || !messages[messages.length - 1].content.trim()) {
      return json(400, { error: 'Empty question.' });
    }

    try {
      return json(200, { reply: await askModel(env, context, messages) });
    } catch (e) {
      return json(e.status || 502, { error: e.message || 'Chat failed.' });
    }
  },
};

# InterviewCram

Duolingo-style, phone-first web app for drilling LeetCode patterns and Python syntax ahead of SWE/MLE intern coding interviews.

## Current state
- The app is a single file: `index.html` (markup, CSS, JS and content inline, no build step). Around it: `manifest.webmanifest`, `sw.js` (offline cache), `icons/`, and `worker/` (Cloudflare Worker for chat).
- Originally built as a Claude artifact, exported here to keep developing in Claude Code.
- Progress (streaks, completed lessons, review queue) is saved in the browser's `localStorage`.
- Layout is a single centered phone column with safe-area insets, meant to be used on an iPhone (Safari → Share → Add to Home Screen).
- Topics: Binary Search, Sliding Window, Two Pointers, Hash Map & Counting, BFS / DFS on Grids, Python Toolkit. `comingSoon` lists the patterns with no content yet (shown as "Not written yet", not locked).
- "Ask Claude" chat panel on every activity card, hidden mid-question in timed challenges. It POSTs the card context to the Worker at `CHAT_URL` (top of the chat section in `index.html`) with an access code saved in `localStorage`. The Worker (`worker/worker.js`) holds the tutor prompt and the OpenRouter key and forwards to the models in `MODELS` (`worker/wrangler.toml`), limited to DeepSeek, GLM, Kimi and Qwen (the only ones the OpenRouter key allows); IDs not on OpenRouter are skipped at runtime.

## Running it
- Live at https://matchaespresso.github.io/interviewcram-app/ (GitHub Pages from `main`; a push redeploys in about a minute).
- Locally: `python3 -m http.server 8000`. Chat calls the deployed Worker, which only allows origins in `ALLOWED_ORIGINS`.
- Worker: from `worker/`, `npx wrangler deploy`. Secrets `OPENROUTER_API_KEY` and `APP_TOKEN` are set with `npx wrangler secret put` and never committed.

## Adding content
- Cards follow the existing shapes; `options[0]` is always the correct answer. Give code cards `tests` (asserts).
- Run `python3 tools/check_content.py index.html` after editing: it executes every card's code against its tests and fails if a wrong option also passes.

## Conventions
- Keep it dependency-free and mobile-first unless we deliberately decide to add a build step.
- Colors are CSS custom properties on `:root` with a dark-mode override; reuse them rather than hard-coding colors.
- When adding content (topics, lessons, problems), follow the existing data structures in the script.

## Ideas / next steps
- Split content (topics, lessons, problems) out of `index.html` into a separate data file.
- Add more problems and patterns aimed at upcoming interviews.

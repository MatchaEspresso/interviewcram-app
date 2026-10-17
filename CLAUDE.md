# InterviewCram

Duolingo-style, phone-first web app for drilling LeetCode patterns and Python syntax ahead of SWE/MLE intern coding interviews.

## Current state
- The app is a single file: `index.html` (markup, CSS, JS and content inline, no build step). Around it: `manifest.webmanifest`, `sw.js` (offline cache), `icons/`, and `server.py` (local server + chat).
- Originally built as a Claude artifact, exported here to keep developing in Claude Code.
- Progress (streaks, completed lessons, review queue) is saved in the browser's `localStorage`.
- Layout is a single centered phone column with safe-area insets, meant to be used on an iPhone (Safari → Share → Add to Home Screen).

- Topics: Binary Search, Sliding Window, Two Pointers, Hash Map & Counting, BFS / DFS on Grids, Python Toolkit. `comingSoon` lists the patterns with no content yet (shown as "Not written yet", not locked).
- "Ask Claude" chat panel on every activity card. It talks to `server.py`'s `/api/chat`, which runs `claude -p` with all tools disabled, using the Mac's Claude login. Hidden mid-question in timed challenges.

## Running it
- Full app with chat: `python3 server.py` (stdlib only), then open the printed `http://<mac-name>.local:8000` on the phone (same Wi-Fi). The server only serves the app files, not the repo.
- `PORT`, `CRAM_MODEL` (default `sonnet`) and `CRAM_CLAUDE` (command to run instead of `claude`, for testing) are env overrides.
- Also deployed without chat at https://matchaespresso.github.io/interviewcram-app/ (GitHub Pages from `main`); there the chat panel explains it needs the Mac server.
- Over plain `http://` to the Mac, the service worker doesn't register (iOS needs HTTPS), so that version is online-only.

## Adding content
- Cards follow the existing shapes; `options[0]` is always the correct answer. Give code cards `tests` (asserts).
- Run `python3 tools/check_content.py index.html` after editing: it executes every card's code against its tests and fails if a wrong option also passes.

## Conventions
- Keep it dependency-free and mobile-first unless we deliberately decide to add a build step.
- Colors are CSS custom properties on `:root` with a dark-mode override; reuse them rather than hard-coding colors.
- When adding content (topics, lessons, problems), follow the existing data structures in the script.

## Ideas / next steps
- Split content (topics, lessons, problems) out of `index.html` into a separate data file.
- Make it a real PWA (manifest + service worker) so it works offline from the home screen.
- Add more problems and patterns aimed at upcoming interviews.

# InterviewCram

Duolingo-style, phone-first web app for drilling LeetCode patterns and Python syntax ahead of SWE/MLE intern coding interviews.

## Current state
- Everything lives in a single file: `index.html` (markup, CSS and JS inline, no build step).
- Originally built as a Claude artifact, exported here to keep developing in Claude Code.
- Progress (streaks, completed lessons, review queue) is saved in the browser's `localStorage`.
- Layout is a single centered phone column with safe-area insets, meant to be used on an iPhone (Safari → Share → Add to Home Screen).

## Running it
- Open `index.html` directly in a browser, or serve it: `python3 -m http.server 8000` and visit http://localhost:8000.
- To test on an iPhone on the same Wi-Fi, visit http://<your-mac-ip>:8000.

## Conventions
- Keep it dependency-free and mobile-first unless we deliberately decide to add a build step.
- Colors are CSS custom properties on `:root` with a dark-mode override; reuse them rather than hard-coding colors.
- When adding content (topics, lessons, problems), follow the existing data structures in the script.

## Ideas / next steps
- Split content (topics, lessons, problems) out of `index.html` into a separate data file.
- Make it a real PWA (manifest + service worker) so it works offline from the home screen.
- Add more problems and patterns aimed at upcoming interviews.

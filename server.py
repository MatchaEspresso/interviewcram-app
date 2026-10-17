#!/usr/bin/env python3
"""Serve InterviewCram from this Mac and answer chat questions with the Claude CLI.

    python3 server.py            # then open the printed URL on your phone (same Wi-Fi)

Chat calls `claude -p` with every tool disabled, so it can only reply with text:
it cannot run commands or read files. It uses the Claude login of whoever runs
this script. Standard library only.
"""
import json
import os
import shlex
import socket
import subprocess
import sys
import tempfile
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.abspath(__file__))
PORT = int(os.environ.get("PORT", "8000"))
MODEL = os.environ.get("CRAM_MODEL", "sonnet")
# Override for testing, e.g. CRAM_CLAUDE="python3 fake_claude.py"
CLAUDE = shlex.split(os.environ.get("CRAM_CLAUDE", "claude"))
TIMEOUT = 120
MAX_BODY = 48_000
MAX_TURNS = 24

# Only the app itself is served, never the repo (.git, this script, notes).
PUBLIC = {"/index.html", "/manifest.webmanifest", "/sw.js"}
PUBLIC_DIRS = ("/icons/",)

SYSTEM = """You are a friendly, sharp coding-interview tutor inside InterviewCram, a phone app \
for drilling LeetCode patterns and Python syntax. The learner is prepping for SWE/MLE intern \
interviews and is asking about the flashcard shown in <card>.

- Keep answers short: they're reading on a phone. Usually 2-6 sentences; use a small code \
block only when it helps. No headings.
- If the card says the learner has NOT answered yet, help them understand the question \
(terms, what's being asked, a nudge) but do not reveal or strongly hint at the correct \
option unless they explicitly ask for the answer.
- If they have answered, explain why the right answer is right and, if they picked wrong, \
what was off about their choice.
- Python 3 for all code. Use `backticks` for inline code and ``` fences for blocks.
- If the card itself seems wrong, say so plainly."""

slots = threading.BoundedSemaphore(2)
WORKDIR = tempfile.mkdtemp(prefix="cram-chat-")  # empty cwd: no project files or CLAUDE.md


def ask_claude(context, messages):
    convo = []
    for m in messages[:-1]:
        who = "Learner" if m["role"] == "user" else "Tutor"
        convo.append(f"{who}: {m['content']}")
    prompt = f"<card>\n{context}\n</card>\n\n"
    if convo:
        prompt += "Conversation so far:\n" + "\n\n".join(convo) + "\n\n"
    prompt += f"Learner's new message: {messages[-1]['content']}\n\nReply as the tutor."
    cmd = CLAUDE + [
        "-p", "--model", MODEL, "--system-prompt", SYSTEM,
        "--tools", "", "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}',
        "--disable-slash-commands", "--no-session-persistence", "--output-format", "text",
    ]
    res = subprocess.run(cmd, input=prompt, capture_output=True, text=True, timeout=TIMEOUT, cwd=WORKDIR)
    out = res.stdout.strip()
    if res.returncode != 0 or not out:
        raise RuntimeError((res.stderr or out or f"claude exited {res.returncode}").strip()[:400])
    if out.startswith("Not logged in"):
        raise RuntimeError("The Claude CLI isn't logged in on this Mac. Run `claude` in Terminal and log in.")
    return out


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)

    def log_message(self, fmt, *args):
        if self.path.startswith("/api/"):
            sys.stderr.write("%s %s\n" % (self.address_string(), fmt % args))

    def send_json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def end_headers(self):
        if not self.path.startswith("/api/"):
            self.send_header("Cache-Control", "no-cache")  # always pick up edits
        super().end_headers()

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/api/health":
            return self.send_json(200, {"ok": True})
        if path == "/":
            self.path = "/index.html"
        elif path not in PUBLIC and not (path.startswith(PUBLIC_DIRS) and ".." not in path):
            return self.send_error(404)
        return super().do_GET()

    def do_HEAD(self):
        self.do_GET()

    def do_POST(self):
        if self.path != "/api/chat":
            return self.send_error(404)
        try:
            n = int(self.headers.get("Content-Length", 0))
            if n <= 0 or n > MAX_BODY:
                return self.send_json(413, {"error": "Message too long."})
            data = json.loads(self.rfile.read(n))
            context = str(data.get("context", ""))[:12_000]
            messages = [
                {"role": "user" if m.get("role") == "user" else "assistant", "content": str(m.get("content", ""))[:4_000]}
                for m in data.get("messages", [])
            ][-MAX_TURNS:]
            if not messages or messages[-1]["role"] != "user" or not messages[-1]["content"].strip():
                return self.send_json(400, {"error": "Empty question."})
        except (ValueError, AttributeError, TypeError):
            return self.send_json(400, {"error": "Bad request."})
        if not slots.acquire(timeout=30):
            return self.send_json(503, {"error": "Busy answering another question. Try again in a moment."})
        try:
            return self.send_json(200, {"reply": ask_claude(context, messages)})
        except subprocess.TimeoutExpired:
            return self.send_json(504, {"error": "Claude took too long to answer. Try again."})
        except FileNotFoundError:
            return self.send_json(500, {"error": "The `claude` command isn't installed on this Mac."})
        except RuntimeError as e:
            return self.send_json(502, {"error": str(e)})
        finally:
            slots.release()


def lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except OSError:
        return None
    finally:
        s.close()


if __name__ == "__main__":
    sys.stdout.reconfigure(line_buffering=True)
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    host = subprocess.run(["scutil", "--get", "LocalHostName"], capture_output=True, text=True).stdout.strip()
    print(f"InterviewCram running. On your phone (same Wi-Fi) open:")
    if host:
        print(f"  http://{host}.local:{PORT}   (keeps working if your IP changes)")
    if ip := lan_ip():
        print(f"  http://{ip}:{PORT}")
    print(f"On this Mac: http://localhost:{PORT}    Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass

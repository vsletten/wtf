#!/usr/bin/env python3
# wtf: tiny Python client for OpenAI Responses API, with a playful spinner
# Deps: stdlib only (urllib, json, threading)
#

import json, os, sys, time, threading, random
from urllib import request, error

# Spinner timing:
WTF_GLYPH_INTERVAL = 0.25   # seconds between glyph frames
WTF_PHRASE_INTERVAL = 1.0   # seconds between phrase changes

# Toggle color output:
WTF_ENABLE_COLOR = os.getenv("WTF_ENABLE_COLOR", True)

# Spinner colors: defaults keep it readable
WTF_GLYPH_COLOR = os.getenv("WTF_GLYPH_COLOR", "36")   # cyan
WTF_TEXT_COLOR  = os.getenv("WTF_TEXT_COLOR",  "97")   # bright white
WTF_RESET_COLOR = "\x1b[0m"

# Spinner color helpers:
def supports_color(stream) -> bool:
    return getattr(stream, "isatty", lambda: False)() \
           and os.getenv("TERM", "") != "dumb"

def fg(code: str) -> str:
    """Return an ANSI 'set foreground' sequence.
    `code` examples: '36' (cyan), '96' (bright cyan),
                     '38;5;208' (256-color orange), '38;2;255;165;0' (truecolor orange)."""
    return f"\x1b[{code}m"


INSTRUCTIONS = (
    "You should respond to the user's prompt in a helpful and respectful way. "
    "Your response will be displayed in a linux terminal, as the output of a command from the user. "
    "It should contain only ASCII character that will display properly in a standard Gnome terminal window. "
    "It should be as brief as possible, while still answering the question. "
    "However, the user can override this brevity stipulation by explicitly requesting a longer or more detailed "
    "response in their prompt, and you must respect such requests."
)

def die(msg, code=1):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)

if len(sys.argv) < 2:
    die(f"Usage: {os.path.basename(sys.argv[0])} \"your prompt here\"", 2)

api_key = os.getenv("OPENAI_API_KEY") or die("OPENAI_API_KEY is not set.")
model = os.getenv("WTF_LLM_MODEL", "gpt-4o")
aliases = {"4o": "gpt-4o", "4o-mini": "gpt-4o-mini", "4.1": "gpt-4.1"}
model = aliases.get(model.lower(), model)

base_url = (os.getenv("OPENAI_BASE_URL") or "https://api.openai.com").rstrip("/")
endpoint = f"{base_url}/v1/responses"
prompt = " ".join(sys.argv[1:])

# -------- spinner (stderr only, to keep stdout clean) ----------
def spinner(stop_event):
    if not sys.stderr.isatty() or stop_event.is_set():
        return
    
    color_term = supports_color(sys.stderr) and os.getenv("WTF_ENABLE_COLOR", True) is True
    glyph_color = fg(WTF_GLYPH_COLOR) if color_term else ""
    text_color = fg(WTF_TEXT_COLOR) if color_term else ""
    reset_color = WTF_RESET_COLOR if color_term else ""

    phrases = [
        "thinking...", "serving brainrot...", "loading vibes...",
        "cooking...", "chewing on this...", "spinning up neurons...",
        "summoning citations...", "buffering brilliance...",
        "optimizing takes...", "deep in the sauce...", "caffeinating ideas...",
        "low-latency daydreaming...", "min-maxing the answer...", "nerd sniping myself..."
    ]
    random.shuffle(phrases)
    glyphs = "|/-\\"
    glyph_i = 0
    phrase_i = 0
    last_phrase_change = time.monotonic()
    width = 78

    while not stop_event.is_set():
        # render current frame
        msg = f"{glyph_color}[{glyphs[glyph_i]}]{reset_color} {text_color}{phrases[phrase_i]}{reset_color}"
        sys.stderr.write("\r" + msg[:width].ljust(width))
        sys.stderr.flush()

        # advance glyph every WTF_GLYPH_INTERVAL
        if not stop_event.wait(WTF_GLYPH_INTERVAL):
            glyph_i = (glyph_i + 1) % len(glyphs)

            # advance phrase every WTF_PHRASE_INTERVAL
            now = time.monotonic()
            if now - last_phrase_change >= WTF_PHRASE_INTERVAL:
                phrase_i = (phrase_i + 1) % len(phrases)
                last_phrase_change = now

    # clear line on exit
    sys.stderr.write("\r" + " " * width + "\r")
    sys.stderr.flush()

def do_request(payload):
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(
        endpoint, data=data, method="POST",
        headers={"Authorization": f"Bearer {api_key}",
                 "Content-Type": "application/json",
                 "Accept": "application/json"}
    )
    try:
        with request.urlopen(req, timeout=60) as resp:
            status, body = resp.status, resp.read()
    except error.HTTPError as e:
        status, body = e.code, e.read()
    except Exception as e:
        die(f"Request failed: {e}")
    try:
        j = json.loads(body.decode("utf-8", errors="replace"))
    except Exception:
        die(f"Non-JSON response (HTTP {status}): {body[:1000]!r}")
    return status, j

def extract_text(rj):
    t = rj.get("output_text")
    if isinstance(t, str) and t:
        return t
    out = rj.get("output")
    if isinstance(out, list):
        parts = []
        for item in out:
            if item.get("type") == "message":
                for c in item.get("content", []):
                    if c.get("type") in ("output_text", "text"):
                        s = c.get("text")
                        if isinstance(s, str):
                            parts.append(s)
        if parts:
            return "".join(parts)
    ch = rj.get("choices")
    if isinstance(ch, list) and ch:
        msg = ch[0].get("message") or {}
        if isinstance(msg, dict) and isinstance(msg.get("content"), str):
            return msg["content"]
    return ""

def web_tool_unsupported(rj):
    err = rj.get("error")
    msg = (err.get("message") if isinstance(err, dict) else str(err or "")).lower()
    return ("web_search" in msg) and ("unsupported" in msg or "not supported" in msg or "tool" in msg)

# Build payloads per Responses API (instructions + plain-string input)
payload_with_web = {
    "model": model,
    "instructions": INSTRUCTIONS,   # acts like system prompt
    "input": prompt,                # simplest valid input shape
    "tools": [ { "type": "web_search" } ]  # may be rejected; we'll fall back
}
payload_no_web = {
    "model": model,
    "instructions": INSTRUCTIONS,
    "input": prompt
}

stop = threading.Event()
t = None
try:
    if sys.stderr.isatty():
        t = threading.Thread(target=spinner, args=(stop,), daemon=True)
        t.start()

    status, j = do_request(payload_with_web)
    if status != 200 and web_tool_unsupported(j):
        status, j = do_request(payload_no_web)
finally:
    stop.set()
    if t:
        t.join()

if status != 200:
    err = j.get("error") or j
    msg = err.get("message") if isinstance(err, dict) else err
    die(f"OpenAI API request failed (HTTP {status})\nDetails: {msg}")

text = extract_text(j)
if not text:
    die("No text content found in API response.\n" + json.dumps(j, indent=2)[:2000])

# Terminal-friendly ASCII only on stdout
print(text.encode("ascii", "ignore").decode("ascii"))

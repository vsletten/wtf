# wtf

Tiny, no-deps (stdlib-only) Python CLI for OpenAI’s **Responses API**.

- Sends your prompt with a lightweight **system `instructions`**.
- Attempts **web search** via the built-in tool; falls back cleanly if unsupported.
- Prints only the model’s text to **stdout**.
- Shows a playful **spinner** (e.g., “serving brainrot…”) on **stderr** while it thinks.
- No venv required. Single file.

## Quick start

```bash
# 1) Put the script somewhere on your PATH
mkdir -p ~/.local/bin # for example
cp wtf.py ~/.local/bin/wtf
chmod +x ~/.local/bin/wtf
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc  # or ~/.zshrc
exec $SHELL -l

# 2) Set your key
export OPENAI_API_KEY=sk-...

# 3) Use it
wtf "short: parquet on S3 vs ingesting into DuckDB?"
```

### macOS notes

- Works in Terminal/iTerm (zsh/bash).
- If `~/.local/bin` isn’t on PATH, add it in `~/.zshrc` or `~/.bash_profile`.

### Ubuntu notes

- Same as above. Uses the system’s `python3`.

### Windows options

- **Best:** WSL (Ubuntu). Put `wtf` in `~/bin` and add to PATH.

- **Native without WSL:** Save as `wtf.py`, ensure `.py` is associated with Python launcher, and place on PATH so you can run `wtf "..."`.
   Optional wrapper `wtf.cmd` (same directory):

  ```cmd
  @echo off
  py "%~dp0wtf.py" %*
  ```

## Requirements

- **Python:** 3.8+ (stdlib only: `urllib`, `json`, `threading`).
- **No venv needed.** No `pip` dependencies.

## Environment variables

- `OPENAI_API_KEY` *(required)* — your API key.
- `WTF_LLM_MODEL` *(optional)* — model name; defaults to `gpt-4o`.
   Shorthands supported: `4o`, `4o-mini`, `4.1`, `5`.
- `OPENAI_BASE_URL` *(optional)* — override the base URL (e.g., a compatible proxy). Default: `https://api.openai.com`.
- `WTF_PHRASE_DELAY` *(optional)* — spinner phrase duration (how often to change phrases), in seconds (float). Default: `1.0`. 

## Usage

```bash
wtf "explain vector similarity like I'm 5"
wtf "longer answer: compare Parquet-on-S3 vs ingesting to DuckDB, include tradeoffs"
wtf "give me a 1-line jq to extract the first field"
```

- Output is **ASCII-only** to keep terminals happy.
- **Spinner** runs on stderr and won’t pollute pipelines:

```bash
wtf "one-liner to list files by size desc" | pbcopy   # macOS
wtf "generate a bash for-loop example" | xclip -sel clip  # Linux
```

To suppress the spinner entirely:

```bash
wtf "..." 2>/dev/null
```

## Behavior details

- **System prompt** is provided via top-level `instructions` (kept short, terminal-friendly).
- **Input** uses the simple string form (`"input": "..."`).
- **Web search**: the script sends `tools: [{"type": "web_search"}]`.
   If the model/account doesn’t support it, the script **auto-retries without tools**.
- **Errors** go to **stderr** with non-zero exit codes.
  - `2` = usage error (no prompt)
  - `1` = request/parse failure
  - `0` = success

## Security

Treat `OPENAI_API_KEY` like any other secret:

- Don’t commit it.
- Consider using your shell’s secret manager or an `.env` that’s `.gitignore`’d.

## FAQ / Troubleshooting

**It says:** `ERROR: OPENAI_API_KEY is not set.`
 → Export your key (`export OPENAI_API_KEY=...`) in your shell profile.

**HTTP 400 invalid type (`'text'` vs `'input_text'`)**
 → This script already uses the correct schema (`instructions` + string `input`). If you edited it to the structured form, ensure you use `{"type": "input_text"}` for user inputs.

**I need Unicode output.**
 → Replace the last line with:

```python
print(text)
```

(Currently we strip to ASCII for better terminal compatibility.)

**I don’t want the spinner messages.**
 → Redirect stderr: `wtf "..." 2>/dev/null`.

**I want to force-disable web search.**
 → Remove the `tools` line in the payload or comment it out.

**Point to a proxy / mirror?**
 → Set `OPENAI_BASE_URL` to your compatible endpoint.

## Example session

```bash
export OPENAI_API_KEY=sk-...
export WTF_LLM_MODEL=4o   # optional

wtf "short: best practice for DuckDB parquet on S3?"
# [spinner on stderr: "[/] spinning up neurons...", etc...]
# stdout: "Use partitioned Parquet + object store caching, pushdown filters, and avoid tiny files; consider local caching with s3:// and enable parallel scans."
```

## File layout

```
.
├── wtf            # the single-file Python script (executable)
├── .env.template  # env vars used by wtf
└── README.md      # this file
```

## License

License? For this? I don't think so. Use it however you want. lol
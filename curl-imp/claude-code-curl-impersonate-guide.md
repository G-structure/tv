# Claude Code + curl-impersonate on a MacBook M4

This guide is meant to be handed to Claude Code or kept next to your Claude Code setup. It explains what `curl-impersonate` is, how to install it on an Apple Silicon MacBook M4, and how to package the setup as a Claude Code skill so Claude can use it reliably.

## 1) What curl-impersonate is

`curl-impersonate` is a special build of `curl` that mimics real browser TLS and HTTP handshakes much more closely than normal `curl`. It ships wrapper commands such as:

- `curl_chrome116`
- `curl_ff117`
- `curl_safari15_5`

Those wrappers apply the right headers and low-level options for the browser profile they impersonate.

### Important caveat

The project is useful when a site behaves differently for normal `curl` than for a browser-like client, but the browser fingerprints in the public repo are not evergreen. At the time of writing, the documented targets include Chrome 116, Firefox 117, and Safari 15.5 rather than the latest shipping browsers. Treat it as “browser-like impersonation,” not “identical to the newest browser on the market.”

## 2) Best setup choice on a MacBook M4

For an Apple Silicon Mac, use this order of preference:

1. **Native source build on macOS** — best for speed and simplest Claude Code integration.
2. **Local Docker build from the repo** — best when you want isolation or a reproducible container image.
3. **Public Docker image fallback** — acceptable if it works on your machine, but less predictable on Apple Silicon.

Avoid planning around the project’s prebuilt macOS binaries on an M4. The repo documents prebuilt macOS binaries for **Intel**, while the official install guide also includes a native **macOS source-build** path. On Apple Silicon, source build or Docker is the safer route.

## 3) Native install on macOS (recommended)

### Prerequisites

Install the build dependencies documented by the project:

```bash
brew install pkg-config make cmake ninja autoconf automake libtool
brew install sqlite nss
brew install go
python3 -m pip install --user gyp-next
```

### Build and install

```bash
git clone https://github.com/lwthiker/curl-impersonate.git
cd curl-impersonate
mkdir build && cd build
../configure

# Firefox version

gmake firefox-build
sudo gmake firefox-install

# Chrome/Edge/Safari version

gmake chrome-build
sudo gmake chrome-install
```

### Verify the install

```bash
command -v curl_chrome116
command -v curl_ff117
command -v curl_safari15_5

curl_chrome116 https://www.wikipedia.org
curl_ff117 https://www.wikipedia.org
```

### Notes

- The **Chrome build** is the one that also provides the Edge and Safari wrapper scripts.
- The **Firefox build** is separate.
- Keep in mind that changing certain `curl` flags can change the fingerprint and make it easier to detect.

## 4) Docker setup on Apple Silicon

### Install Docker Desktop for Apple silicon

Install the Apple Silicon build of Docker Desktop.

If you ever need to run an x86/amd64 container on Apple Silicon, Docker Desktop can use Rosetta-based amd64 emulation, but Docker documents that Intel containers on Apple Silicon are **best effort only** and may be slower, use more memory, or fail.

### Best Docker path: build the images locally

The project’s `INSTALL.md` describes the Docker build as the reference implementation. Build both images locally from a fresh checkout:

```bash
git clone https://github.com/lwthiker/curl-impersonate.git
cd curl-impersonate

docker build -t curl-impersonate-chrome:local chrome/
docker build -t curl-impersonate-ff:local firefox/
```

### Verify the local Docker images

```bash
docker run --rm curl-impersonate-chrome:local curl_chrome116 https://www.wikipedia.org
docker run --rm curl-impersonate-ff:local curl_ff117 https://www.wikipedia.org
```

### If you choose to use the public Docker images

The repo README shows examples such as:

```bash
docker pull lwthiker/curl-impersonate:0.6-chrome
docker pull lwthiker/curl-impersonate:0.6-ff
```

On an M4, only use `--platform linux/amd64` if you actually need emulation. Example:

```bash
docker run --rm --platform linux/amd64 \
  lwthiker/curl-impersonate:0.6-chrome \
  curl_chrome116 https://www.wikipedia.org
```

Prefer native arm64 or locally built images whenever possible.

## 5) How Claude Code skills should be structured

Claude Code skills are directories with a required `SKILL.md` entrypoint.

Use one of these locations:

- **Personal skill** for all projects:
  - `~/.claude/skills/<skill-name>/SKILL.md`
- **Project skill** for one repository:
  - `.claude/skills/<skill-name>/SKILL.md`

A good skill layout for this use case looks like this:

```text
curl-impersonate-fetch/
├── SKILL.md
├── examples.md
└── scripts/
    └── fetch-with-curl-impersonate.sh
```

### Design rules for this skill

- Make it **manual-only** with `disable-model-invocation: true` because it performs network requests.
- Keep `SKILL.md` short and focused.
- Put the real shell logic into a helper script under `scripts/`.
- Use `${CLAUDE_SKILL_DIR}` to reference bundled files from the skill.
- Use `$ARGUMENTS` to pass the user’s URL and optional mode into the helper script.
- Restrict `allowed-tools` to the smallest Bash surface area that still works.

## 6) Recommended skill behavior

The skill should do the following:

1. Accept a URL as the first argument.
2. Accept an optional browser mode: `chrome`, `firefox`, or `safari`.
3. Prefer a **native wrapper** if one is installed locally.
4. Fall back to **local Docker images** if native wrappers are not installed.
5. Optionally fall back to the public Docker image tags if local images are not present.
6. Report which path it used: native or Docker.
7. Refuse to frame the task as bypassing auth, paywalls, CAPTCHAs, or rate limits.

## 7) Recommended SKILL.md

Save this as either:

- `~/.claude/skills/curl-impersonate-fetch/SKILL.md`, or
- `.claude/skills/curl-impersonate-fetch/SKILL.md`

```md
---
name: curl-impersonate-fetch
description: Fetch a URL with curl-impersonate when a site behaves differently for normal curl than for a browser-like client. Use for legitimate compatibility testing, debugging, and fetching pages you are authorized to access.
argument-hint: [url] [chrome|firefox|safari] [extra-curl-flags...]
disable-model-invocation: true
allowed-tools: Bash(/bin/bash *)
---

# curl-impersonate fetch

Use this skill when:

- a site returns different content to a browser-like client than to normal curl
- browser-like TLS/HTTP handshakes are needed for debugging or compatibility testing
- the user explicitly asks to use curl-impersonate

Do not use this skill to bypass authentication, rate limits, CAPTCHAs, paywalls, or other access controls.

## Procedure

1. Treat the first argument as the URL.
2. Treat the second argument as an optional browser selector if it is `chrome`, `firefox`, or `safari`.
3. Pass all provided arguments to the helper script exactly as written.
4. Run:

```bash
/bin/bash "${CLAUDE_SKILL_DIR}/scripts/fetch-with-curl-impersonate.sh" $ARGUMENTS
```

5. After running the command, summarize:
   - which execution path was used: native wrapper or Docker
   - which browser profile was used
   - whether the fetch succeeded
   - any non-zero exit code or Docker architecture issue

6. If the helper script reports that neither native wrappers nor Docker are available, explain the missing dependency and point the user to the setup steps in this skill’s companion guide.
```

## 8) Recommended helper script

Create `scripts/fetch-with-curl-impersonate.sh` next to `SKILL.md`:

```bash
#!/bin/bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "usage: fetch-with-curl-impersonate.sh <url> [chrome|firefox|safari] [extra-curl-flags...]" >&2
  exit 2
fi

url="$1"
shift || true

browser="chrome"
if [[ $# -gt 0 ]]; then
  case "$1" in
    chrome|firefox|safari)
      browser="$1"
      shift
      ;;
  esac
fi

extra_args=("$@")

case "$browser" in
  chrome)
    native_wrapper="${CURL_IMPERSONATE_CHROME_WRAPPER:-curl_chrome116}"
    local_image="${CURL_IMPERSONATE_DOCKER_IMAGE_CHROME_LOCAL:-curl-impersonate-chrome:local}"
    fallback_image="${CURL_IMPERSONATE_DOCKER_IMAGE_CHROME:-lwthiker/curl-impersonate:0.6-chrome}"
    docker_wrapper="${CURL_IMPERSONATE_DOCKER_WRAPPER_CHROME:-curl_chrome116}"
    ;;
  firefox)
    native_wrapper="${CURL_IMPERSONATE_FIREFOX_WRAPPER:-curl_ff117}"
    local_image="${CURL_IMPERSONATE_DOCKER_IMAGE_FIREFOX_LOCAL:-curl-impersonate-ff:local}"
    fallback_image="${CURL_IMPERSONATE_DOCKER_IMAGE_FIREFOX:-lwthiker/curl-impersonate:0.6-ff}"
    docker_wrapper="${CURL_IMPERSONATE_DOCKER_WRAPPER_FIREFOX:-curl_ff117}"
    ;;
  safari)
    native_wrapper="${CURL_IMPERSONATE_SAFARI_WRAPPER:-curl_safari15_5}"
    local_image="${CURL_IMPERSONATE_DOCKER_IMAGE_CHROME_LOCAL:-curl-impersonate-chrome:local}"
    fallback_image="${CURL_IMPERSONATE_DOCKER_IMAGE_CHROME:-lwthiker/curl-impersonate:0.6-chrome}"
    docker_wrapper="${CURL_IMPERSONATE_DOCKER_WRAPPER_SAFARI:-curl_safari15_5}"
    ;;
  *)
    echo "unsupported browser profile: $browser" >&2
    exit 2
    ;;
esac

if command -v "$native_wrapper" >/dev/null 2>&1; then
  echo "mode=native wrapper=$native_wrapper browser=$browser" >&2
  exec "$native_wrapper" "$url" "${extra_args[@]}"
fi

if command -v docker >/dev/null 2>&1; then
  docker_platform_args=()
  if [[ -n "${CURL_IMPERSONATE_DOCKER_PLATFORM:-}" ]]; then
    docker_platform_args=(--platform "$CURL_IMPERSONATE_DOCKER_PLATFORM")
  fi

  image="$local_image"
  if ! docker image inspect "$image" >/dev/null 2>&1; then
    image="$fallback_image"
  fi

  echo "mode=docker image=$image wrapper=$docker_wrapper browser=$browser" >&2
  exec docker run --rm "${docker_platform_args[@]}" "$image" "$docker_wrapper" "$url" "${extra_args[@]}"
fi

echo "Neither a native curl-impersonate wrapper nor Docker is available." >&2
echo "Install curl-impersonate natively or install Docker Desktop and build the local images." >&2
exit 127
```

Then make it executable:

```bash
chmod +x ~/.claude/skills/curl-impersonate-fetch/scripts/fetch-with-curl-impersonate.sh
```

If you are creating a project-local skill, replace the path with the repository’s `.claude/skills/...` path.

## 9) Recommended examples.md

This file is optional, but useful because Claude Code skills work well when they include examples.

Save it as `examples.md` next to `SKILL.md`:

```md
# Examples

## Native chrome wrapper

User:
`/curl-impersonate-fetch https://www.wikipedia.org chrome`

Expected behavior:
- Runs the local `curl_chrome116` wrapper if installed.
- Reports `mode=native`.

## Docker firefox wrapper

User:
`/curl-impersonate-fetch https://www.wikipedia.org firefox`

Expected behavior:
- If native wrapper is missing, uses Docker.
- Reports `mode=docker` and the image name.

## Docker fallback on Apple Silicon with amd64 emulation

Prerequisite before launching Claude Code:
`export CURL_IMPERSONATE_DOCKER_PLATFORM=linux/amd64`

User:
`/curl-impersonate-fetch https://www.wikipedia.org chrome`

Expected behavior:
- Runs Docker with `--platform linux/amd64`.
- Useful only when the image you need is not available natively for arm64.
```

## 10) Optional: persistent environment for Claude Code

Claude Code’s Bash commands do **not** keep environment variable exports from one Bash invocation to the next. If you want consistent wrapper names or Docker image tags, set them **before** launching Claude Code, or use `CLAUDE_ENV_FILE` so Claude Code sources a file before each Bash command.

Example env file:

```bash
mkdir -p ~/.claude/env
cat > ~/.claude/env/curl-impersonate.sh <<'SH'
export CURL_IMPERSONATE_CHROME_WRAPPER=curl_chrome116
export CURL_IMPERSONATE_FIREFOX_WRAPPER=curl_ff117
export CURL_IMPERSONATE_SAFARI_WRAPPER=curl_safari15_5

export CURL_IMPERSONATE_DOCKER_IMAGE_CHROME_LOCAL=curl-impersonate-chrome:local
export CURL_IMPERSONATE_DOCKER_IMAGE_FIREFOX_LOCAL=curl-impersonate-ff:local

# Only set this if you truly need amd64 emulation on Apple Silicon.
# export CURL_IMPERSONATE_DOCKER_PLATFORM=linux/amd64
SH

export CLAUDE_ENV_FILE="$HOME/.claude/env/curl-impersonate.sh"
claude
```

## 11) Suggested usage prompts

Examples you can type to Claude Code once the skill is installed:

```text
/curl-impersonate-fetch https://www.wikipedia.org chrome
/curl-impersonate-fetch https://example.com firefox -I
/curl-impersonate-fetch https://example.com safari --compressed
```

## 12) Operational advice for Claude Code

When using this skill, Claude Code should:

- prefer the native wrappers when available
- only use Docker if native wrappers are missing
- explain clearly whether a failure is due to missing wrapper binaries, missing Docker, or an Apple Silicon architecture mismatch
- avoid broad or invasive crawl behavior unless the user explicitly asks for it
- keep requests narrowly scoped to the user’s stated task

## 13) References

- Claude Code skills docs: https://code.claude.com/docs/en/slash-commands
- Claude Code settings docs: https://code.claude.com/docs/en/settings
- Claude Code setup docs: https://code.claude.com/docs/en/setup
- curl-impersonate README: https://github.com/lwthiker/curl-impersonate
- curl-impersonate install guide: https://github.com/lwthiker/curl-impersonate/blob/main/INSTALL.md
- Docker Desktop for Mac: https://docs.docker.com/desktop/setup/install/mac-install/
- Docker Desktop Apple Silicon settings and known issues:
  - https://docs.docker.com/desktop/settings-and-maintenance/settings/
  - https://docs.docker.com/desktop/troubleshoot-and-support/troubleshoot/known-issues/

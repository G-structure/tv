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

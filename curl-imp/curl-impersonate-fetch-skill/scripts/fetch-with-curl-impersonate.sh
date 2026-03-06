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

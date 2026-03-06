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

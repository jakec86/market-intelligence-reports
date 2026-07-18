---
name: advisor-model-pairing
description: advisorModel in settings.json must match the session model family or advisor calls 400
metadata: 
  node_type: memory
  type: feedback
  originSessionId: c16932d1-6723-4e23-9a13-1e4a2bca21dd
---

The `advisorModel` value in `~/.claude/settings.json` must belong to the same model family as the active session model, or the first advisor() call fails with a 400: `'<advisor-model>' cannot be used as an advisor when the request model is '<session-model>'`.

Pairings:
- Session **Opus 4.8** (`claude-opus-4-8`) → `"advisorModel": "opus"`
- Session **Fable 5** (`claude-fable-5`) → `"advisorModel": "mythos"` (Mythos 5 is Fable 5's reasoning companion)

**Why:** the advisor tool runs on a separate model; the API only allows same-generation advisor/session pairings.

**How to apply:** `advisorModel` is read at *session start*, so editing it (or switching models via the `/model` picker) requires a session restart to take effect. When changing the default model, update `advisorModel` to match and restart. Default everyday model is Opus 4.8 (1M) → keep `advisorModel: "opus"` unless deliberately running Fable 5.

Note: launch a model via the `/model` picker or a real terminal — running `claude --model ...` through Claude Code's `!` prefix fails with "Input must be provided through stdin or as a prompt argument" because the `!` shell is non-interactive (headless `--print` mode).

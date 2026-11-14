# PREREQ: set up a new machine for nothing-agent

Give this file to Claude Code on the new machine. Read HANDOVER.md and TODO.md after this file.

## 1. Tools for this project

| Tool | Why | Install (macOS) |
|---|---|---|
| Node.js 18 or later | Runs `brain.mjs` | `brew install node` |
| Claude Code, logged in with the subscription | `brain.mjs` uses the Agent SDK on the subscription, no API key | `npm install -g @anthropic-ai/claude-code`, then `claude` and log in |
| adb | `act.sh` drives the phone | `brew install android-platform-tools` |
| bash | `act.sh` is bash. zsh does not split `$VAR` into words | Built in |
| Tailscale (optional) | Reach the phone over 4G when away from home | tailscale.com |

Then:
```
cd nothing-agent && npm install
```

Phone: Developer options > Wireless debugging ON. The new machine must pair one time
(Wireless debugging > Pair device with pairing code, then `adb pair <ip:port>`).

## 2. Claude Code skills and plugins in use on the work laptop

Plugins (install with `/plugin` in Claude Code: add the marketplace, then install):

| Plugin | What it does | Source |
|---|---|---|
| ponytail | Forces the simplest solution that works (YAGNI, stdlib first) | marketplace `DietrichGebert/ponytail` |
| i-have-adhd | Short output, next actions first, numbered steps | `github.com/ayghri/i-have-adhd` (clone, add as a directory marketplace) |
| simmer | Iterative refine loop with judges | marketplace `2389-research/claude-plugins` |
| vibe-wise | Project notes in `.vibe-wise/` (this repo has old notes there, gitignored) | `github.com/nykooi1/vibe-wise` (clone, add as a directory marketplace) |

Personal skills (folder `~/.claude/skills/`):

| Skill | What it does | Where to get it |
|---|---|---|
| malaysian-casual-chat | Chat replies in mixed English and 华语 | Only on the work laptop at `~/.claude/skills/malaysian-casual-chat/SKILL.md`. Not in any repo yet |

The work laptop loads malaysian-casual-chat at every session start with this hook in
`~/.claude/settings.json`:
```json
"hooks": {
  "SessionStart": [{
    "matcher": "startup|resume|clear|compact",
    "hooks": [{
      "type": "command",
      "command": "f=\"$HOME/.claude/skills/malaysian-casual-chat/SKILL.md\"; [ -f \"$f\" ] && { echo 'MALAYSIAN CASUAL CHAT MODE ACTIVE'; awk 'n>=2; /^---$/{n++}' \"$f\"; } || exit 0",
      "timeout": 5
    }]
  }]
}
```

Work-only skills (scanner knowledge, news classifier, bug-bounty commands) are not needed for
this project. Do not copy them to the home machine.

## 3. Rules the user wants (from the work laptop memory)

- Read HANDOVER.md and TODO.md before you start. Update them when the context gets long.
- No git push or merge without the user's permission each time. No force push.
- No `Co-Authored-By` lines in commits.
- File names in kebab-case, functions and variables in snake_case.
- After code changes to a web UI, restart the server and reload the page.
- End each reply with options: 1. run something, 2. other options.
- `voice-samples/` is biometric data. Never commit it.

# Security and Privacy

This repository is intended to publish skill instructions and helper scripts, not runtime secrets.

Do not commit:

- `.entropy/` run directories from real research sessions
- login cookies, browser profiles, session files, or platform tokens
- `.env` files or API keys
- raw retrieval dumps that contain temporary source URLs or private account state
- personal documents used as source material unless they are explicitly public

The installer copies only the skill bundle directories. It does not configure retrieval accounts, browser login state, API keys, or agent permissions.

If a secret is accidentally pushed to a public remote:

1. Revoke or rotate the secret immediately.
2. Remove it from the repository.
3. Rewrite public history only after confirming all collaborators understand the impact.

Report security issues privately to the repository owner.

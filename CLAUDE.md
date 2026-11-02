# Man AI – Agent Instructions

Man AI is Superhairpieces' AI chief of staff: a project board kept current from Google Chat, a chat and live voice
with Gemini, Claude and ChatGPT, access to the company's systems, and a real web browser people can watch and take
over. It runs on Cloud Run in the Google Cloud project `shp-ai-bot-2026`. COMPANY_ASSISTANT.md describes it in
full; README.md covers setup and security.

It was split out of `mannetsang/trustpilot-ai-pipeline` (folder `chat-assistant/`), which still holds the company's
other tools (BigCommerce reports, Google Merchant scripts, the Trustpilot pipeline, `lib/secrets.py`).

## Agent Behavior

- If you believe something is correct, say "correct." If you believe something is wrong, say "wrong." Do not side
  with the user just to agree.

## Git

- Whenever you complete a piece of work (new feature, fix, config change), commit it and push to GitHub.
- Never commit secrets: tokens, webhook URLs, service-account keys, OAuth client JSON, `.env` files. They live in
  Secret Manager.

## Local Environment

Manne runs commands on **Windows** (PowerShell or `cmd.exe`). Give one-line commands, use `python` not `python3`,
and avoid shell builtins, pipes, `export` and heredocs.

## Layout

- `src/cloud_run/`: the app (Flask on Cloud Run, service `chat-assistant`). Firestore `(default)` database,
  collections `chat_assistant*`.
- `src/browser/`: the browser service (Playwright Chromium, service `web-browser`), callable only by the app.
- `scripts/gchat.py`: Google Chat from a Claude Code session, with Manne's stored sign-in; never sends without
  `--confirm`.
- `setup.sh`: one-time setup by a project Owner (service account, secrets, hourly job).
- `tests/`: `python -m unittest discover -s tests` runs everything offline (in-memory store, fakes).

## Deploy

    gcloud run deploy chat-assistant --source src/cloud_run --region us-central1 --project shp-ai-bot-2026 --quiet

    gcloud run deploy web-browser --source src/browser --region us-central1 --project shp-ai-bot-2026 --quiet

Both keep their existing settings (service account, env vars: `OWNER_EMAIL`, `GCP_PROJECT`, `BROWSER_URL`).
Redeploying `web-browser` closes every open browser tab, sign-ins included: deploy it only when it changed.
Pushes to `main` that touch `src/cloud_run/` deploy the app through `.github/workflows/deploy.yml`.

Live: https://chat-assistant-onvg62bzra-uc.a.run.app (sign-in: manne@superhairpieces.com, OAuth client
"Chat Assistant" in the project; its JSON is the secret `chat-assistant-oauth-client`).

## Credentials

All in Secret Manager in `shp-ai-bot-2026`, each readable only by the accounts that need it:
`chat-assistant-oauth-client`, `chat-assistant-user-token` (Manne's Google sign-in), `chat-assistant-run-token`
(the hourly job's header), plus the company keys the integrations read (BigCommerce, Amazon, SkuVault, ...;
`integrations.py` lists them), each granted to `chat-assistant@shp-ai-bot-2026.iam.gserviceaccount.com`.

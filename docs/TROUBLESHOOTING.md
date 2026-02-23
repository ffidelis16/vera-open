# Troubleshooting

Common issues and how to fix them.

---

## Config Errors

### `Config file not found at 'config.yaml'`

You haven't created your config file yet.

```bash
cp config.example.yaml config.yaml
# Edit config.yaml with your values
```

### `tasks.database_id is required`

Your Tasks database ID is empty in `config.yaml`. Find your database ID:

1. Open the database as a full page in Notion
2. Copy the URL: `notion.so/workspace/<database_id>?v=...`
3. Paste the 32-character hex string into `config.yaml`

### `tasks.database_id should be 32 hex characters`

The ID you pasted isn't the right length. Common mistakes:
- You copied the full URL instead of just the ID
- You copied a page ID instead of the database ID
- You included the `?v=...` part

### `daily_check is enabled but database_id is empty`

Either set the database_id or disable it:
```yaml
daily_check:
  enabled: false
```

### `Urgency weights must sum to 1.0`

The four weights under `scoring.urgency_weights` must add up to exactly 1.0.

### `persona.preset is 'custom' but no custom_prompt provided`

If you set `preset: "custom"`, you must also provide `custom_prompt`:
```yaml
persona:
  preset: "custom"
  custom_prompt: "Your custom system prompt here..."
```

---

## Environment Variables

### `Missing required environment variables`

Set all four secrets:
```bash
export NOTION_TOKEN=ntn_...
export ANTHROPIC_API_KEY=sk-ant-...
export TELEGRAM_BOT_TOKEN=1234567890:ABC...
export TELEGRAM_CHAT_ID=123456789
```

For local development, use a `.env` file:
```bash
export $(cat .env | xargs)
```

For GitHub Actions, add them as repository secrets (Settings → Secrets → Actions).

### `NOTION_TOKEN doesn't start with 'ntn_'`

You might be using an old-format token or a session cookie. Go to [notion.so/my-integrations](https://www.notion.so/my-integrations) and create a new integration.

### `TELEGRAM_CHAT_ID must be numeric`

The chat ID is a number, not your username. To find it:
1. Send `/start` to your bot on Telegram
2. Visit `https://api.telegram.org/bot<TOKEN>/getUpdates`
3. Look for `"chat":{"id":123456789}`

---

## Notion API Errors

### `Notion API 401 (unauthorized)`

Your integration token is invalid or expired. Regenerate it at [notion.so/my-integrations](https://www.notion.so/my-integrations).

### `Notion API 404 (object_not_found)`

The database exists but your integration doesn't have access. Fix:

1. Open the database in Notion
2. Click `•••` (top right) → **Connections**
3. Click **Connect to** → select your integration

### `Notion API 400 (validation_error)`

Usually means a property name in `config.yaml` doesn't match your database. Run with `debug.verbose: true` to see the full error. Common causes:
- Typo in property name (case-sensitive!)
- Property type mismatch (e.g., trying to write a number to a text field)
- Property was renamed or deleted in Notion

### `Rate limited (429). Waiting...`

Vera handles this automatically with exponential backoff. If you see it frequently, you may have too many parallel operations. This is rare with normal usage.

### `Failed after 3 attempts`

Notion's servers are having issues. Wait a few minutes and try again. If persistent, check [status.notion.so](https://status.notion.so).

---

## Claude API Errors

### `401 Unauthorized` / `invalid_api_key`

Your Anthropic API key is wrong. Check it at [console.anthropic.com](https://console.anthropic.com).

### `429 Rate Limit`

You've hit Anthropic's rate limit. This shouldn't happen with normal daily usage (1-2 calls/day). If it does, you may be on a free trial with strict limits.

### `overloaded_error`

Claude's servers are busy. The pipeline will fail, and you can retry by running the GitHub Actions workflow manually.

---

## Telegram Errors

### `Telegram API error (401)`

Your bot token is invalid. Create a new bot with @BotFather and update the token.

### `Telegram API error (400): chat not found`

The chat ID is wrong, or your bot hasn't been started. Send `/start` to your bot on Telegram, then try again.

### `HTML parse failed, sending as plain text`

The AI generated invalid HTML. Vera automatically falls back to plain text. If this happens often, check your custom persona prompt — it may not be instructing proper HTML output.

### Message not received

1. Check that you sent `/start` to your bot
2. Verify chat ID is correct
3. Check GitHub Actions logs for errors
4. Try `debug.dry_run: false` and `debug.verbose: true` locally

---

## GitHub Actions

### Workflow never runs

1. Make sure the workflow file is at `.github/workflows/daily.yml`
2. Check that Actions are enabled (Settings → Actions → General)
3. GitHub disables scheduled workflows on repos with no activity for 60 days. Push any commit to re-enable.

### Workflow runs but fails

Check the Actions log:
1. Go to your repo → **Actions** tab
2. Click the failed run
3. Expand the step that failed
4. Common issue: secrets not set (Settings → Secrets → Actions)

### Briefing arrives 15-20 minutes late

This is normal. GitHub Actions cron has documented delays of 5-20 minutes. It's not a bug.

### `config.yaml not found` in GitHub Actions

You need to either:
- Force-add it: `git add -f config.yaml && git commit -m "Add config" && git push`
- Or include it in the repo (remove it from `.gitignore`)

---

## Performance

### Pipeline takes more than 60 seconds

With verbose logging (`debug.verbose: true`), check which phase is slow:
- **Collectors:** Usually fast (<5s). If slow, you may have thousands of tasks.
- **Urgency update:** Each task = 1 API call. 100 tasks ≈ 15s.
- **AI synthesis:** Claude typically responds in 3-10s.
- **Telegram:** Near-instant.

For large task databases (500+), consider adding a stricter filter in `config.yaml` (e.g., only fetch tasks from the current month).

---

## Still stuck?

1. Run with full verbose logging:
   ```bash
   # In config.yaml, set:
   # debug:
   #   verbose: true
   python -m src.main --mode daily
   ```

2. Check each component independently:
   ```bash
   python -m src.main --mode validate   # Config OK?
   # If validate passes, the issue is in runtime (API calls)
   ```

3. Open an issue on GitHub with the error log (redact your tokens!).

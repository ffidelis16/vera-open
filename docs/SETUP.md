# Setup Guide

From zero to your first morning briefing in ~30 minutes.

---

## Prerequisites

- Python 3.11+ installed ([python.org](https://python.org))
- A Notion account (free tier works)
- A Telegram account
- A GitHub account (for automated scheduling)
- An Anthropic API key ([console.anthropic.com](https://console.anthropic.com))

---

## Step 1: Notion Integration

You need a Notion integration token so Vera can read your databases.

1. Go to [notion.so/my-integrations](https://www.notion.so/my-integrations)
2. Click **"New integration"**
3. Name it `Vera Open` (or whatever you prefer)
4. Select your workspace
5. Under **Capabilities**, ensure these are enabled:
   - ✅ Read content
   - ✅ Update content
   - ✅ Insert content
6. Click **Submit**
7. Copy the **Internal Integration Token** (starts with `ntn_`)

**Important:** You must share each database with this integration. Open each database in Notion → click `•••` (top right) → **Connections** → **Connect to** → select your integration.

---

## Step 2: Notion Databases

Vera needs at least one database: **Tasks**. The others are optional but recommended.

**Option A: Use the Vera template**
Duplicate the template (see [TEMPLATE.md](TEMPLATE.md)) and all databases come pre-configured.

**Option B: Use your existing databases**
Map your property names in `config.yaml`. See [CUSTOMIZE.md](CUSTOMIZE.md) for details.

**Finding your database ID:**

1. Open the database as a full page in Notion
2. Look at the URL: `https://notion.so/workspace/abc123def456...?v=...`
3. The database ID is the 32-character hex string **before** `?v=`
4. Example: `https://notion.so/myspace/a1b2c3d4e5f6789012345678abcdef01?v=...`
   → database_id = `a1b2c3d4e5f6789012345678abcdef01`

---

## Step 3: Telegram Bot

1. Open Telegram and search for **@BotFather**
2. Send `/newbot`
3. Follow the prompts to name your bot
4. Copy the **bot token** (format: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`)

**Finding your Chat ID:**

1. Send any message to your new bot (e.g., `/start`)
2. Open this URL in your browser (replace `<TOKEN>` with your bot token):
   ```
   https://api.telegram.org/bot<TOKEN>/getUpdates
   ```
3. Find `"chat":{"id":123456789}` in the response
4. That number is your Chat ID

---

## Step 4: Anthropic API Key

1. Go to [console.anthropic.com](https://console.anthropic.com)
2. Sign up or log in
3. Go to **API Keys** → **Create Key**
4. Copy the key (starts with `sk-ant-`)

Vera uses Claude Sonnet. Typical daily cost: $0.01-0.03/day.

---

## Step 5: Local Setup

```bash
# Clone the repository
git clone https://github.com/you/vera-open.git
cd vera-open

# Create your config
cp config.example.yaml config.yaml

# Create your .env file
cp .env.example .env
```

Edit `.env` with your actual values:
```env
NOTION_TOKEN=ntn_your_actual_token_here
ANTHROPIC_API_KEY=sk-ant-your_actual_key_here
TELEGRAM_BOT_TOKEN=1234567890:your_actual_bot_token
TELEGRAM_CHAT_ID=your_actual_chat_id
```

Edit `config.yaml` with your database IDs:
```yaml
tasks:
  database_id: "your_tasks_database_id_here"
daily_check:
  enabled: true  # or false if you don't have this database
  database_id: "your_daily_check_database_id_here"
```

Install dependencies:
```bash
pip install -r requirements.txt
```

---

## Step 5b: Tell Vera About Yourself (Optional but Recommended)

```bash
cp workspace/USER.example.md workspace/USER.md
```

Edit `workspace/USER.md` with free-form information about yourself: who you are, what you're working on, how you prefer to communicate. This is the single highest-impact customization — it turns generic briefings into ones that feel written for you specifically.

See [CUSTOMIZE.md](CUSTOMIZE.md#user-context-workspaceusermd) for examples.

---

## Step 6: Validate

```bash
# Load .env into your shell
export $(cat .env | xargs)

# Validate config + secrets
python -m src.main --mode validate
```

You should see:
```
✅ Config válida!
   Nome: Vera
   Idioma: pt-BR
   ...
```

If you see errors, check [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

---

## Step 7: First Run (Dry Run)

Set `debug.dry_run: true` in `config.yaml`, then:

```bash
export $(cat .env | xargs)
python -m src.main --mode daily
```

This runs the full pipeline but **doesn't send the Telegram message** — it prints the briefing to the console instead. Verify it looks correct.

---

## Step 8: First Real Briefing

Set `debug.dry_run: false` in `config.yaml`, then:

```bash
export $(cat .env | xargs)
python -m src.main --mode daily
```

Check Telegram. Your briefing should arrive within 60 seconds.

---

## Step 9: GitHub Actions (Automated Daily Runs)

1. Push your repository to GitHub (**do not push** `.env` or `config.yaml` — they're in `.gitignore`)

2. Add secrets in your GitHub repo:
   - Go to **Settings** → **Secrets and variables** → **Actions**
   - Add these repository secrets:
     | Name | Value |
     |---|---|
     | `NOTION_TOKEN` | Your Notion integration token |
     | `ANTHROPIC_API_KEY` | Your Anthropic API key |
     | `TELEGRAM_BOT_TOKEN` | Your Telegram bot token |
     | `TELEGRAM_CHAT_ID` | Your Telegram chat ID |

3. Push `config.yaml` **or** commit it to the repo:
   
   Since `config.yaml` is in `.gitignore` by default (it could contain sensitive info if you're careless), you have two options:
   
   **Option A (recommended):** Force-add it:
   ```bash
   git add -f config.yaml
   # If you created workspace/USER.md, add it too:
   git add -f workspace/USER.md
   git commit -m "Add config and user context"
   git push
   ```
   
   **Option B:** Rename `config.example.yaml` to `config.yaml` in the repo and make sure all your database IDs are filled in. Secrets stay in GitHub Secrets.

4. The workflow runs automatically at 9:00 AM BRT (12:00 UTC) every day.

5. To test immediately: go to **Actions** → **Daily Briefing** → **Run workflow**.

**Note:** GitHub Actions cron can delay 5-20 minutes. This is normal and documented by GitHub.

---

## Done

Your daily briefing is now automated. Every morning, Vera will:

1. Read your Notion databases
2. Calculate urgency scores and write them back
3. Detect gaps and patterns
4. Generate a personalized briefing
5. Send it to your Telegram

To customize the briefing style, scoring weights, or add more databases, see [CUSTOMIZE.md](CUSTOMIZE.md).

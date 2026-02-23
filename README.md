# Vera Open

**Morning OS for Notion users** — AI-powered daily briefings delivered via Telegram.

Vera reads your Notion workspace every morning, calculates what matters most, and sends you a concise briefing via Telegram. No app to open, no dashboard to check. Your day's priorities arrive where you already are.

---

## What it does

- **Reads your tasks** from Notion and calculates urgency scores (0-100) based on deadlines, priority, and staleness
- **Tracks your patterns** via daily check-ins (energy, mood, focus, sleep)
- **Prioritizes your day** — top 3 tasks, overdue alerts, blocked items
- **Detects gaps** — stale tasks, missing deadlines, declining energy trends
- **Generates a briefing** using Claude AI, personalized to your data and preferred tone
- **Knows who you are** — drop a `USER.md` with your context and briefings adapt to your role, habits, and communication style
- **Sends via Telegram** every morning, automatically

## How it works

```
Notion databases → Python collectors → Scoring engine → Claude AI → Telegram
                        (parallel)        (urgency,         (synthesis)
                                          priorities,
                                          gap audit)
```

Runs on GitHub Actions (free tier). Costs ~$0.01-0.03/day in AI API usage. Zero infrastructure to maintain.

## Quick start

```bash
# 1. Clone
git clone https://github.com/you/vera-open.git
cd vera-open

# 2. Copy and edit config
cp config.example.yaml config.yaml
# Edit config.yaml with your Notion database IDs

# 3. Set up secrets (for local testing)
cp .env.example .env
# Fill in your API keys

# 4. (Optional) Tell Vera about yourself
cp workspace/USER.example.md workspace/USER.md
# Edit with your context — makes briefings dramatically better

# 5. Install dependencies
pip install -r requirements.txt

# 6. Validate your setup
python -m src.main --mode validate

# 7. Run a dry run
# (set debug.dry_run: true in config.yaml first)
python -m src.main --mode daily
```

For the full setup guide including Notion integration, Telegram bot creation, and GitHub Actions deployment, see **[SETUP.md](docs/SETUP.md)**.

## Requirements

| Service | What you need | Cost |
|---|---|---|
| **Notion** | Free account + Integration token | Free |
| **Anthropic** | API key (Claude Sonnet) | ~$0.01-0.03/day |
| **Telegram** | Bot token + your Chat ID | Free |
| **GitHub** | Repository with Actions enabled | Free (2,000 min/mo) |
| **Python** | 3.11+ | — |

## Configuration

Vera is fully config-driven. Everything lives in `config.yaml`:

- **Persona** — `executive` (direct, metrics-focused) or `coach` (supportive, growth-oriented), or bring your own prompt
- **Databases** — map your Notion property names to Vera's internal model
- **Scoring** — adjust urgency weights (deadline proximity, priority, staleness)
- **Schedule** — set your briefing time and weekly review day
- **Language** — pt-BR, en-US, es-ES

See **[CUSTOMIZE.md](docs/CUSTOMIZE.md)** for all options.

## Notion template

Vera works with any Notion setup as long as you have a Tasks database. But if you're starting fresh, use the included template:

**[→ Duplicate the Vera Open template](https://notion.so)** *(link after publish)*

The template includes 4 databases pre-configured to work with Vera's defaults:

| Database | Purpose | Required? |
|---|---|---|
| **Tasks** | Your to-do list with status, priority, deadline | ✅ Yes |
| **Daily Check** | Daily energy/mood/focus/sleep log | Recommended |
| **Pipeline** | Deals, leads, job applications | Optional |
| **Energy Timing** | Your energy patterns by time of day | Optional |

See **[TEMPLATE.md](docs/TEMPLATE.md)** for database schemas.

## Project structure

```
vera-open/
├── src/
│   ├── main.py          # CLI entrypoint + async orchestrator
│   ├── config.py         # Pydantic config models + YAML loader
│   ├── notion.py         # Async Notion API client
│   ├── tasks.py          # Tasks collector + urgency calculator
│   ├── checks.py         # Daily check-in collector
│   ├── pipeline.py       # Pipeline collector
│   ├── timing.py         # Energy timing collector
│   ├── scorer.py         # Daily scores + streaks
│   ├── methodology.py    # Task prioritization
│   ├── auditor.py        # Gap detection + pattern analysis
│   ├── synthesize.py     # AI prompt builder + Claude API
│   ├── telegram.py       # Telegram delivery (HTML)
│   └── presets/          # Persona prompt templates
├── workspace/
│   └── USER.example.md   # Your context (who you are, how you work)
├── .github/workflows/
│   ├── daily.yml         # Daily briefing (9h BRT)
│   └── weekly.yml        # Weekly review (Sat 10h BRT)
├── config.example.yaml   # Configuration template
├── requirements.txt      # Python dependencies (4 packages)
└── docs/
    ├── SETUP.md
    ├── CUSTOMIZE.md
    ├── TEMPLATE.md
    └── TROUBLESHOOTING.md
```

## How Vera thinks

**Urgency score (0-100)** — weighted combination of:
- Deadline proximity (40%) — past-due = 100, tomorrow = 85, next week = 50
- Priority level (30%) — maps your 1-5 scale to 0-100
- Staleness (20%) — days since last edit (untouched tasks rise in urgency)
- Dependencies (10%) — reserved for v1.1

**Priority tiers:**
- 🔴 **Overdue** — urgency ≥ 95 (past deadline)
- 🟡 **Top 3** — highest urgency active tasks
- 🟢 **Should do** — next tier (positions 4-8)
- ⏸️ **Blocked** — tasks in blocked/waiting status

**Gap detection:**
- Tasks without deadlines (>3 = warning)
- Tasks untouched for 7+ days
- Missing daily check-ins
- Declining energy trends
- Urgency overload (>5 tasks at 70+)

## Modes

| Command | What it does | When |
|---|---|---|
| `--mode validate` | Checks config + environment | Anytime |
| `--mode daily` | Full daily briefing pipeline | Every morning |
| `--mode weekly_review` | Weekly retrospective | Saturdays |
| `--mode week_setup` | Plan the upcoming week | Sundays/Mondays |

## Troubleshooting

See **[TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)** for common issues.

## Roadmap

**v1.0** (current)
- [x] Daily briefing pipeline
- [x] Urgency scoring
- [x] Multi-database support
- [x] Configurable personas
- [x] Gap detection

**v1.1** (planned)
- [ ] Bidirectional Telegram (reply to reschedule, mark done)
- [ ] Weekly review with charts
- [ ] Dependency tracking between tasks
- [ ] Custom scoring formulas

## License

MIT — fork it, customize it, make it yours.

---

*Built by someone who got tired of opening Notion to figure out what to do today.*

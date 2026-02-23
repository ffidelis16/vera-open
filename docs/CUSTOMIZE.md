# Customization Guide

Everything in Vera is controlled by `config.yaml`. This guide covers every option.

---

## User Context (workspace/USER.md)

The most impactful personalization with the least effort.

Create `workspace/USER.md` with free-form information about yourself. Vera injects this into the AI's context every morning, so the briefing reads like it was written by someone who knows you — not a generic bot.

```bash
cp workspace/USER.example.md workspace/USER.md
# Edit with your info
```

Example:
```markdown
# About Me

## Who I am
Alex, freelance product designer in Berlin. 6 years of experience,
mostly B2B SaaS. Working across 3 clients right now.

## How I work
Night owl — peak energy after 8pm. Mondays are admin-heavy.
I tend to overcommit on deadlines.

## What matters right now
Trying to raise my rates to €100/h. Also training for a half marathon.

## Communication preferences
Be blunt. Don't sugarcoat missed deadlines. Remind me to eat.
```

This file is gitignored by default (it contains personal info). The AI reads it fresh every run, so you can edit it anytime — no redeploy needed.

If the file doesn't exist, Vera works fine without it — just with less personalized output.

---

## Persona

Controls the AI's tone and communication style.

```yaml
persona:
  preset: "executive"    # or "coach" or "custom"
  # custom_prompt: "..."  # only if preset is "custom"
```

**`executive`** — Direct, metrics-focused. Leads with what matters, flags risks, uses action verbs. Like a chief of staff.

**`coach`** — Supportive, growth-oriented. Acknowledges effort before gaps, celebrates streaks, connects tasks to bigger goals.

**`custom`** — Write your own system prompt. The prompt receives all the structured data and should output HTML for Telegram.

Example custom persona:
```yaml
persona:
  preset: "custom"
  custom_prompt: |
    You are a minimalist productivity advisor.
    Use only bullet points and numbers.
    Never exceed 5 lines per section.
    Tone: calm, zen, focused.
```

---

## Language

```yaml
language: "pt-BR"    # Also: "en-US", "es-ES"
```

Affects the AI's output language and date formatting. The persona prompt and all AI output will be in this language.

---

## Timezone

```yaml
timezone: "America/Sao_Paulo"
```

Used for urgency calculations (deadline proximity), schedule times, and daily check-in date matching. Must be a valid [IANA timezone](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones).

---

## Schedule

```yaml
schedule:
  daily_briefing: "09:00"
  weekly_review_day: "saturday"
  weekly_review_time: "10:00"
```

**Note:** These values are for reference and urgency calculations. The actual execution time is controlled by the GitHub Actions cron in `.github/workflows/daily.yml`. If you change your briefing time here, update the cron too.

To convert your local time to UTC for the cron: subtract your UTC offset (e.g., BRT = UTC-3, so 09:00 BRT = 12:00 UTC).

---

## Tasks Database

The only required database.

```yaml
tasks:
  database_id: "your_32_char_hex_id"
  fields:
    title: "Name"              # Title property (task name)
    status: "Status"           # Select property
    deadline: "Deadline"       # Date property
    priority: "Priority"       # Number property (1-5)
    urgency: "Urgência Real"   # Number property (Vera writes here)
    project: "Project"         # Rich text — set "" to skip
    tags: "Tags"               # Multi-select — set "" to skip
  status_groups:
    active: ["To Do", "Doing", "In Progress"]
    done: ["Done", "Complete"]
    blocked: ["Blocked", "Waiting"]
```

**Mapping your property names:** If your Tasks database uses different property names (e.g., `"Estado"` instead of `"Status"`), just change the values in `fields`. The keys (`title`, `status`, `deadline`, etc.) stay the same.

**Status groups:** Tell Vera which status values mean "active", "done", and "blocked". Vera only fetches tasks with status in `active` or `blocked`.

**Urgency field:** Vera writes a 0-100 score to this field. Create a Number property in your Tasks database and map it here. If you don't want Vera writing to your database, set `urgency: ""`.

---

## Daily Check Database

Tracks your daily energy, mood, focus, and sleep. Vera reads the last 7 days to personalize briefings.

```yaml
daily_check:
  enabled: true
  database_id: "your_32_char_hex_id"
  fields:
    date: "Date"           # Date property
    energy: "Energy"       # Number (1-5)
    mood: "Mood"           # Number (1-5)
    focus: "Focus"         # Number (1-5)
    sleep_quality: "Sleep" # Number (1-5)
    notes: "Notes"         # Rich text (optional context)
```

Set `enabled: false` if you don't use this.

---

## Pipeline Database

Track deals, leads, freelance prospects, job applications — anything with stages.

```yaml
pipeline:
  enabled: false
  database_id: ""
  fields:
    title: "Name"
    status: "Status"
    value: "Value"           # Number (monetary value)
    next_action: "Next Action"  # Rich text
    deadline: "Deadline"
  status_groups:
    active: ["Lead", "Proposal", "Negotiation"]
    won: ["Won", "Closed"]
    lost: ["Lost"]
```

Set `enabled: true` and fill in your database_id to include pipeline data in briefings.

---

## Energy Timing Database

Map your energy patterns throughout the day so Vera can suggest when to tackle which tasks.

```yaml
energy_timing:
  enabled: false
  database_id: ""
  fields:
    time_block: "Time Block"   # Select: "Morning", "Afternoon", "Evening"
    energy_level: "Energy"     # Number (1-5)
    best_for: "Best For"       # Rich text: "Deep work", "Admin", etc.
```

---

## Scoring

Fine-tune how urgency is calculated.

```yaml
scoring:
  urgency_weights:
    deadline_proximity: 0.4    # Closer deadline = higher urgency
    priority_level: 0.3        # User-set priority
    staleness: 0.2             # Days since last edit
    dependency_count: 0.1      # (Reserved for v1.1)
  streak:
    enabled: true
    metric: "tasks_completed"
```

**Weights must sum to 1.0.** Adjust to match your workflow:

| Profile | deadline | priority | staleness | dependency |
|---|---|---|---|---|
| **Deadline-driven** | 0.5 | 0.2 | 0.2 | 0.1 |
| **Priority-first** | 0.2 | 0.5 | 0.2 | 0.1 |
| **Anti-stagnation** | 0.3 | 0.2 | 0.4 | 0.1 |
| **Balanced** (default) | 0.4 | 0.3 | 0.2 | 0.1 |

---

## Debug

```yaml
debug:
  dry_run: false     # true = runs everything but doesn't send Telegram message
  verbose: false     # true = detailed logs for debugging
```

Recommended workflow:
1. Start with `dry_run: true` to verify output
2. Set `verbose: true` if something looks wrong
3. Switch to `dry_run: false` for production

---

## Adjusting GitHub Actions Schedule

Edit `.github/workflows/daily.yml`:

```yaml
on:
  schedule:
    - cron: "0 12 * * *"   # 12:00 UTC = 09:00 BRT
```

Common schedules:
| Local time | UTC offset | Cron |
|---|---|---|
| 07:00 BRT | UTC-3 | `0 10 * * *` |
| 08:00 BRT | UTC-3 | `0 11 * * *` |
| 09:00 BRT | UTC-3 | `0 12 * * *` |
| 08:00 EST | UTC-5 | `0 13 * * *` |
| 09:00 CET | UTC+1 | `0 8 * * *` |

---

## Adding a Custom Preset

Create a new file in `src/presets/`:

```
src/presets/minimalist.txt
```

Write your persona prompt:
```
You are a minimalist daily advisor.
Maximum 10 lines total. No headers, no bold.
Just the essentials, separated by line breaks.
Focus on the single most important task.
```

Then in `config.yaml`:
```yaml
persona:
  preset: "minimalist"
```

Vera will automatically load `src/presets/minimalist.txt`.

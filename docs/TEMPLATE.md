# Notion Template

Vera works with any Notion setup, but if you're starting fresh, this template gives you pre-configured databases that match Vera's defaults.

---

## Template Structure

```
📁 Vera Open (workspace)
├── 📊 Tasks
├── 📊 Daily Check
├── 📊 Pipeline
└── 📊 Energy Timing
```

---

## Tasks Database

Your main task list. The only required database.

| Property | Type | Required | Notes |
|---|---|---|---|
| **Name** | Title | ✅ | Task name |
| **Status** | Select | ✅ | `To Do`, `Doing`, `In Progress`, `Blocked`, `Waiting`, `Done`, `Complete` |
| **Deadline** | Date | Recommended | When the task is due |
| **Priority** | Number | Recommended | Scale 1-5 (5 = highest) |
| **Urgência Real** | Number | Auto | Vera writes here (0-100). Create the property, Vera fills it. |
| **Project** | Rich Text | Optional | Group tasks by project |
| **Tags** | Multi-select | Optional | Labels for filtering |

**Status values you should create:**

| Status | Group | Meaning |
|---|---|---|
| `To Do` | Active | Not started |
| `Doing` | Active | Currently working on |
| `In Progress` | Active | Underway |
| `Blocked` | Blocked | Can't proceed |
| `Waiting` | Blocked | Depends on someone else |
| `Done` | Done | Completed |
| `Complete` | Done | Alternative completion status |

**Tip:** You can add more status values. Just update `status_groups` in `config.yaml` to include them.

---

## Daily Check Database

One row per day. Log your subjective state to help Vera personalize briefings.

| Property | Type | Required | Notes |
|---|---|---|---|
| **Date** | Date | ✅ | Which day this check-in is for |
| **Energy** | Number | ✅ | 1-5 scale |
| **Mood** | Number | ✅ | 1-5 scale |
| **Focus** | Number | ✅ | 1-5 scale |
| **Sleep** | Number | Recommended | 1-5 scale (sleep quality) |
| **Notes** | Rich Text | Optional | Free-form context |

**How to use it:** Every morning (or evening), create a new row and rate your dimensions. Takes 30 seconds. Vera reads the last 7 days to detect trends.

**Scale guide:**

| Score | Energy | Mood | Focus | Sleep |
|---|---|---|---|---|
| 1 | Exhausted | Terrible | Can't concentrate | Barely slept |
| 2 | Low | Bad | Easily distracted | Poor |
| 3 | Moderate | Neutral | Average | Okay |
| 4 | Good | Good | Sharp | Good |
| 5 | Excellent | Great | In the zone | Perfect |

---

## Pipeline Database

Track anything with stages: freelance projects, job applications, sales leads.

| Property | Type | Required | Notes |
|---|---|---|---|
| **Name** | Title | ✅ | Item name |
| **Status** | Select | ✅ | `Lead`, `Proposal`, `Negotiation`, `Won`, `Closed`, `Lost` |
| **Value** | Number | Optional | Monetary value (R$, $, €) |
| **Next Action** | Rich Text | Recommended | What's the next step? |
| **Deadline** | Date | Optional | When action is needed |

---

## Energy Timing Database

Map your energy patterns. Small database (~3-5 rows) that rarely changes.

| Property | Type | Required | Notes |
|---|---|---|---|
| **Time Block** | Select | ✅ | `Morning`, `Afternoon`, `Evening`, `Night` |
| **Energy** | Number | ✅ | 1-5 average energy for this block |
| **Best For** | Rich Text | Recommended | What type of work fits this energy level |

**Example data:**

| Time Block | Energy | Best For |
|---|---|---|
| Morning | 3 | Admin, email, light tasks |
| Afternoon | 4 | Deep work, writing, complex problems |
| Evening | 5 | Creative work, brainstorming |
| Night | 2 | Reading, planning tomorrow |

---

## Creating the Template Manually

If you prefer to create databases yourself instead of duplicating:

1. Create a new Notion page called "Vera Open" (or any name)
2. Inside it, create 4 inline databases with the schemas above
3. Share each database with your Notion integration (see [SETUP.md](SETUP.md#step-1-notion-integration))
4. Copy each database ID and paste into `config.yaml`

---

## Connecting Existing Databases

If you already have a task manager in Notion:

1. Check which properties your database has
2. Map them in `config.yaml` under `tasks.fields`
3. If you're missing a property (like `Urgência Real`), just create it — Notion makes this easy
4. Run `python -m src.main --mode validate` to confirm everything connects

**Example:** Your database uses Portuguese property names:

```yaml
tasks:
  database_id: "abc123..."
  fields:
    title: "Tarefa"
    status: "Estado"
    deadline: "Prazo"
    priority: "Prioridade"
    urgency: "Urgência"
    project: "Projeto"
    tags: "Etiquetas"
  status_groups:
    active: ["A Fazer", "Em Progresso"]
    done: ["Concluído"]
    blocked: ["Bloqueado"]
```

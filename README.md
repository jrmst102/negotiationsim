# Negotiation Simulation

A web-based negotiation simulation for the MS in Integrated Marketing — Competitive Strategy course. Students negotiate a Brand Partnership deal through structured rounds, receiving AI-powered feedback and scoring against an objective rubric.

## Features

### Homework Mode (v1.0)
- **Brand Partnership scenario** — 3-round negotiation with 8 term fields (base fee, royalty rate, campaign duration, exclusivity, performance bonus, termination period, usage rights)
- **AI counterpart** — GPT-4 Mini with a fixed persona (Victoria Chen), hidden priorities, and conversation memory
- **Objective scoring** — Economic Value (40%), Strategic Alignment (30%), Relationship Preservation (20%), Information Management (10%)
- **Anonymized leaderboard** — auto-generated aliases (Adjective + Noun); instructor sees real name mapping
- **3-submission cap** per round

### Class Session Mode (v1.2)
- **Two activity modes** — Homework (async, individual, Human-AI) and Class Session (synchronous, instructor-paced)
- **Group negotiation** — teams of 2–6 students negotiate together with a designated lead submitter
- **Human-Human counterpart** — groups paired against each other; one side plays buyer (student role), the other plays seller (partner role)
- **Instructor-controlled pacing** — timed rounds with pause/resume/extend, manual round advancement
- **Counterpart configuration** — ALL_HH, ALL_HA, or MIXED mode per session
- **AI as evaluator** — in HH matches, GPT-4 Mini scores both sides using the objective rubric
- **Dual leaderboards** — homework and class session scores tracked separately

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12, FastAPI, Uvicorn |
| Templates | Jinja2 (server-side rendered HTML) |
| Styling | Custom CSS |
| Data | CSV files via storage abstraction |
| AI | OpenAI GPT-4 Mini (`gpt-4o-mini`) |
| Auth | bcrypt + itsdangerous signed session cookies |
| Storage | DigitalOcean Spaces (S3) or local filesystem |
| Deployment | DigitalOcean App Platform |

## Project Structure

```
app/
├── ai/                  # OpenAI client, prompt templates
│   ├── openai_client.py # AI counterpart + HH evaluator
│   └── prompts.py       # System prompts, message builders
├── auth/                # Authentication
│   ├── login_manager.py # Multi-sim auth, session management
│   └── password_manager.py
├── core/                # Business logic
│   ├── aliases.py       # Anonymous alias generation
│   ├── groups.py        # Group CRUD + member management
│   ├── scenarios.py     # Scenario definitions + partner briefings
│   ├── scoring.py       # Rubric scoring (student + partner roles)
│   └── sessions.py      # Class session lifecycle + timers
├── data/
│   └── csv_manager.py   # CSV read/write abstraction
└── storage/
    ├── config.py        # Storage backend selection
    └── store.py         # DO Spaces / local filesystem

web/
├── main.py              # FastAPI app, middleware, startup
├── routes/
│   ├── admin_routes.py  # Admin dashboard, groups, sessions, control
│   ├── auth_routes.py   # Login/logout, session cookies
│   └── student_routes.py # Homework + class session flows
├── static/
│   └── style.css
└── templates/           # Jinja2 templates (22 files)

scripts/
└── provision_demo.py    # Demo data provisioning
```

## Quick Start

### Prerequisites
- Python 3.12+
- OpenAI API key (for AI counterpart/evaluator)

### Setup

```bash
# Clone
git clone https://github.com/jrmst102/negotiationsim.git
cd negotiationsim

# Virtual environment
python -m venv .venv
source .venv/bin/activate

# Dependencies
pip install -r requirements.txt

# Environment
cp .env.example .env
# Edit .env with your OPENAI_API_KEY

# Run
python run.py
```

The app starts at `http://localhost:8080`. On first launch, a demo simulation is provisioned with:

| User | Password | Role |
|------|----------|------|
| professor | Secret123! | Admin |
| student1 | student1 | Student |
| student2 | student2 | Student |
| student3 | student3 | Student |

Simulation code: `demo`

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SESSION_SECRET` | Yes | Cookie signing secret |
| `OPENAI_API_KEY` | Yes | OpenAI API key |
| `OPENAI_MODEL` | No | Model name (default: `gpt-4o-mini`) |
| `OPENAI_MAX_TOKENS` | No | Max response tokens (default: `2000`) |
| `SPACES_ACCESS_KEY_ID` | No | DO Spaces key (omit for local storage) |
| `SPACES_SECRET_ACCESS_KEY` | No | DO Spaces secret |
| `SPACES_REGION` | No | DO Spaces region |
| `SPACES_BUCKET` | No | DO Spaces bucket name |
| `SPACES_ENDPOINT` | No | DO Spaces endpoint URL |

## Deployment

Configured for DigitalOcean App Platform via `Procfile`:

```
web: uvicorn web.main:app --host 0.0.0.0 --port ${PORT:-8080}
```

## License

See [LICENSE](LICENSE) for details.

---

© 2026 Dr. Jose Mendoza. All rights reserved.

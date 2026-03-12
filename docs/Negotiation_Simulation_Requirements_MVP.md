# Competitive Strategy Negotiation Simulation
## Software Requirements Specification — MVP (Phase 1)

**Program:** MS in Integrated Marketing — Competitive Strategy Course
**Platform:** Analytics Toolkit
**Version:** 1.0 — Draft

---

## 1. Executive Summary

This document defines the software requirements for the Competitive Strategy Negotiation Simulation, an AI-powered educational tool for the MS in Integrated Marketing program. The simulation allows graduate students to practice marketing negotiation against an AI counterpart through structured, multi-round scenarios with objective scoring and competitive benchmarking.

The MVP delivers one complete scenario (Brand Partnership / Co-Branding Deal) with three negotiation rounds, a structured form-based interface, AI-powered evaluation using GPT-4 Mini, composite scoring, and an anonymized leaderboard. The application integrates into the existing Analytics Toolkit platform, reusing the Unified User Management System (UMS) for authentication, role-based access, organization management, and shared UI components.

Two additional scenarios (Retail Shelf Space and Media Buy) are designed and will be displayed as locked placeholders in the MVP, with development planned for Phase 2.

---

## 2. Project Context

### 2.1 Platform Overview

The Analytics Toolkit is a multi-application educational platform serving the MS in Integrated Marketing program. The platform currently includes four planned applications: Competitive Strategy Simulation (this project), AHP Studio, Dynamic Pricing Sandbox, and Marketing Mix Modeling Sandbox. All applications share a centralized identity and access management layer provided by the UMS.

### 2.2 Existing Infrastructure

The UMS is a production-deployed Turborepo monorepo providing authentication, RBAC, organization management, and shared UI. The simulation will be built as a new application within this monorepo, consuming existing packages as internal dependencies. This approach avoids package publishing overhead and leverages the established build pipeline, deployment configuration, and CI/CD workflows.

**Production URL:** https://sea-turtle-app-svipi.ondigitalocean.app

### 2.3 Architecture Decision: Monorepo Integration

The simulation is added to the existing UMS Turborepo monorepo rather than created as a separate repository. The simulation backend becomes a new package (`packages/strategy-service`) and the simulation frontend becomes new pages/routes within the existing web application (`apps/web`). This is the recommended approach for MVP because:

- It provides zero-config access to shared packages (`@toolkit/auth-client`, `@toolkit/ui-kit`, `@toolkit/shared-config`).
- It uses the existing Turborepo build and CI pipeline.
- It keeps deployment consolidated on DigitalOcean App Platform.
- It avoids npm package publishing complexity.

Extraction to a separate repository can be evaluated in future phases if the codebase grows significantly.

---

## 3. Technology Stack

### 3.1 Inherited from UMS

| Layer | Technology | Notes |
|-------|-----------|-------|
| Runtime | Node.js 20 LTS | Shared across all services |
| Language | TypeScript 5 (strict) | Full type safety |
| API Framework | Express 4 | With Zod validation, Helmet, CORS |
| Database | PostgreSQL 16 | Via Prisma 6 ORM |
| Authentication | JWT access + refresh tokens | httpOnly cookie-based refresh |
| Frontend | React 18 + Vite 5 | Single-page application |
| Styling | Tailwind CSS 3 | With shared design tokens |
| Build System | Turborepo + npm workspaces | Monorepo orchestration |
| CI/CD | GitHub Actions | lint → test → build pipeline |
| Testing | Vitest + Supertest | Unit and integration tests |
| Hosting | DigitalOcean App Platform | API (Docker) + Web (static) + DB (managed) |

### 3.2 New for Simulation

| Layer | Technology | Purpose |
|-------|-----------|---------|
| AI Engine | OpenAI GPT-4 Mini | AI negotiation counterpart and scoring evaluation |
| AI SDK | OpenAI Node.js SDK | API client for GPT-4 Mini integration |
| New DB Tables | PostgreSQL 16 (Prisma) | Scenario state, attempts, scores, leaderboard, aliases |
| State Management | React Context + hooks | Negotiation round state, form management |

### 3.3 Development and Deployment

| Concern | Approach |
|---------|----------|
| Version Control | GitHub (existing repository) |
| Branch Strategy | Feature branches → PR to main → auto-deploy |
| Local Development | Docker Compose for PostgreSQL; `npm run dev` for all services |
| Production Deployment | DigitalOcean App Platform; pushes to main trigger deploy |
| Environment Config | Environment variables via DigitalOcean app spec + local .env |
| API Architecture | New Express router mounted at `/strategy/*` within auth-service, or separate service |

---

## 4. Monorepo Structure

The simulation adds the following to the existing UMS monorepo:

| Path | Type | Description |
|------|------|-------------|
| `packages/strategy-service/` | New package | Express API handling negotiation logic, AI integration, scoring, leaderboard |
| `packages/strategy-service/prisma/` | Schema extension | Prisma schema for simulation-specific tables (extends shared DB) |
| `packages/strategy-service/src/routes/` | API routes | Scenario, negotiation, scoring, and leaderboard endpoints |
| `packages/strategy-service/src/services/` | Business logic | AI service, scoring engine, leaderboard calculations |
| `packages/strategy-service/src/prompts/` | AI prompts | System prompts, persona configs, scenario briefings |
| `apps/web/src/pages/strategy/` | New pages | Scenario dashboard, negotiation interface, leaderboard, results |
| `apps/web/src/components/strategy/` | New components | Term sheet form, AI response display, score cards, leaderboard table |

### 4.1 Package Dependencies

The `strategy-service` package consumes the following existing packages:

- `@toolkit/shared-config` — Design tokens, app IDs, role hierarchy, environment helpers
- `@toolkit/auth-service` — Prisma client (shared database), auth middleware, role guards

The web application's strategy pages consume:

- `@toolkit/auth-client` — AuthProvider, ProtectedRoute, RequireRole, useAuth hooks
- `@toolkit/ui-kit` — AppShell, Button, Card, Table, Tabs, Modal, Toast, Badge, Spinner, Input, Select
- `@toolkit/shared-config` — Design tokens, API route constants

---

## 5. Functional Requirements

### 5.1 Authentication and Authorization

All authentication and authorization is handled by the existing UMS. No new auth logic is built for the simulation.

| Requirement | Implementation |
|-------------|---------------|
| Student login | Existing `/auth/login` endpoint; JWT issued by auth-service |
| Session management | Existing JWT access + refresh token rotation via auth-client |
| Route protection | Existing `ProtectedRoute` component wraps all `/strategy/*` pages |
| App access control | Existing app authorization middleware checks `competitive-strategy` permission |
| Role mapping | UMS `ADMIN` = Instructor; UMS `USER` = Student |
| Cohort mapping | UMS `Organization` = Class section / cohort |
| Student enrollment | Instructor generates invite code via `/orgs/:orgId/invite-codes`; students register with code |

### 5.2 Scenario Dashboard

The main entry point for the simulation. Displays all three scenarios as cards on a single page.

**5.2.1 Dashboard Layout**

- Three scenario cards displayed in a grid or vertical stack.
- MVP scenario (Brand Partnership) shows status: Not Started, In Progress, or Completed with score.
- Locked scenarios (Retail Shelf Space, Media Buy) display a lock icon overlay, scenario title, brief description, and a "Coming Soon" label. They are not clickable.
- Each unlocked scenario card shows: scenario name, brief description, student's current status, best/average score (if attempts exist), number of attempts, and a button to start or continue.

**5.2.2 Mode Selection**

When starting a new attempt, the student selects between Practice mode (scores are recorded but do not count toward the leaderboard) and Graded mode (scores count toward leaderboard and competitive benchmark). The instructor controls which modes are available via scenario configuration.

### 5.3 Negotiation Interface

The core interaction is a structured, form-based negotiation. There is no free-text conversation in the MVP. Each scenario consists of three rounds.

**5.3.1 Round Flow**

Each round follows this sequence:

1. **Briefing Display** — The student reads the round context: scenario background (Round 1) or updated situation with new market data (Rounds 2–3). This is read-only narrative content.

2. **Term Sheet Submission** — The student fills in a structured form with specific negotiation terms. Each field has defined valid ranges, units, and input types (slider, dropdown, numeric input). The student submits their proposed terms.

3. **AI Evaluation and Response** — The system sends the submitted terms to GPT-4 Mini along with the scenario context, AI persona configuration, and prior round history. The AI returns a structured response: per-term evaluation (Accept / Counter / Reject), counter-values for countered terms, narrative explanation in character (2–3 paragraphs), and overall deal status (Close to agreement / Far apart / Walkaway risk).

4. **Revise or Accept** — The student reviews the AI's response and either revises their offer and resubmits (returns to step 2), accepts the AI's counter-offer as-is, or locks in their current offer (ends the round at current terms).

5. **Round Closes** — The final agreed or last-submitted terms are recorded. These become the baseline for the next round. The student's per-round score is calculated.

**5.3.2 Term Sheet Fields (Brand Partnership MVP)**

The following fields define the structured negotiation form for the Brand Partnership scenario. Each field has a defined type, valid range, default value, and scoring weight.

| Field | Input Type | Range / Options | Scoring Weight |
|-------|-----------|----------------|---------------|
| Revenue Split (student %) | Slider | 20%–80% | High |
| Creative Control | Dropdown | Student Approval / Joint Approval / Partner Approval | High |
| Campaign Duration | Numeric (months) | 3–24 months | Medium |
| Exclusivity Window | Numeric (months) | 0–12 months | Medium |
| Brand Prominence | Dropdown | Co-equal / Student Lead / Partner Lead | Low |
| Performance Benchmark (target CAC reduction) | Slider | 5%–50% | Medium |
| Minimum Guaranteed Impressions | Numeric | 100K–5M | Medium |
| Exit Clause Trigger | Dropdown | No Exit / 30-day Notice / Performance-based / Mutual Agreement | Low |

These fields and ranges are preliminary and subject to calibration during test runs. The AI's hidden priorities, red lines, and walkaway thresholds are configured separately and not visible to students.

### 5.4 AI Counterpart

**5.4.1 Integration**

The AI counterpart is powered by GPT-4 Mini via the OpenAI API. Each student interaction (term sheet submission) results in one API call. The system prompt encodes the AI's persona, hidden priorities, red lines, and walkaway conditions. The conversation history (all prior submissions and responses within the attempt) is included in each call for implicit memory.

**5.4.2 Persona Configuration (Brand Partnership)**

- **Role:** VP of Partnerships at a large, established consumer brand.
- **Personality:** Polished, strategically minded, slightly guarded. Protective of brand equity.
- **Red lines:** Creative final approval must remain with the larger brand. Revenue split cannot go below a defined floor (configured per scenario).
- **Hidden priorities:** Values exclusivity highly (due to prior failed partnership). Prefers shorter initial commitment with renewal option.
- **Walkaway:** Terminates if the collective offer devalues the partnership below a configured threshold.

**5.4.3 AI Response Format**

The AI returns a structured JSON response that the frontend parses and displays:

- `terms` — Object with per-field evaluation: `{ status: accept|counter|reject, counterValue?: value, reasoning: string }`
- `narrative` — String, 2–3 paragraphs in character explaining the response and signaling priorities
- `dealStatus` — Enum: `CLOSE | FAR | WALKAWAY_RISK | WALKAWAY`
- `trustDelta` — Number (-1 to +1), change in AI's internal trust based on this submission

**5.4.4 AI Walkaway Behavior**

If the AI determines a walkaway, the round ends immediately. The student receives a partial score for that round (terms evaluated up to the walkaway point, with a penalty multiplier). The attempt is not terminated — the student proceeds to the next round with a narrative explaining the breakdown, and the terms reset to a default disadvantaged position. This ensures a poor round is penalized but does not prevent the student from completing the scenario.

### 5.5 Scoring System

**5.5.1 Objective Rubric**

Scoring is fully objective, based on the specific terms the student achieves relative to defined optimal and acceptable ranges. The AI evaluates each submission against the rubric as part of its response.

| Component | Weight | Measurement |
|-----------|--------|-------------|
| Economic Value | 40% | Revenue split, financial commitments relative to student's optimal range. Midpoint of AI's acceptable range = 50%; student's ideal = 100%. |
| Strategic Alignment | 30% | How well final terms serve briefing objectives (e.g., audience reach, CAC reduction). Each term evaluated against stated goals. |
| Relationship Preservation | 20% | Agreement reached (vs. walkaway), number of revision cycles, cumulative trust delta across rounds. Lower friction scores higher. |
| Information Management | 10% | Pattern analysis: did the student's offers reflect discovery of AI's hidden priorities (e.g., offering exclusivity to unlock concessions elsewhere)? |

**5.5.2 Score Calculation**

- Each round produces a component score (0–100) for each rubric element.
- Round weights: Round 1 = 25%, Round 2 = 35%, Round 3 = 40% (later rounds weighted higher).
- Scenario score = weighted sum of round scores across all rubric components.
- Attempt score = scenario score (single number, 0–100).
- Leaderboard score = average of all graded attempt scores for the student.

**5.5.3 Completion Requirement**

A student must complete all three rounds to receive a score. An attempt where the student exits before finishing all rounds is recorded as incomplete. Incomplete attempts do not count toward the average and the student appears as "In Progress" on the leaderboard with no score.

### 5.6 Leaderboard

**5.6.1 Structure**

- One leaderboard per scenario per cohort (UMS Organization).
- Columns: Rank, Anonymized Alias, Average Score, Number of Attempts, Percentile.
- Updates after each completed graded attempt.
- Students who have started but not completed appear at the bottom as "In Progress" with no score.
- The student's own row is visually highlighted.

**5.6.2 Anonymized Aliases**

Each student is assigned a randomly generated alias when they first access the simulation. Aliases follow an Adjective + Noun pattern (e.g., "Steel Falcon," "Coral Strategist," "Iron Compass"). The alias is consistent across all scenarios and persistent for the semester. The instructor can see the mapping between real names and aliases.

**5.6.3 Competitive Benchmark**

Percentile ranking is calculated as the percentage of students in the cohort with a lower average score. The percentile updates dynamically as more students complete the scenario. The competitive benchmark is available to the instructor as part of the grading data.

### 5.7 Instructor Features (MVP Scope)

The MVP includes a minimal instructor view. Full instructor dashboard is deferred to Phase 2.

- View all student scores for the cohort (real names mapped to aliases).
- Export scores as CSV for grade import into LMS.
- Toggle scenario availability (lock/unlock) — UI present but only functional for the MVP scenario.
- Toggle mode availability (practice only, graded only, or both).
- Run calibration attempts (instructor/TA plays through the scenario without affecting the leaderboard).

---

## 6. Data Model

The simulation extends the existing UMS PostgreSQL database with new tables. All tables reference the UMS `User` and `Organization` models via foreign keys.

| Table | Purpose | Key Fields |
|-------|---------|------------|
| Scenario | Scenario definitions and configuration | id, name, slug, description, status (ACTIVE/LOCKED), order, config (JSON) |
| ScenarioUnlock | Tracks which scenarios are unlocked per org | id, scenarioId, orgId, unlockedAt, unlockedBy |
| StudentAlias | Anonymized leaderboard identities | id, userId, orgId, alias (unique per org) |
| Attempt | One complete playthrough of a scenario | id, userId, orgId, scenarioId, mode (PRACTICE/GRADED), status (IN_PROGRESS/COMPLETED/ABANDONED), startedAt, completedAt |
| Round | One round within an attempt | id, attemptId, roundNumber (1–3), status, briefingShown, startedAt, completedAt |
| Submission | One term sheet submission within a round | id, roundId, submissionNumber, terms (JSON), aiResponse (JSON), score (JSON), submittedAt |
| AttemptScore | Final computed score for a completed attempt | id, attemptId, economicValue, strategicAlignment, relationshipPreservation, infoManagement, compositeScore, roundScores (JSON) |
| LeaderboardEntry | Cached leaderboard position | id, userId, orgId, scenarioId, averageScore, attemptCount, percentile, updatedAt |

---

## 7. API Endpoints

All endpoints are mounted under `/strategy` and require JWT authentication and `competitive-strategy` app access.

### 7.1 Scenarios

| Method | Path | Role | Description |
|--------|------|------|-------------|
| GET | `/strategy/scenarios` | User+ | List all scenarios with unlock status for the student's org |
| PATCH | `/strategy/scenarios/:id/unlock` | Admin | Unlock a scenario for the org |
| PATCH | `/strategy/scenarios/:id/lock` | Admin | Lock a scenario for the org |

### 7.2 Attempts

| Method | Path | Role | Description |
|--------|------|------|-------------|
| POST | `/strategy/scenarios/:id/attempts` | User | Start a new attempt (creates attempt + first round) |
| GET | `/strategy/attempts/:id` | User | Get attempt details including all rounds and submissions |
| GET | `/strategy/attempts` | User | List student's own attempts (optionally filtered by scenario) |
| POST | `/strategy/attempts/:id/abandon` | User | Mark an in-progress attempt as abandoned |

### 7.3 Negotiation

| Method | Path | Role | Description |
|--------|------|------|-------------|
| GET | `/strategy/rounds/:id/briefing` | User | Get the briefing content for a round |
| POST | `/strategy/rounds/:id/submit` | User | Submit term sheet; triggers AI evaluation; returns AI response |
| POST | `/strategy/rounds/:id/accept` | User | Accept current terms and close the round |
| POST | `/strategy/rounds/:id/lock-in` | User | Lock in student's last offer and close the round |

### 7.4 Scoring and Leaderboard

| Method | Path | Role | Description |
|--------|------|------|-------------|
| GET | `/strategy/scenarios/:id/leaderboard` | User+ | Get anonymized leaderboard for the student's org |
| GET | `/strategy/scores/me` | User | Get the student's own scores across all attempts |
| GET | `/strategy/scores/export` | Admin | Export all scores for the org as CSV (real names) |

### 7.5 Instructor Administration

| Method | Path | Role | Description |
|--------|------|------|-------------|
| GET | `/strategy/admin/students` | Admin | List all students with alias mappings and scores |
| PATCH | `/strategy/admin/config` | Admin | Update scenario config (mode availability, etc.) |

---

## 8. User Interface Screens

All screens use existing `@toolkit/ui-kit` components within the AppShell layout. New components are built with Tailwind CSS using shared design tokens.

| Screen | Route | Description |
|--------|-------|-------------|
| Scenario Dashboard | `/strategy` | Three scenario cards; active/locked states; student status and scores |
| Mode Selection | `/strategy/scenarios/:id/start` | Modal or page: Practice vs. Graded mode selection before starting |
| Negotiation — Briefing | `/strategy/attempts/:id/rounds/:n` | Read-only narrative briefing for the current round |
| Negotiation — Term Sheet | `/strategy/attempts/:id/rounds/:n/negotiate` | Structured form with sliders, dropdowns, and numeric inputs |
| Negotiation — AI Response | `/strategy/attempts/:id/rounds/:n/response` | AI's counter-offer displayed term-by-term with narrative |
| Round Summary | `/strategy/attempts/:id/rounds/:n/summary` | Agreed terms, per-round score breakdown, next round preview |
| Attempt Results | `/strategy/attempts/:id/results` | Final composite score, per-round breakdown, rubric detail |
| Leaderboard | `/strategy/scenarios/:id/leaderboard` | Anonymized rankings, student's row highlighted, percentile |
| My Scores | `/strategy/scores` | Student's own attempt history, averages, and per-attempt detail |
| Instructor — Scores | `/strategy/admin/scores` | All students, real names + aliases, export button |
| Instructor — Config | `/strategy/admin/config` | Scenario unlock toggles, mode toggles |

---

## 9. Non-Functional Requirements

### 9.1 Performance

- AI response latency: Target < 5 seconds per term sheet submission (dependent on GPT-4 Mini response time).
- Leaderboard updates: Within 10 seconds of attempt completion.
- Page load: < 2 seconds for all screens (consistent with existing UMS performance).

### 9.2 Scalability

MVP targets a single cohort of 30–60 students. The system should support concurrent usage by the full cohort (all students negotiating simultaneously). OpenAI API rate limits should be monitored; the service should implement retry with exponential backoff.

### 9.3 Security

- All existing UMS security measures apply (Helmet, CORS, JWT validation, httpOnly cookies).
- AI system prompts and persona configurations are server-side only; never exposed to the client.
- Students cannot access other students' attempt data or scores (except anonymized leaderboard).
- OpenAI API key stored as environment variable; never exposed to the client.

### 9.4 Data Integrity

- Submitted terms and AI responses are immutable once recorded.
- Scores are computed server-side and cannot be modified by the client.
- Leaderboard calculations are server-side, triggered by attempt completion.

### 9.5 Availability

The application is deployed on DigitalOcean App Platform with managed PostgreSQL, providing standard platform availability. No custom HA configuration is required for MVP.

---

## 10. Environment Configuration

The following environment variables are added for the simulation, in addition to all existing UMS variables:

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | API key for GPT-4 Mini access |
| `OPENAI_MODEL` | No | Model identifier (default: `gpt-4o-mini`) |
| `OPENAI_MAX_TOKENS` | No | Max response tokens per AI call (default: 2000) |
| `STRATEGY_SCORING_VERSION` | No | Scoring rubric version identifier for traceability (default: v1) |

---

## 11. MVP Scope Boundary

### 11.1 In Scope

- Brand Partnership scenario: three rounds with full term sheet, AI counterpart, scoring, and leaderboard.
- Scenario dashboard showing all three scenarios (two locked with lock icon and "Coming Soon" label).
- Structured form-based negotiation (no free-text conversation).
- GPT-4 Mini with fixed persona and implicit memory via conversation history.
- Objective rubric scoring with four weighted components.
- Unlimited attempts with running average on leaderboard.
- Anonymized leaderboard with generated aliases.
- Practice and graded modes (behavior is identical in MVP; only the leaderboard flag differs).
- Instructor score viewing and CSV export.
- Calibration mode for instructor/TA test runs.
- Full UMS integration (auth, roles, orgs, UI kit).

### 11.2 Out of Scope (Deferred)

| Feature | Target Phase |
|---------|-------------|
| Scenarios 2 and 3 (Retail Shelf Space, Media Buy) | Phase 2 |
| Functional sequential scenario unlocking | Phase 2 |
| Narrative interconnection between scenarios | Phase 2 |
| Team / group negotiation mode | Phase 2 or 3 |
| Adaptive AI difficulty (distinct behavior for practice vs. graded) | Phase 2 |
| Free-text conversation layer | Phase 3 |
| Transcript export for post-negotiation reflections | Phase 2 |
| Full instructor dashboard (analytics, per-student drill-down) | Phase 2 |
| Aggregate cross-scenario leaderboard | Phase 3 |

---

## 12. Open Items for Resolution

The following items require decisions or further specification before development begins:

| Item | Question | Impact |
|------|----------|--------|
| Revision cap per round | Is there a maximum number of resubmissions per round, or unlimited? | UI flow, AI cost, scoring logic |
| Practice vs. graded in MVP | If adaptive difficulty is deferred, does anything differ beyond the leaderboard flag? | Scope; may simplify to single mode for MVP |
| Alias style | Adjective + Noun (fun) vs. alphanumeric (neutral)? Instructor sees real name mapping? | UI, alias generation service |
| Cohort isolation | Leaderboards strictly per-org, or cross-section competition possible? | Leaderboard query logic |
| Data retention | How long are attempt records and scores retained? Semester? Persistent? | Database policy, storage planning |
| AI cost budget | Expected API cost per student per scenario (depends on revision count)? | May inform revision cap decision |
| Scoring calibration | Process for validating AI scoring consistency across students before launch? | QA / calibration sprint planning |

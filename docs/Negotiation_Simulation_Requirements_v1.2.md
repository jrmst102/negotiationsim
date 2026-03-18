# Competitive Strategy Negotiation Simulation
## Software Requirements Specification — v1.2

**Program:** MS in Integrated Marketing — Competitive Strategy Course
**Platform:** Analytics Toolkit
**Version:** 1.2 — Draft
**Builds on:** v1.0 MVP (completed)

---

## 1. Executive Summary

This document defines the requirements for v1.2 of the Competitive Strategy Negotiation Simulation. Version 1.0 (MVP) delivered a single scenario (Brand Partnership) with individual students negotiating against an AI counterpart through a structured form-based interface. Version 1.2 extends the simulation to support two activity modes, group-based negotiation, and Human-Human counterpart matching — enabling both classroom use and a controlled research experiment comparing AI and human negotiation partners.

### What's New in v1.2

- **Two activity modes:** Homework (asynchronous, individual, Human-AI only) and Class Session (synchronous, instructor-paced, groups, Human-Human or Human-AI).
- **Group negotiation:** Teams of 2–6 students negotiate together, with one designated member submitting on behalf of the group.
- **Human-Human counterpart:** In class sessions, groups can be paired against other groups instead of the AI. One side plays the smaller brand (student role), the other plays the larger brand (partner role). Both sides are scored on their own objectives.
- **Instructor-controlled pacing:** In class sessions, the instructor manually advances rounds for the entire class, with timed countdowns per round.
- **Counterpart configuration:** The instructor sets whether a class session is all-Human-Human, all-Human-AI, or mixed (random assignment with instructor override).
- **Separate leaderboards:** Homework and class session scores are tracked independently.
- **AI as evaluator:** In Human-Human matches, the AI shifts from counterpart to evaluator, scoring both sides after each round using the same objective rubric.
- **Research experiment support:** The counterpart configuration (HH vs. HA) and data tagging enable a cluster-randomized experiment comparing learning outcomes across conditions.

---

## 2. Project Context

### 2.1 Platform Overview

The Analytics Toolkit is a multi-application educational platform serving the MS in Integrated Marketing program. The platform currently includes four planned applications: Competitive Strategy Simulation (this project), AHP Studio, Dynamic Pricing Sandbox, and Marketing Mix Modeling Sandbox. All applications share a centralized identity and access management layer provided by the UMS.

### 2.2 Existing Infrastructure

The UMS is a production-deployed Turborepo monorepo providing authentication, RBAC, organization management, and shared UI. The v1.0 simulation is already deployed within this monorepo. Version 1.2 extends the existing codebase.

**Production URL:** https://sea-turtle-app-svipi.ondigitalocean.app

### 2.3 v1.0 (Completed)

The following was delivered in v1.0 and remains unchanged unless explicitly noted:

- Brand Partnership scenario with three rounds and structured term sheet (8 fields).
- Scenario dashboard with two locked placeholder scenarios (Retail Shelf Space, Media Buy).
- AI counterpart (GPT-4 Mini) with fixed persona, hidden priorities, implicit memory via conversation history.
- Objective rubric scoring (Economic Value 40%, Strategic Alignment 30%, Relationship Preservation 20%, Information Management 10%).
- 3-submission cap per round.
- Anonymized leaderboard with Adjective + Noun aliases; instructor sees real name mapping.
- Per-cohort leaderboard with optional cross-section competition.
- Instructor score viewing, CSV export, scenario lock/unlock, calibration mode.
- Full UMS integration (auth, roles, orgs, UI kit).
- Persistent data retention.

---

## 3. Technology Stack

### 3.1 Inherited from v1.0

All technologies from v1.0 carry forward unchanged (Node.js 20, TypeScript 5, Express 4, PostgreSQL 16 via Prisma 6, React 18 + Vite 5, Tailwind CSS 3, Turborepo, GitHub Actions, DigitalOcean App Platform, GPT-4 Mini via OpenAI SDK).

### 3.2 New for v1.2

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Real-time Communication | Polling (short-poll or SSE) | Sync class sessions: students see round timer, submission status, instructor round advancement |
| Timer Service | Server-side countdown | Enforces round time limits in class sessions; broadcasts remaining time to clients |

**Note:** WebSockets are an alternative to polling for real-time features. Polling is recommended for MVP simplicity given the low frequency of updates (round advancement, timer ticks). WebSockets can be evaluated if polling latency proves insufficient.

---

## 4. Activity Modes

Version 1.2 introduces two distinct activity modes. A scenario can be played in either mode, and scores are tracked separately per mode.

### 4.1 Homework Mode (Asynchronous, Human-AI)

This is the existing v1.0 behavior with no structural changes.

| Attribute | Value |
|-----------|-------|
| Pacing | Self-paced; student advances rounds at their own speed |
| Counterpart | AI only |
| Participants | Individual students |
| Submissions | 3 per round (existing cap) |
| Timer | None |
| Availability | Always available when scenario is unlocked |
| Leaderboard | Homework leaderboard (separate from class) |

### 4.2 Class Session Mode (Synchronous, Instructor-Paced)

A new mode designed for in-class use. The instructor creates a session, configures groups and pairings, and controls the pace of the negotiation for the entire class.

| Attribute | Value |
|-----------|-------|
| Pacing | Instructor manually advances rounds for all groups simultaneously |
| Counterpart | Human-Human, Human-AI, or mixed (instructor configures) |
| Participants | Groups of 2–6 students |
| Submissions | 3 per round (same cap) |
| Timer | Timed rounds with visible countdown (duration set by instructor, e.g., 10 minutes per round) |
| Availability | Only during an active class session created by the instructor |
| Leaderboard | Class session leaderboard (separate from homework) |

---

## 5. Functional Requirements

### 5.1 Authentication and Authorization

Unchanged from v1.0. All existing UMS auth, RBAC, and app-access controls apply.

### 5.2 Scenario Dashboard

The dashboard is extended to show both activity modes.

**5.2.1 Dashboard Layout**

- Three scenario cards as before (Brand Partnership active, two locked).
- Each unlocked scenario card shows two entry points: "Practice on Your Own" (homework mode) and "Join Class Session" (class session mode, visible only when an active session exists for the student's org).
- If no class session is active, the class session entry point shows "No Active Session" in a disabled state.
- Student status and scores are shown separately for homework and class modes.

### 5.3 Group Management

New functionality for class session mode.

**5.3.1 Group Creation**

- The instructor creates groups within their organization before starting a class session.
- Groups have 2–6 members, drawn from the org's student roster.
- The instructor can manually assign students to groups or use auto-assignment (system distributes students evenly into groups of a specified size).
- Each group has a designated **lead** who submits term sheets on behalf of the group. The instructor assigns the lead, or the first member added becomes lead by default. The lead can be changed by the instructor.
- Group membership is visible to all group members.

**5.3.2 Group Participation**

- All group members see the same scenario briefing, term sheet form, and counterpart responses.
- Only the designated lead can submit the term sheet. Other members see the form in read-only mode with a label indicating who the lead is.
- Group discussion and strategy coordination happen verbally (in class) — the system does not provide a group chat.
- The group's score applies to all members equally.

### 5.4 Class Session Management

New functionality for the instructor to control in-class negotiation sessions.

**5.4.1 Creating a Session**

The instructor creates a class session with the following configuration:

| Setting | Options |
|---------|---------|
| Scenario | Select from unlocked scenarios |
| Counterpart mode | All Human-Human / All Human-AI / Mixed (random assignment) |
| Round duration | Time limit per round in minutes (e.g., 10 minutes) |
| Groups | Select from pre-created groups, or create/edit groups at this point |

**5.4.2 Group Pairing (Human-Human)**

When the counterpart mode includes Human-Human pairings:

- The system randomly pairs groups. One group in each pair is assigned the **student role** (smaller brand) and the other the **partner role** (larger brand).
- The instructor can review and override pairings and role assignments before starting the session.
- In mixed mode, the system randomly assigns some groups to HH pairs and the remaining to HA (playing against AI). The instructor can override these assignments.
- **Odd group handling:** If there is an odd number of groups and the mode is all-HH or mixed, the system flags the unpaired group for the instructor to decide: assign to AI, have one group face two opponents in sequence, or another arrangement.

**5.4.3 Partner Role Briefing**

Groups assigned the partner role (larger brand) receive a different confidential briefing that includes:

- The larger brand's objectives and scoring criteria (different from the student role).
- The persona information that the AI uses in HA mode: hidden priorities, red lines, walkaway thresholds.
- Strategic guidance on how to evaluate incoming offers and construct counter-offers.

This ensures the HH experience mirrors the HA experience as closely as possible for research validity.

**5.4.4 Instructor Session Dashboard**

During an active session, the instructor sees a real-time dashboard showing:

- List of all groups with their pairing and role assignment.
- Current round number and countdown timer.
- Submission status per group: Not Submitted / Submitted (with timestamp) / Waiting for Counterpart.
- A **"Start Round"** button to begin each round (starts the timer).
- An **"Advance to Next Round"** button to close the current round and open the next (available after timer expires or when the instructor manually advances).
- An **"End Session"** button to close the session after Round 3 (triggers final scoring).
- Ability to pause the timer if needed.

**5.4.5 Round Flow in Class Session Mode**

1. Instructor clicks "Start Round" — the round timer begins for all groups.
2. Each group sees the briefing and term sheet form. The lead submits the group's offer within the time limit.
3. **In HH pairs:** When both groups in a pair have submitted, each side sees the other's offer (displayed in the same format as an AI response). The AI evaluates both submissions and provides scores, but the counter-offer comes from the human counterpart, not the AI. Groups may revise and resubmit (within the 3-submission cap and the time limit).
4. **In HA matches:** The flow is identical to homework mode — the AI responds to each submission. The time limit still applies.
5. When the timer expires or the instructor advances, the round closes. Any group that hasn't submitted uses default terms (midpoint of each field's range) and receives a penalty score for that round.
6. The instructor advances to the next round. Repeat for Rounds 2 and 3.

**5.4.6 Timer Behavior**

- The round timer is visible to all students as a countdown (e.g., "8:32 remaining").
- At configurable thresholds (e.g., 2 minutes, 30 seconds), the timer display changes color or shows a warning.
- When the timer reaches zero, submissions are locked for that round. Groups that have not submitted receive default terms.
- The instructor can extend the timer during a round if needed.

### 5.5 Counterpart Abstraction

The system treats the counterpart as a pluggable component. The negotiation flow, term sheet form, scoring rubric, and leaderboard work identically regardless of whether the counterpart is AI or human.

| Aspect | Human-AI | Human-Human |
|--------|----------|-------------|
| Counter-offer source | AI generates structured response | Other group submits structured term sheet |
| Counter-offer display | AI response format (accept/counter/reject per term + narrative) | Same format, but values come from the human counterpart; AI generates the accept/counter/reject evaluation and narrative based on comparing both sides' submissions |
| Scoring | AI scores the student's submission | AI scores both sides' submissions against their respective role's objectives |
| Narrative feedback | AI writes in-character narrative | AI generates an observer-perspective narrative analyzing the exchange between both sides |
| Walkaway | AI can trigger walkaway based on persona thresholds | No walkaway in HH mode — both sides must complete all rounds |

### 5.6 Scoring System

**5.6.1 Objective Rubric**

Unchanged from v1.0 for the student role (smaller brand). The same four components apply: Economic Value (40%), Strategic Alignment (30%), Relationship Preservation (20%), Information Management (10%).

**5.6.2 Partner Role Scoring**

Groups playing the partner role (larger brand) in HH mode are scored on a parallel rubric reflecting the larger brand's objectives:

| Component | Weight | Measurement |
|-----------|--------|-------------|
| Brand Protection | 40% | Did the partner retain creative control, protect brand equity, and avoid undervaluing the partnership? |
| Deal Economics | 30% | Revenue split and financial terms relative to the larger brand's optimal range. |
| Strategic Value | 20% | Did the agreed terms serve the larger brand's briefing objectives (e.g., shorter commitment, renewal option, exclusivity)? |
| Counterpart Management | 10% | Did the partner extract useful information about the smaller brand's priorities while protecting their own? |

**5.6.3 Score Calculation**

- Unchanged from v1.0 for individual scoring mechanics (round weights 25%/35%/40%, composite 0–100).
- In group mode, all members of a group receive the same score.
- In HH mode, both groups in a pair receive scores — each evaluated against their own role's rubric.
- Homework and class session scores are averaged independently on their respective leaderboards.

### 5.7 Leaderboard

**5.7.1 Dual Leaderboards**

Each scenario has two separate leaderboards:

- **Homework leaderboard:** Individual students, Human-AI attempts only. Identical to v1.0.
- **Class session leaderboard:** Groups (or individual students within groups), Human-Human and Human-AI attempts. Updated after each class session completes.

The leaderboard screen uses tabs to toggle between the two. Cross-section competition (from v1.0) applies within each leaderboard independently.

**5.7.2 HH and HA on the Same Class Leaderboard**

In mixed-mode class sessions, HH and HA group scores appear on the same class session leaderboard. The counterpart type (HH or HA) is tagged on each entry but does not affect ranking. This is a known design tradeoff: HH scores are influenced by opponent quality while HA scores are not. For the research experiment, this data is analyzed separately; for the student-facing leaderboard, they are combined for simplicity.

### 5.8 Instructor Features (v1.2)

All v1.0 instructor features carry forward. The following are added:

- **Group management:** Create, edit, and delete groups. Assign students to groups. Designate group leads.
- **Session management:** Create class sessions, configure counterpart mode, set round duration, manage pairings, run the session (start/advance/end rounds), pause/extend timer.
- **Session history:** View past class sessions with results, group pairings, and scores.
- **Pairing review:** Before starting a session, review and override auto-generated HH pairings and role assignments.
- **Odd group resolution:** System flags unpaired groups; instructor assigns them to AI or makes alternative arrangements.
- **Export by mode:** Export homework scores and class session scores as separate CSVs.
- **Research tagging:** Each attempt is tagged with counterpart type (HH or HA) and session ID, enabling filtered analysis for the research experiment.

---

## 6. Data Model

The following tables are **new or modified** for v1.2. All v1.0 tables remain, with modifications noted.

### 6.1 New Tables

| Table | Purpose | Key Fields |
|-------|---------|------------|
| NegotiationGroup | A team of students for class sessions | id, orgId, name, scenarioId, createdBy, createdAt |
| GroupMember | Membership in a group | id, groupId, userId, isLead (boolean), joinedAt |
| ClassSession | An instructor-created in-class session | id, orgId, scenarioId, counterpartMode (ALL_HH / ALL_HA / MIXED), roundDurationMinutes, status (DRAFT / ACTIVE / COMPLETED), currentRound, createdBy, startedAt, completedAt |
| SessionPairing | Pairing of groups within a session | id, sessionId, studentGroupId, partnerGroupId (nullable — null if HA), counterpartType (HH / HA), studentRole, partnerRole |
| RoundTimer | Timer state for active session rounds | id, sessionId, roundNumber, startedAt, durationSeconds, pausedAt, extendedSeconds |

### 6.2 Modified Tables

| Table | Changes |
|-------|---------|
| Attempt | Add fields: `activityMode` (HOMEWORK / CLASS_SESSION), `sessionId` (nullable FK to ClassSession), `groupId` (nullable FK to NegotiationGroup), `counterpartType` (AI / HUMAN), `role` (STUDENT_ROLE / PARTNER_ROLE) |
| Round | Add field: `submissionDeadline` (timestamp, set from timer in class mode; null in homework mode) |
| Submission | Add field: `submittedByUserId` (the group lead who submitted; same as userId in individual mode) |
| LeaderboardEntry | Add field: `activityMode` (HOMEWORK / CLASS_SESSION) — enables separate leaderboard queries |
| AttemptScore | No structural changes; scoring logic is role-aware |

---

## 7. API Endpoints

All v1.0 endpoints remain. The following are **new or modified** for v1.2.

### 7.1 Groups

| Method | Path | Role | Description |
|--------|------|------|-------------|
| POST | `/strategy/groups` | Admin | Create a group |
| GET | `/strategy/groups` | Admin | List groups for the org |
| GET | `/strategy/groups/:id` | User+ | Get group details and members |
| PATCH | `/strategy/groups/:id` | Admin | Update group (name, lead) |
| DELETE | `/strategy/groups/:id` | Admin | Delete a group |
| POST | `/strategy/groups/:id/members` | Admin | Add members to a group |
| DELETE | `/strategy/groups/:id/members/:userId` | Admin | Remove a member |
| POST | `/strategy/groups/auto-assign` | Admin | Auto-assign students to groups of specified size |

### 7.2 Class Sessions

| Method | Path | Role | Description |
|--------|------|------|-------------|
| POST | `/strategy/sessions` | Admin | Create a class session (draft) |
| GET | `/strategy/sessions` | Admin | List sessions for the org |
| GET | `/strategy/sessions/:id` | User+ | Get session details, pairings, status |
| PATCH | `/strategy/sessions/:id` | Admin | Update session config (before starting) |
| POST | `/strategy/sessions/:id/generate-pairings` | Admin | Auto-generate HH pairings |
| PATCH | `/strategy/sessions/:id/pairings/:pairingId` | Admin | Override a pairing |
| POST | `/strategy/sessions/:id/start` | Admin | Start the session (moves from DRAFT to ACTIVE, begins Round 1) |
| POST | `/strategy/sessions/:id/advance-round` | Admin | Close current round, open next |
| POST | `/strategy/sessions/:id/end` | Admin | End the session, trigger final scoring |
| POST | `/strategy/sessions/:id/timer/pause` | Admin | Pause the round timer |
| POST | `/strategy/sessions/:id/timer/resume` | Admin | Resume the round timer |
| POST | `/strategy/sessions/:id/timer/extend` | Admin | Add time to the current round |

### 7.3 Session Status (Polling)

| Method | Path | Role | Description |
|--------|------|------|-------------|
| GET | `/strategy/sessions/:id/status` | User+ | Current round, timer remaining, submission statuses (polled by clients) |

### 7.4 Modified Endpoints

| Endpoint | Change |
|----------|--------|
| `POST /strategy/scenarios/:id/attempts` | New optional fields: `sessionId`, `groupId`. If `sessionId` is provided, the attempt is class session mode |
| `POST /strategy/rounds/:id/submit` | In class session mode, validates that the submitting user is the group lead; enforces round timer deadline |
| `GET /strategy/scenarios/:id/leaderboard` | New query param `mode=homework\|class` to filter by activity mode |
| `GET /strategy/scores/export` | New query param `mode=homework\|class` to export by activity mode |

---

## 8. User Interface Screens

### 8.1 Modified Screens

| Screen | Changes |
|--------|---------|
| Scenario Dashboard | Two entry points per scenario: "Practice on Your Own" and "Join Class Session" |
| Negotiation — Term Sheet | In group mode: read-only for non-lead members with "Lead is submitting" indicator. In class mode: round timer countdown visible at top |
| Negotiation — AI Response | In HH mode: shows human counterpart's offer in the same format, with AI-generated evaluation overlay |
| Leaderboard | Tabs for Homework and Class Session leaderboards. Class leaderboard shows group names/aliases and tags HH/HA |
| Instructor — Config | Extended with group management and session management |

### 8.2 New Screens

| Screen | Route | Description |
|--------|-------|-------------|
| Group Management | `/strategy/admin/groups` | Create, edit, delete groups; assign students; designate leads |
| Session Setup | `/strategy/admin/sessions/new` | Configure a class session: select scenario, counterpart mode, round duration, assign groups |
| Pairing Review | `/strategy/admin/sessions/:id/pairings` | Review auto-generated pairings; override assignments; resolve odd groups |
| Session Control | `/strategy/admin/sessions/:id/control` | Live instructor dashboard: round status, timer controls, submission tracker, advance/end buttons |
| Session History | `/strategy/admin/sessions` | List of past sessions with results |
| Partner Role Briefing | `/strategy/sessions/:id/briefing` | Confidential briefing for groups assigned the partner role (larger brand) |
| Session Waiting Room | `/strategy/sessions/:id/lobby` | Students see their group, role assignment, and counterpart type while waiting for instructor to start |

---

## 9. Non-Functional Requirements

### 9.1 Performance

- All v1.0 performance targets apply.
- Session status polling: Clients poll every 3–5 seconds during active class sessions. Target < 200ms response time for the status endpoint.
- Timer accuracy: Visible countdown should be within ±2 seconds of server time.

### 9.2 Scalability

- v1.2 must support a full class of 30–60 students (10–15 groups of 4–6) in a single synchronous session.
- Concurrent polling from 30–60 clients at 3–5 second intervals = 12–20 requests/second to the status endpoint. This is well within Express capacity but should be load-tested.

### 9.3 Security

- All v1.0 security measures apply.
- Partner role briefing (confidential persona card) is only served to groups assigned the partner role. Students assigned the student role cannot access it.
- Group submissions are validated server-side: only the designated lead's userId is accepted for the submit endpoint in group mode.

### 9.4 Data Integrity

- All v1.0 data integrity rules apply.
- Session state transitions are atomic (DRAFT → ACTIVE → COMPLETED; no skipping).
- Round advancement is server-authoritative — clients cannot advance rounds; only the instructor's endpoint triggers advancement.
- Timer state is server-side; client countdowns are display-only and sync via polling.

### 9.5 Data Retention

Unchanged from v1.0 — persistent retention for all data. Class session records, pairings, and group assignments are retained alongside attempt data.

### 9.6 Availability

Unchanged from v1.0.

---

## 10. Environment Configuration

No new environment variables required for v1.2. All v1.0 variables carry forward. The session polling interval could be configurable but defaults are acceptable for MVP.

---

## 11. Scoring Calibration

The v1.0 calibration process (Phase 1: strategy differentiation, Phase 2: consistency check) applies to both the student role and the partner role scoring rubrics. The partner role rubric should be independently calibrated using the same two-phase process.

Additionally, for research validity: run at least 3 matched test scenarios where the same term sheet sequence is evaluated in both HA mode (AI generates counter-offers) and HH mode (a TA manually submits counter-offers mimicking the AI's strategy). Compare scores to verify that the AI evaluator produces comparable scoring regardless of counterpart source.

---

## 12. Research Experiment Support

The v1.2 data model and configuration are designed to support a cluster-randomized controlled experiment comparing Human-AI and Human-Human negotiation conditions.

### 12.1 Condition Assignment

The instructor's counterpart mode configuration (ALL_HH, ALL_HA, or MIXED) maps directly to experimental conditions. In MIXED mode, random assignment of groups to HH or HA provides within-session randomization. Section-level assignment (all groups in one section get HH, another section gets HA) provides cluster-level randomization.

### 12.2 Data Tagging

Every attempt record includes:

- `counterpartType` (AI / HUMAN) — the experimental condition
- `sessionId` — links to the specific class session
- `activityMode` (HOMEWORK / CLASS_SESSION) — distinguishes practice from experimental data
- `role` (STUDENT_ROLE / PARTNER_ROLE) — which side of the negotiation

This enables filtered queries for research analysis: select all class session attempts, segment by counterpart type, control for session and section.

### 12.3 Data Export for Research

The instructor CSV export supports filtering by activity mode and counterpart type, producing datasets suitable for the planned multilevel regression analysis. De-identification (replacing user IDs with anonymous keys) can be applied at export time.

---

## 13. Scope Boundary

### 13.1 In Scope (v1.2)

- Homework mode (existing v1.0 behavior, relabeled).
- Class session mode with instructor-paced rounds and timed countdowns.
- Group creation, management, and lead designation.
- Human-Human counterpart pairing with role assignment (student role / partner role).
- Mixed counterpart configuration (some groups HH, some HA, within one session).
- AI as evaluator in HH mode (scores both sides per round).
- Partner role briefing and scoring rubric.
- Instructor session dashboard with real-time status, timer controls, and round advancement.
- Pairing review and override.
- Odd group handling (instructor decision).
- Separate homework and class session leaderboards.
- Research data tagging (counterpart type, session ID, activity mode, role).
- Polling-based real-time updates for class sessions.

### 13.2 Out of Scope (Deferred)

| Feature | Target Phase |
|---------|-------------|
| Scenarios 2 and 3 (Retail Shelf Space, Media Buy) | Phase 2 |
| Functional sequential scenario unlocking | Phase 2 |
| Narrative interconnection between scenarios | Phase 2 |
| Adaptive AI difficulty (distinct behavior for practice vs. graded) | Phase 2 |
| Free-text conversation layer | Phase 3 |
| Transcript export for post-negotiation reflections | Phase 2 |
| Full instructor dashboard (analytics, per-student drill-down) | Phase 2 |
| Aggregate cross-scenario leaderboard | Phase 3 |
| WebSocket-based real-time (upgrade from polling) | Phase 2 if needed |
| In-app group chat for team coordination | Phase 3 |
| Asynchronous Human-Human mode | Phase 3 |

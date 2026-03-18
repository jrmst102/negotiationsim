# Instructions for Claude — Negotiation Simulation UI (Frontend Only)

## Objective

Build the frontend UI for a Competitive Strategy Negotiation Simulation. This is a standalone React application that consumes three published npm packages from the `@jrmst102` scope on GitHub Packages. The backend API does not exist yet — build the UI with mock data and placeholder API calls that can be wired up later.

## Installed packages available to import

### `@jrmst102/auth-client`

Auth SDK. Exports:

- `AuthProvider` — React context provider, wrap the app root
- `ProtectedRoute` — Route guard, renders `<Outlet>` if authenticated
- `RequireRole` — Role guard for route nesting; takes a `role` prop and renders `<Outlet>` if allowed. Use as a route wrapper, not inline around arbitrary JSX.
- `useAuth()` — Returns `{ user, login, logout, isAuthenticated, isLoading, error }`
- `usePermissions()` — Returns `{ effectiveApps, canAccess(appId), hasRole(role) }`
- `useTeam()` — Team context hook
- `apiClient` — Pre-configured Axios instance with JWT refresh
- `setAccessToken`, `getAccessToken` — Manual token management
- Types: `User`, `AuthState`, `AuthContextValue`, `PermissionsContextValue`

### `@jrmst102/ui-kit`

Component library. Exports:

- `AppShell` — Layout shell with HeaderBar + SidebarNav + Outlet. No props.
- `Button` — Props: `variant` (primary/secondary/ghost/danger), `size` (sm/md/lg), `loading` (boolean)
- `Card` — Props: `header` (ReactNode), `footer` (ReactNode)
- `Input` — Props: `label`, `error`, `helpText` + standard input attrs
- `Select` — Props: `label`, `error`, `options: { value, label }[]` + standard select attrs
- `Modal` — Props: `isOpen`, `onClose`, `title`, `children`
- `Table<T>` — Props: `columns: { key, header, render? }[]`, `data: T[]`, `keyField`, `className`
- `Tabs` — Props: `tabs: { id, label, content }[]`, `defaultTab`, `className`
- `Badge` — Props: `variant` (default/success/warning/error/info)
- `Spinner` — Props: `size` (sm/md/lg), `className`
- `Toast` — Props: `message`, `type` (success/error/info/warning), `duration`, `onClose`
- Also available: `Avatar`, `HeaderBar`, `SidebarNav`

### `@jrmst102/shared-config`

Constants. Exports:

- `ROLE_HIERARCHY` — `['user', 'lead', 'admin', 'super_admin']`
- `APP_IDS` — Object with app identifier constants
- `ALL_APP_IDS` — Array of all app IDs
- `APP_LABELS` — Display labels per app
- `APP_ROUTES` — Route paths per app
- `AUTH_API` — Object with auth endpoint paths
- `ORGS_API` — Object with org endpoint paths

## Tech stack

- React 18, Vite, TypeScript strict mode, Tailwind CSS 3
- React Router v6 for routing
- No additional component libraries — use `@jrmst102/ui-kit` components and build custom components with Tailwind

## What to build

Build the following screens as React pages/components. Use mock data (hardcoded JSON or local state) for all data. Create an `api/` directory with stub functions that return mock data wrapped in Promises — these will be replaced with real `apiClient` calls later.

### Screen 1: Scenario Dashboard (`/strategy`)

- Display three scenario cards in a responsive grid.
- Card 1 (Brand Partnership): Active. Show scenario name, description ("Brand Partnership / Co-Branding Deal"), student status (Not Started / In Progress / Completed), best score, number of attempts, and a "Start" or "Continue" button.
- Card 2 (Retail Shelf Space): Locked. Show a lock icon overlay, title, brief description, and "Coming Soon" badge. Not clickable.
- Card 3 (Media Buy): Locked. Same as Card 2.
- Use `Card` and `Badge` from ui-kit.

### Screen 2: Mode Selection Modal

- When clicking "Start" on an active scenario, show a `Modal` with two options: Practice mode and Graded mode.
- Each option shows a title, short description (Practice: "Scores recorded but don't count toward leaderboard" / Graded: "Scores count toward leaderboard and competitive benchmark").
- A "Begin Negotiation" button confirms the selection and navigates to the negotiation screen.

### Screen 3: Negotiation — Briefing (`/strategy/attempts/:id/rounds/:n`)

- Full-width content area showing the round briefing narrative.
- Round indicator at the top showing "Round 1 of 3" (or 2/3).
- Read-only formatted text (2–3 paragraphs of scenario context).
- A "Proceed to Negotiation" button at the bottom.
- Use `Card` for the briefing container.

### Screen 4: Negotiation — Term Sheet (`/strategy/attempts/:id/rounds/:n/negotiate`)

This is the core form. Build a structured form with these 8 fields for the Brand Partnership scenario:

1. Revenue Split (student %) — Range slider, 20%–80%, show current value
2. Creative Control — Dropdown: Student Approval / Joint Approval / Partner Approval
3. Campaign Duration — Numeric input, 3–24 months
4. Exclusivity Window — Numeric input, 0–12 months
5. Brand Prominence — Dropdown: Co-equal / Student Lead / Partner Lead
6. Performance Benchmark (target CAC reduction) — Range slider, 5%–50%
7. Minimum Guaranteed Impressions — Numeric input, 100K–5M (format with K/M suffix)
8. Exit Clause Trigger — Dropdown: No Exit / 30-day Notice / Performance-based / Mutual Agreement

- Use `Input` and `Select` from ui-kit where appropriate. Build a custom slider component with Tailwind for the range sliders.
- Group fields into sections: "Financial Terms", "Creative & Brand", "Performance & Exit".
- Show a "Submit Offer" button at the bottom. Clicking it shows a loading spinner and then navigates to the AI response screen.
- If this is a revision (after seeing AI response), pre-populate the form with the student's last submission. Show a "Previous AI Feedback" collapsible summary at the top.

### Screen 5: Negotiation — AI Response (`/strategy/attempts/:id/rounds/:n/response`)

- Display the AI's counter-offer term by term.
- For each of the 8 fields, show: field name, student's submitted value, AI's evaluation status (Accept / Counter / Reject as a colored badge), counter-value (if countered), and a one-line reasoning.
- Use `Badge` with variant success for Accept, warning for Counter, error for Reject.
- Below the terms, show the AI's narrative response (2–3 paragraphs in character) in a styled quote block or card.
- Show deal status as a prominent indicator: "Close to Agreement" (green), "Far Apart" (yellow), "Walkaway Risk" (red), "Walkaway" (red, full width alert).
- Show three action buttons: "Revise Offer" (goes back to term sheet with values pre-filled), "Accept Counter-Offer" (accepts AI's terms), "Lock In My Offer" (keeps student's last terms).
- If walkaway triggered, hide the action buttons and show a message explaining the breakdown with a "Continue to Next Round" button.

### Screen 6: Round Summary (`/strategy/attempts/:id/rounds/:n/summary`)

- Show the final agreed terms for the round in a clean table.
- Show per-round score breakdown: Economic Value, Strategic Alignment, Relationship Preservation, Information Management — each as a labeled progress bar (0–100) with the score value.
- If not the final round, show a "Proceed to Round X" button.
- If the final round, show "View Final Results" button.

### Screen 7: Attempt Results (`/strategy/attempts/:id/results`)

- Show the final composite score prominently (large number, 0–100, with a circular progress or gauge visualization).
- Break down score by round (Round 1 / 2 / 3) with weights shown (25% / 35% / 40%).
- Break down score by rubric component (Economic Value 40%, Strategic Alignment 30%, Relationship Preservation 20%, Information Management 10%).
- Show buttons: "View Leaderboard", "Try Again", "Back to Dashboard".

### Screen 8: Leaderboard (`/strategy/scenarios/:id/leaderboard`)

- Use `Table` from ui-kit.
- Columns: Rank, Alias, Average Score, Attempts, Percentile.
- Mock 10–15 rows with fun aliases (Adjective + Noun pattern: "Steel Falcon", "Coral Strategist", "Iron Compass", etc.).
- Highlight the current student's row with a distinct background color.
- Students with no completed attempts appear at the bottom as "In Progress" with dashes for score and percentile.
- Use `Tabs` to toggle between "My Scores" and "Leaderboard".

### Screen 9: Instructor Scores View (`/strategy/admin/scores`)

- Only visible to users with admin role. Use `RequireRole` with `role="admin"` as a route wrapper.
- `Table` showing all students: Real Name, Alias, Average Score, Attempts, Percentile.
- An "Export CSV" button (mock: just show a toast saying "CSV downloaded").
- Scenario config toggles: lock/unlock scenario, practice/graded mode toggles. Use simple toggle switches built with Tailwind.

## Routing structure

Wrap all `/strategy/*` routes inside `ProtectedRoute`. For admin routes, nest them inside `RequireRole` with `role="admin"`. The app should work within the `AppShell` layout (HeaderBar + SidebarNav + content area).

```
/strategy                                    → Scenario Dashboard
/strategy/attempts/:id/rounds/:n             → Briefing
/strategy/attempts/:id/rounds/:n/negotiate   → Term Sheet
/strategy/attempts/:id/rounds/:n/response    → AI Response
/strategy/attempts/:id/rounds/:n/summary     → Round Summary
/strategy/attempts/:id/results               → Attempt Results
/strategy/scenarios/:id/leaderboard          → Leaderboard
/strategy/scores                             → My Scores (tab within leaderboard)
/strategy/admin/scores                       → Instructor Scores (RequireRole admin)
/strategy/admin/config                       → Instructor Config (RequireRole admin)
```

## Mock data structure

Create TypeScript interfaces in a `types/` directory matching these shapes, then create mock data that conforms to them:

- `Scenario` — id, name, slug, description, status (ACTIVE/LOCKED), order
- `Attempt` — id, scenarioId, mode (PRACTICE/GRADED), status (IN_PROGRESS/COMPLETED/ABANDONED), startedAt, completedAt
- `Round` — id, attemptId, roundNumber, status, briefing (string)
- `Submission` — id, roundId, submissionNumber, terms (object), aiResponse (object)
- `AIResponse` — terms (per-field: status/counterValue/reasoning), narrative, dealStatus, trustDelta
- `AttemptScore` — economicValue, strategicAlignment, relationshipPreservation, infoManagement, compositeScore
- `LeaderboardEntry` — rank, alias, averageScore, attemptCount, percentile, isCurrentUser

## Design guidelines

- Use Tailwind utility classes. Follow a clean, professional aesthetic.
- Color palette: blue-600 for primary actions, gray tones for backgrounds and borders, green/yellow/red for status indicators.
- Typography: use Tailwind's default font stack. Headings in semibold/bold, body in regular.
- Spacing: consistent padding (p-4/p-6) and gaps (gap-4/gap-6).
- The negotiation screens are the core experience — they should feel polished and focused, not cluttered.

## What NOT to build

- No backend, no API server, no database.
- No authentication pages (login/register) — those exist in the UMS app.
- No real AI integration — mock the AI responses.
- No free-text chat interface — the negotiation is form-based only.

# Task: Enhanced Kantorku Components

## Summary
Rewrote and enhanced 5 major Kantorku components following cyberpunk design rules with dark theme, glass morphism, tiny text, and comprehensive features.

## Changes Made

### 1. `src/lib/kantorku/workers-data.ts`
- Added missing `team_consult` and `failed` states to `CONTRACT_STATE_LABELS`
- Added new `CONTRACT_STATE_COLORS` mapping for all 11 contract states

### 2. `src/components/kantorku/DashboardZone.tsx` (REWRITE)
- **Overview Tab**: 6 key metrics (Total Cost, Total Tokens, Events, Avg Latency, Success Rate, Active Workers), Cost by Model bar chart, Cost by Worker bar chart (NEW), Token usage chart, Worker status pie chart, Squad distribution horizontal bar, Event type distribution bar, Latency history line chart (NEW), Sessions list, Metrics summary card
- **Observability Tab**: Recent traces list with filter (ok/error/timeout), expandable trace details, Middleware pipeline visualization showing each step's name, type, status, duration
- **Infrastructure Tab**: Health status with providers, Circuit breakers, Approval gates list, Escalations list (unresolved highlighted), Bulletin board (active entries), SOP rules, Worker infrastructure summary

### 3. `src/components/kantorku/LobbyZone.tsx` (REWRITE)
- Full contract lifecycle with all 11 states
- Intake result display with estimated workers and duration
- Team consult feedback section
- Approval gates section (team_review state)
- Debrief summary (done state) with duration/cost stats
- New session button
- handleSendMessage: processes manager_message, contract_ready, and team_consult types
- handleAccept: sets up DAG, middleware, approval gates, traces, latency, debrief, metrics
- Creates/updates sessions on contract flow

### 4. `src/components/kantorku/ChatPanel.tsx` (ENHANCE)
- **ClientChatPanel**: Search bar with message filtering, SimpleMarkdown renderer (bold, code blocks, inline code, bullet points), timestamp per message, animated typing indicator, New Session button, Search toggle button
- **WorkersChatPanel**: Filter dropdown for message types, reply-to threading with referenced content preview, timestamp per message, squad color badges, message count display

### 5. `src/components/kantorku/ContractCard.tsx` (ENHANCE)
- Priority badges on todos (low/medium/high/critical with icons)
- Dependency arrows showing which todo depends on which
- Actual time tracking (estimated vs actual with color coding)
- Approval gates section with status indicators
- Team approval status with individual worker votes
- Budget indicator with progress bar
- Revision history count with version badge
- Progress bar with percentage
- Blocked todo status styling

### 6. `src/components/kantorku/SettingsDialog.tsx` (ENHANCE)
- API key input (existing)
- Backend URL input for Python backend
- Connection test button (calls /api/health) with status indicator
- Theme toggle (UI only, always dark)
- Connection status display
- Clear data button (with confirmation)
- Export data button (downloads localStorage as JSON)
- Version display (v0.4.0)
- About section with 6 framework features

### 7. `src/app/globals.css`
- Added typingBounce keyframe animation for typing indicator

## Verification
- Lint passes: `bun run lint` - no errors
- Dev server: Page loads with 200 status
- All components properly typed with TypeScript
- All imports from correct paths

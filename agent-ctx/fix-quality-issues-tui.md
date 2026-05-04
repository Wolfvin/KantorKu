# Task: Fix Top Quality Issues in KantorKu TUI

## Changes Made

### 1. Make WorkersLiveStream Scrollable
- **Approach**: VerticalScroll wrapper (recommended simpler approach)
- Wrapped `WorkersLiveStream` in a `VerticalScroll(id="workers-scroll")` in `compose()`
- Added CSS `#workers-scroll { height: 1fr; }` in the theme builder
- WorkersLiveStream remains a `Static` — the VerticalScroll container handles scrolling

### 2. Extract Event Rendering Dispatch Dict
- Created module-level `EVENT_RENDERERS: dict[str, Any]` dict
- Created `_register_event_renderer(event_type)` decorator for clean registration
- Extracted all 38 event type renderers into individual `@_register_event_renderer`-decorated functions
- Covers: briefing_opened, plan_drafted, plan_revised, revision_requested, manager_brainstorming, worker_speak_up, worker_dm, worker_broadcast, task_assigned, task_started, task_done, task_failed, task_recovered, task_timeout, context_fetch_start, context_fetch_done, verify_design_start, verify_design_done, verify_engineer_start, verify_engineer_done, error_logged, skill_updated, llm_stream_start, llm_stream_chunk, llm_stream_done, contract_accepted, delegation_request, delegation_result, checkpoint_saved, crash_recovered, circuit_open, circuit_closed, rate_limit_hit, cost_warning, worker_hired, worker_fired, middleware_before, middleware_after
- Note: `middleware_before` and `middleware_after` are now separate renderers (was previously combined in a single elif)
- Note: `context_fetch_start` and `context_fetch_done` are now separate renderers (was previously combined)
- Replaced the 250-line if/elif chain in `_render_stream()` with a clean 4-line dispatch:
  ```python
  renderer = EVENT_RENDERERS.get(event_type)
  if renderer:
      result = renderer(e)
      if result:
          parts.append(result)
  ```
- System messages still render inline (not in the dispatch dict) since they use a different pattern

### 3. ContractState Enum
- Added `from enum import Enum` import
- Created `ContractState(str, Enum)` class with all 13 lifecycle states
- Extends `str, Enum` for full backward compatibility: `ContractState.IDLE == "idle"` is `True`
- Replaced key string literals with enum values in:
  - `parse_nl_action()` — state comparisons
  - `_update_action_buttons()` — state comparisons
  - `_update_input_placeholder()` — dict keys
  - `_update_subtitle()` — dict keys
  - `_update_action_hints()` — dict keys
  - `_update_lifecycle_breadcrumb()` — dict keys
  - `ContractDisplay._render()` — state comparisons
  - `action_accept_contract()` — state comparison
  - `action_revise_contract()` — state comparison
  - `_do_disrupt()` — state comparison
  - `action_cancel_input()` — state comparison
  - `_process_input_text()` — state comparison
  - `_set_contract_state()` — thinking indicator comparison

### 4. Thinking Spinner/Animation
- Created `ThinkingIndicator(Static)` widget with:
  - Pulsing spinner animation: ◐ → ◓ → ◑ → ◒ rotating at 250ms intervals
  - `start(message)` method: shows the widget and begins animation
  - `stop()` method: hides the widget and stops animation
  - CSS with `display: none` (hidden by default), `color: yellow`, `text-style: bold`
- Placed in the left panel between the manager log and the disrupt button
- Wired into `_set_contract_state()`:
  - When state is `ContractState.MANAGER_THINKING`, indicator starts with "Manager thinking"
  - For any other state, indicator stops
- Uses Textual's `set_interval()` for the animation timer
- Properly cleans up timer on `stop()`

## Verification
- Python syntax check: PASSED
- Module import check: PASSED
- ContractState enum equality check: PASSED (str, Enum backward compatible)
- EVENT_RENDERERS count: 38 (all expected event types registered)
- Dict lookup with string keys on ContractState-keyed dicts: PASSED
- ThinkingIndicator extends Static: PASSED
- Spinner chars correct: PASSED

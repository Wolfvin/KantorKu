# Task 6 — Settings Screen for KantorKu TUI

## Summary
Rewrote `settings_screen.py` from a 4-tab layout to a 3-column layout matching the spec, and updated the `/settings` command.

## Files Modified
- `/home/z/my-project/framework/kantorku/tui/settings_screen.py` — Complete rewrite (was 1841 lines, now ~860 lines)
- `/home/z/my-project/framework/kantorku/tui/commands.py` — Updated `await tui.push_screen()` in cmd_settings

## Key Changes

### settings_screen.py
- **Layout**: 3-column (sidebar | center tabs | preview panel) instead of 4-tab
- **Left sidebar**: Worker list with ListView + New Worker / Delete Worker buttons
- **Center tabs**: 3 tabs — "System Prompt" (SKILL.md), "Tools & API" (API config + allowed_tools + available tools reference), "Skills" (allowed_skills + add skill file)
- **Right panel**: Live preview showing current worker state (API, tools, skills, SKILL.md preview)
- **CRUD**: Create (dir + plugin.json + SKILL.md), Read (from_directory), Update (to_plugin_json), Delete (shutil.rmtree)
- **Hot-reload**: registry.reload_worker() in embedded mode, fallback to register_identity()
- **Backup**: _backup_file() creates timestamped .bak files before overwrite
- **All CSS**: Uses KANTORKU_THEME references (no hardcoded hex)
- **Error handling**: Inline error messages, skip bad workers with warning, PermissionError catch

### commands.py
- Updated `/settings` command to use `await tui.push_screen(SettingsScreen(tui))`

## Testing
- All imports verified (no circular dependencies)
- WorkerIdentity.to_plugin_json() and to_dict() verified
- Integration test: 13 workers loaded, 0 skills loaded, AVAILABLE_TOOLS list correct
- SettingsScreen instantiation verified
- No hardcoded hex values in source CSS

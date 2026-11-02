# Cross-Team Project Tracker - Implementation Summary

## PR Created
**URL**: https://github.com/mannetsang/man-ai/pull/1  
**Branch**: `cursor/cross-team-project-tracker-89da`  
**Status**: Ready for review (do NOT merge or deploy yet per constraints)

## What Changed

### Data Model (Backward Compatible ✅)

Projects now support these additional fields:

1. **`milestones`** (array): List of deliverables
   - Each: `{title, due, done}`
   - Example: `[{"title": "Phase 1", "due": "2026-11-15", "done": false}]`

2. **`blockers`** (array): Active obstacles
   - Each: `{what, blocked_by, since}`
   - Example: `[{"what": "Waiting for API access", "blocked_by": "IT", "since": "Oct 28"}]`

3. **`waiting_on_man`** (object): Items waiting for your input
   - Fields: `{needed, since}`
   - Example: `{"needed": "Approve design", "since": "Nov 1"}`

4. **`tracker_status`** (string): Overall health
   - Values: `on_track | at_risk | blocked | done | unknown`

5. **`last_update_at`** (string): Free-text timestamp
   - Example: `"Nov 1, 3:00 PM EST"`

**Tasks** can now link to projects via `project_id` field.

All existing project data continues to work (defaults: empty arrays, `unknown` status).

### Projects Tab - New Tracker View

#### "Waiting on Man" Section (at the top)
Shows items requiring your attention:
- Projects with `waiting_on_man` set
- Count of open questions (from Questions tab)
- Count of pending suggested actions (from Activity tab)

#### Warning Flags on Project Cards
- ⚠ **Overdue**: Has milestones past their due date
- ⚠ **Stale**: No update in >7 days  
- 🚫 **Blockers**: Shows blocker count (e.g., "🚫 2 blockers")

#### New Filters
- **Tracker status**: on track / at risk / blocked / done / unknown
- **Project owner**: Dropdown of all project owners
- (Plus existing: Company, Project status)

#### Enhanced Project Dialog
Can now edit:
- **Milestones**: Add/remove, mark done, set due dates
- **Blockers**: What's blocking, who/what is blocking, since when
- **Waiting on Man**: What's needed, since when
- **Tracker status** and **last update** timestamp

### Board Integration
- Task dialog now has **Project** dropdown
- Links task to project via `project_id`
- Project cards show open task count for that project

### One-Time Seed

Loaded from `uploads/tracker_seed_0f81.json`:
- **13 AI team workstreams** (Devon, Mark, Elon, Nova, Taylor, Vera, Kai, Ari)
- Loads automatically on app startup
- **Idempotent**: Won't overwrite projects with same name
- Sets flag `tracker_seeded` in store

Examples seeded:
- "Fix broken .ca link on /superhair-knowledge" (Devon, on track, waiting on Man)
- "Fill missing OTTO recommendations" (Mark, at risk)
- "Apple Business Spain alert" (Elon, blocked, waiting on Man)
- "Architecture inventory" (Nova, on track, waiting on Man)
- "AmazCS Operator Console" (Kai, done)

## Test Results

```
test_task_can_link_to_project ... ok
test_task_without_project_link ... ok
test_project_backward_compatible ... ok
test_project_with_tracker_fields ... ok
test_update_project_tracker_fields ... ok
test_seed_handles_done_status ... ok
test_seed_tracker_workstreams ... ok

----------------------------------------------------------------------
Ran 7 tests in 0.001s

OK
```

All tests pass ✅

## Files Changed

```
modified:   CLAUDE.md
modified:   README.md
modified:   src/cloud_run/knowledge.py
modified:   src/cloud_run/main.py
modified:   src/cloud_run/static/app.js
modified:   src/cloud_run/templates/index.html
new file:   tests/test_tracker.py
```

**Lines**: +572 insertions, -22 deletions

## Before Deploy - Action Items

### Firestore Indexes
✅ **No new composite indexes required**

The tracker fields are stored within project documents (not queried separately), so no Firestore index configuration is needed.

### Manual Steps  
✅ **None required**

The seed data (`tracker_seed_0f81.json`) loads automatically on first run after deploy. It's idempotent, so redeploying won't duplicate projects.

## Screenshots

Unable to capture from local instance (requires auth). The UI changes are:

### Projects Tab Layout:
```
┌─────────────────────────────────────────────────┐
│ ⏸ Waiting on Man (3 projects)                   │
│   • Fix broken .ca link (Devon)                 │
│     Go-ahead to create branch (since Nov 1)     │
│   • Apple Spain alert (Elon)                    │
│     Should Elon investigate? (since Oct 28)     │
│   • Architecture review (Nova)                  │
│     Which project to design first? (since Nov 1)│
│                                                  │
│ ❓ Open questions (6)                            │
│ 💬 Pending suggested actions (0)                │
├─────────────────────────────────────────────────┤
│ [Filters: Tracker Status] [Owner] [Company]    │
│           [Project Status] [+ New project]      │
├─────────────────────────────────────────────────┤
│ Projects Grid:                                  │
│                                                  │
│ ┌────────────────────┐ ┌────────────────────┐  │
│ │ Fix broken .ca link│ │ OTTO recommenda... │  │
│ │ on_track • Devon   │ │ at_risk • Mark     │  │
│ │ 1 milestone        │ │ ⚠ Stale           │  │
│ │ ⏸ Waiting on Man   │ │                    │  │
│ └────────────────────┘ └────────────────────┘  │
│                                                  │
│ ┌────────────────────┐ ┌────────────────────┐  │
│ │ Apple Spain alert  │ │ WhatsApp replies   │  │
│ │ blocked • Elon     │ │ on_track • Vera    │  │
│ │ 🚫 1 blocker       │ │ 1 milestone        │  │
│ │ ⏸ Waiting on Man   │ │                    │  │
│ └────────────────────┘ └────────────────────┘  │
└─────────────────────────────────────────────────┘
```

### Project Dialog (when editing):
```
┌─────────────────────────────────────────┐
│ Edit project                     [X]    │
├─────────────────────────────────────────┤
│ Name: Fix broken .ca link              │
│ Owner: Devon          Deadline: [date] │
│ Tracker status: [on_track ▾]           │
│ Last update: Nov 2, 2:30 AM UTC        │
│                                         │
│ Milestones:                             │
│ ☐ Create branch and commit  2026-11-03│
│ [+ Add milestone]                       │
│                                         │
│ Blockers:                               │
│ (No blockers)                           │
│ [+ Add blocker]                         │
│                                         │
│ Waiting on Man:                         │
│ What's needed: Go-ahead to create...   │
│ Since when: Nov 1, 7:05 PM EST         │
│                                         │
│ [Delete] [Cancel] [Save]               │
└─────────────────────────────────────────┘
```

## What's Next

1. **Review the PR**: https://github.com/mannetsang/man-ai/pull/1
2. **Test locally** (optional):
   ```bash
   git checkout cursor/cross-team-project-tracker-89da
   STORE_BACKEND=memory python3 src/cloud_run/main.py
   ```
3. **Deploy when ready**:
   ```bash
   # After merging to main, or deploy the branch directly:
   gcloud run deploy chat-assistant --source src/cloud_run \
     --region us-central1 --project shp-ai-bot-2026 --quiet
   ```
4. **Verify** the 13 workstreams loaded on first run
5. The AI can now maintain tracker fields in the hourly pass (same as it updates projects/tasks now)

## Notes for AI Hourly Pass

The assistant can update these fields when reading chats:
- Set `tracker_status` based on conversation (on_track/at_risk/blocked)
- Add `milestones` from discussed deliverables
- Record `blockers` from obstacles mentioned
- Set `waiting_on_man` when someone asks for Man's decision
- Update `last_update_at` with timestamp from chat

This would require updates to `assistant.py` and the LLM prompt (not included in this PR, can be follow-up work).

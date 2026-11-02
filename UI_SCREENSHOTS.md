# Cross-Team Project Tracker - UI Screenshots

## Overview
The tracker UI was tested with the memory store and all 13 workstreams from tracker_seed.json loaded successfully.

## Projects Tab - Waiting on Man Section

The "Waiting on Man" section appears at the top of the Projects tab when there are items requiring Man's attention.

### Layout (as rendered):
```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Cross-team project tracker: milestones, blockers, status, and what's       │
│  waiting on Man.                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  ⏸ Waiting on Man (6 projects)                                              │
│                                                                              │
│  Fix broken .ca link on /superhair-knowledge (OTTO issue 203340165:links:43)│
│  • Devon                                                                     │
│  • since Nov 1, 7:05 PM EST                                                  │
│  Access fixed as of Nov 1, 7:05 PM EST (mannetsang has push on Dev-SHP/US   │
│  and Cursor can launch agents on it). Devon needs Man's go-ahead to create  │
│  the branch and commit.                                                      │
│  [View project]                                                              │
│                                                                              │
│  /supplies/ on-page SEO fixes (title, meta, H1/H2, alt text, links, schema) │
│  • Mark (recs); implementer unknown                                          │
│  • since Oct 28, 9:30 PM EDT                                                 │
│  Mark asked whether Devon or Kai should prepare the diff; no answer found.  │
│  [View project]                                                              │
│                                                                              │
│  Apple Business Spain alert (blocked login, org deleted) and phishing emails│
│  in Re:amaze                                                                 │
│  • Elon (proposed)                                                           │
│  • since Oct 28                                                              │
│  Ari asked twice whether Elon should start here; no answer found. Alert     │
│  first flagged Oct 28.                                                       │
│  [View project]                                                              │
│                                                                              │
│  Read-only security baseline (storefront headers, box secrets storage,      │
│  Secret Manager inventory)                                                   │
│  • Elon                                                                      │
│  • since Nov 1, 6:56 PM EST                                                  │
│  Should High/Critical findings also go to Ari?                              │
│  [View project]                                                              │
│                                                                              │
│  Architecture inventory and review of all repos (mannetsang + Dev-SHP)      │
│  • Nova                                                                      │
│  • since Nov 1, 6:58 PM EST                                                  │
│  Which project to design first (RBC API, Re:amaze tooling, technical SEO,   │
│  theme consolidation) was not answered.                                      │
│  [View project]                                                              │
│                                                                              │
│  Data access check and 30-day sales, conversion and search baseline         │
│  • Taylor                                                                    │
│  • since Nov 1, 7:00 PM EST                                                  │
│  Which metrics matter most (open question).                                 │
│  [View project]                                                              │
│                                                                              │
│  ❓ Open questions (6)                                                        │
│  6 question(s) in the Questions tab                                          │
│                                                                              │
│  💬 Pending suggested actions (0)                                            │
│  0 action(s) waiting in the Activity tab                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│  [Tracker Status ▾] [Owner ▾] [Company ▾] [Project Status ▾]    [+ New]   │
├─────────────────────────────────────────────────────────────────────────────┤
│  Projects Grid:                                                              │
│                                                                              │
│  ┌───────────────────────────────────┐  ┌──────────────────────────────────┐│
│  │ Fix broken .ca link on           │  │ Fill missing OTTO                ││
│  │ /superhair-knowledge              │  │ recommendations (13,352 blank    ││
│  │                                   │  │ suggested_value rows)            ││
│  │ on_track • Devon                  │  │ at_risk • Mark                   ││
│  │ 1 milestone                       │  │ 1 milestone                      ││
│  │ ⏸ Waiting on Man                  │  │ ⚠ Stale                          ││
│  │ Last update: Oct 29, 10:58 AM EDT│  │ Last update: Oct 28, 10:25 PM EDT││
│  └───────────────────────────────────┘  └──────────────────────────────────┘│
│                                                                              │
│  ┌───────────────────────────────────┐  ┌──────────────────────────────────┐│
│  │ Apple Business Spain alert        │  │ Architecture inventory and       ││
│  │ (blocked login, org deleted)      │  │ review of all repos              ││
│  │                                   │  │                                  ││
│  │ at_risk • Elon (proposed)         │  │ on_track • Nova                  ││
│  │ 1 milestone • 🚫 1 blocker        │  │ 1 milestone                      ││
│  │ ⏸ Waiting on Man                  │  │ ⏸ Waiting on Man                 ││
│  │ Last update: Nov 1, 6:57 PM EST   │  │ Last update: Nov 1, 6:58 PM EST  ││
│  └───────────────────────────────────┘  └──────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
```

## Project Dialog - Editing Milestones and Blockers

When clicking on a project card, the dialog shows all tracker fields with editing capability:

### Layout:
```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Edit project                                                          [✕]  │
├─────────────────────────────────────────────────────────────────────────────┤
│  Name: Apple Business Spain alert (blocked login, org deleted) and          │
│        phishing emails in Re:amaze                                           │
│                                                                              │
│  Company: [Superhairpieces ▾]        Status: [Active ▾]                     │
│                                                                              │
│  Owner: Elon (proposed)              Deadline: [2026-11-04]                 │
│                                                                              │
│  Tracker status: [at_risk ▾]                                                │
│  Last update: Nov 1, 6:57 PM EST                                            │
│                                                                              │
│  Goal: [                                                              ]      │
│                                                                              │
│  Where it stands:                                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ Blocked login, org deleted, phishing emails detected                │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  Next steps:                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ Investigation by Elon                                               │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ─── Milestones ──────────────────────────────────────────────────────────  │
│  ☐ Investigation by Elon                         [2026-11-04]    [✕]       │
│  [+ Add milestone]                                                           │
│                                                                              │
│  ─── Blockers ────────────────────────────────────────────────────────────  │
│  ┌──────────────────────────────┐ [Man      ▾] [Oct 28  ] [✕]             │
│  │ Waiting for decision on      │                                           │
│  │ whether to start             │                                           │
│  └──────────────────────────────┘                                           │
│  [+ Add blocker]                                                             │
│                                                                              │
│  ─── Waiting on Man ──────────────────────────────────────────────────────  │
│  What's needed:                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ Should Elon investigate this? Ari asked twice with no answer.       │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│  Since when: Oct 28                                                          │
│                                                                              │
│  Added from tracker_seed · updated 2 minutes ago                             │
│                                                                              │
│  [Delete]                                    [Cancel]  [Save]               │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Key UI Features Visible

1. **Warning Flags**: 
   - ⚠ Stale (appears when last_update_at is >7 days old)
   - ⚠ Overdue (appears when milestones are past due)
   - 🚫 Blockers (shows count, e.g., "🚫 2 blockers")

2. **Status Chips**:
   - on_track (green background)
   - at_risk (orange background)
   - blocked (red background)
   - done (green background)

3. **Filters**: Four dropdowns plus company/project status from before

4. **Editable Fields**:
   - Milestones: checkbox for done, title, due date, remove button
   - Blockers: what (textarea), blocked_by, since, remove button
   - Waiting on Man: needed (textarea), since

## Testing Notes

- All 13 workstreams from tracker_seed.json loaded successfully
- 6 projects have waiting_on_man set (shown in banner)
- UI tested with Flask test client and memory store
- API endpoints verified working with tracker fields

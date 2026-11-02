"""What the assistant knows about the companies, and how that knowledge is shown to a model.

Three layers:
  1. knowledge/company.md: the stable background (personas, salons, staff, teams),
     copied from the repo's CLAUDE.md and shipped with the service.
  2. The knowledge base in the store: projects, facts, open questions for the
     owner, and the systems the assistant can or can't reach yet. It grows from
     the hourly Chat read, from the owner's answers and from conversations.
  3. brief(): a compact text view of (2) that goes into every prompt.

SEED_SYSTEMS and SEED_QUESTIONS are written once, on first start; after that
the knowledge base is the owner's and the assistant's to edit.
"""

import hashlib
import os
import re

from store import AUTONOMY_CATEGORIES, utcnow_iso

_COMPANY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "knowledge", "company.md")
_company_cache = None

# status: connected (the assistant can use it now), available (credentials exist in the
# project but the assistant can't use them yet), needed, requested, not_used.
SEED_SYSTEMS = [
    ("google_chat", "Google Chat", "Communication", "connected", "Read every space and DM; post as Manne."),
    ("google_calendar", "Google Calendar", "Communication", "connected", "Read and create calendar events."),
    ("workspace_directory", "Workspace directory", "People", "connected", "Names and emails of everyone in the company."),
    # The AI rows' status is kept true by talk.Talk.test_partners (Check connections and every hourly run).
    ("gemini", "Gemini (Vertex AI)", "AI", "connected", "Man AI's own brain and voice."),
    ("chatgpt", "ChatGPT (OpenAI)", "AI partner", "available", "Second opinions, drafts and live voice calls from ChatGPT."),
    ("claude", "Claude (Anthropic)", "AI partner", "available", "Second opinions and drafts from Claude."),
    ("bigcommerce_ca", "BigCommerce: superhairpieces.ca", "Commerce", "available",
     "Orders, products, customers for the .ca store (hash gmosz3ja). Token exists for the reporting scripts."),
    ("bigcommerce_com", "BigCommerce: superhairpieces.com (USD)", "Commerce", "needed", "Orders, products, customers for the US store."),
    ("merchant_center", "Google Merchant Center", "Marketing", "available",
     "Shopping feeds. .ca account 5298296396 is connected for the repo scripts; .com/EU 289630622 and Gen'C 670525760 are not."),
    ("trustpilot", "Trustpilot", "Reviews", "available", "Reviews and replies; used by the trustpilot pipeline."),
    ("gmail", "Gmail", "Communication", "needed", "Read and send email as Manne (can be added to the same sign-in)."),
    ("google_drive", "Google Drive / Sheets / Docs", "Documents", "needed",
     "Find and update SOPs, sheets and docs (can be added to the same sign-in)."),
    ("skuvault", "SkuVault", "Inventory", "needed", "Stock levels, purchase orders, the Amazon-SkuVault bridge."),
    ("stamped", "Stamped.io", "Reviews", "needed", "Product reviews and the Review Rewards program."),
    ("amazon", "Amazon Seller Central", "Commerce", "needed", "Amazon orders, listings, FBM/FBA."),
    ("meta", "Meta (Facebook / Instagram)", "Marketing", "needed", "Ads, Instagram posts and messages."),
    ("google_ads", "Google Ads", "Marketing", "needed", "Campaigns and budgets (an API application exists in the repo)."),
    ("analytics", "GA4 / Search Console", "Marketing", "needed", "Traffic, conversions, search performance."),
    ("accounting", "Accounting (QuickBooks?)", "Finance", "needed", "Revenue, costs, payables."),
    ("teamdesk", "TeamDesk", "Operations", "needed", "Referenced by an existing integration; purpose unknown."),
]

SEED_QUESTIONS = [
    ("Gen'C Beauty: what does it sell, to whom, on which sites or platforms, who's on the team, "
     "and how does it relate to Superhairpieces?", "I can't run a company I can't describe.", 1),
    ("What are the top 3-5 goals for each company for the next 90 days, with numbers if you have them?",
     "Goals decide which projects I push first.", 1),
    ("List every active project you can think of, one line each: name, goal, owner, status, deadline. "
     "Which Chat spaces are projects and which are day-to-day channels?", "Projects are how I organise the work.", 1),
    ("Where does the truth live for orders, inventory, customers/CRM, support tickets, salon appointments, "
     "finance, staff schedules, and SOPs/documents?", "Tells me which systems to connect first.", 2),
    ("Which systems will you give me API access to: BigCommerce .com and EU, SkuVault, "
     "Stamped.io, Amazon Seller Central, Meta/Instagram, Google Ads, GA4/Search Console, accounting, TeamDesk?",
     "Each connection lets me do work instead of asking about it.", 2),
    ("What are these Cloud Run services and who maintains them: course-webapp, gchat-gemini-bot, "
     "genc-sales-dashboard, google-ads-dashboard, order-form, reviews-dashboard, stamped-webhook?",
     "They're already running on the company's project; I should know what they do.", 3),
    ("Besides you, who can give me instructions, and who should I escalate to in each area?",
     "So I route work to the right people.", 2),
    ("What are my hard limits: spending caps, anything I must never touch or say, "
     "and who approves when you're unavailable?", "Sets the guardrails for autopilot.", 1),
]


def company_background():
    global _company_cache
    if _company_cache is None:
        try:
            with open(_COMPANY_FILE, encoding="utf-8") as handle:
                _company_cache = handle.read()
        except OSError:
            _company_cache = ""
    return _company_cache


def vocabulary(store):
    """Words a voice line must hear right: the company background, plus every project and system name."""
    names = lambda kind: ", ".join(sorted({i.get("name", "") for i in store.list_items(kind)} - {""}))  # noqa: E731
    return "\n\n".join(part for part in (company_background(), f"Projects: {names('projects')}",
                                           f"Systems: {names('systems')}") if not part.endswith(": "))


def name_hints(store, limit=900):
    """A short list of names for speech-to-text: company terms, people and places, projects, systems."""
    names = ["Superhairpieces", "Gen'C Beauty", "Tier 1"]
    for line in company_background().splitlines():
        if line.startswith("|") and not line.startswith("|--") and "`" not in line:
            for cell in line.strip("|").split("|"):
                names += [n.strip() for n in cell.split(",") if re.fullmatch(r"[A-Z][\w' .-]{1,30}", n.strip())]
    for kind in ("projects", "systems"):
        names += [i.get("name", "") for i in store.list_items(kind)]
    seen, out = set(), []
    for n in names:
        if n and n.lower() not in seen:
            seen.add(n.lower())
            out.append(n)
    return ", ".join(out)[:limit]


def slug(text, prefix=""):
    base = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")[:48] or "item"
    digest = hashlib.sha1((text or "").lower().encode("utf-8")).hexdigest()[:6]
    return f"{prefix}{base}-{digest}"


def ensure_seeded(store):
    """Write the starting systems and interview questions once."""
    if store.get_flag("seeded_v1"):
        return
    now = utcnow_iso()
    for sid, name, category, status, unlocks in SEED_SYSTEMS:
        if not store.get_item("systems", sid):
            store.save_item("systems", sid, {"name": name, "category": category, "status": status,
                                             "unlocks": unlocks, "source": "seed", "created_at": now, "updated_at": now})
    for i, (question, why, priority) in enumerate(SEED_QUESTIONS):
        qid = slug(question, "q-")
        if not store.get_item("questions", qid):
            store.save_item("questions", qid, {"question": question, "why": why, "priority": priority,
                                               "status": "open", "source": "round 1", "project_id": "",
                                               "created_at": f"{now}#{i:02d}", "updated_at": now})
    store.set_flag("seeded_v1", now)


def seed_tracker_workstreams(store, tracker_data):
    """One-time load of tracker workstreams from tracker_seed.json. Idempotent: won't overwrite existing projects."""
    if store.get_flag("tracker_seeded"):
        return 0
    
    count = 0
    failures = []
    now = utcnow_iso()
    
    for idx, ws in enumerate(tracker_data.get("workstreams", [])):
        try:
            name = ws.get("name", "").strip()
            if not name:
                failures.append(f"Item {idx}: missing name")
                continue
            
            # Check if a project with this exact name already exists
            if find_project(store, name):
                continue
            
            # Parse tracker status
            status_map = {
                "On track": "on_track",
                "At risk": "at_risk",
                "Blocked": "blocked",
                "Done": "done",
                "Unknown": "unknown"
            }
            tracker_status = status_map.get(ws.get("status"), "unknown")
            
            # Build waiting_on_man structure
            waiting_on_man = {}
            waiting_text = ws.get("waiting_on_man", "")
            if waiting_text and not waiting_text.startswith("None"):
                waiting_on_man = {"needed": waiting_text[:500], "since": ws.get("last_update_at", now)}
            
            # Extract milestone from next_milestone if present
            milestones = []
            if ws.get("next_milestone"):
                milestones.append({
                    "title": ws["next_milestone"][:200],
                    "due": "",
                    "done": False
                })
            
            project = {
                "name": name,
                "owner": ws.get("owner", "")[:100],
                "status": "active" if tracker_status not in ("done",) else "done",
                "tracker_status": tracker_status,
                "summary": "",
                "next_steps": ws.get("next_milestone", "")[:2000],
                "milestones": milestones,
                "blockers": [],
                "waiting_on_man": waiting_on_man,
                "last_update_at": ws.get("last_update_at", "")[:30],
                "company": "superhairpieces",
                "goal": "",
                "deadline": "",
                "spaces": []
            }
            
            saved = save_project(store, project, source="tracker_seed")
            if saved:
                count += 1
            else:
                failures.append(f"Item {idx} ({name[:40]}...): save_project returned None")
        except Exception as exc:  # noqa: BLE001 - log and continue with other items
            name_preview = ws.get("name", "unknown")[:40] if isinstance(ws.get("name"), str) else "unknown"
            failures.append(f"Item {idx} ({name_preview}...): {type(exc).__name__}: {str(exc)[:100]}")
    
    # Always set the flag after processing all items, even if some failed
    store.set_flag("tracker_seeded", now)
    
    if failures:
        print(f"Tracker seed: {count} succeeded, {len(failures)} failed:")
        for failure in failures:
            print(f"  - {failure}")
    
    return count


def add_fact(store, text, topic="general", project_id="", source=""):
    text = (text or "").strip()
    if not text:
        return None
    fid = slug(text, "f-")
    if store.get_item("facts", fid):
        return store.get_item("facts", fid)
    now = utcnow_iso()
    return store.save_item("facts", fid, {"text": text[:1000], "topic": topic or "general", "project_id": project_id or "",
                                          "source": source[:120], "created_at": now, "updated_at": now})


def add_question(store, question, why="", project_id="", priority=2, source=""):
    question = (question or "").strip()
    if not question:
        return None
    qid = slug(question, "q-")
    existing = store.get_item("questions", qid)
    if existing:
        return existing
    now = utcnow_iso()
    return store.save_item("questions", qid, {"question": question[:600], "why": (why or "")[:300],
                                              "project_id": project_id or "", "priority": int(priority or 2),
                                              "status": "open", "source": source[:120], "created_at": now,
                                              "updated_at": now})


def find_project(store, name_or_id):
    """Find a project by ID or exact name. Never uses raw names as doc IDs."""
    if not name_or_id:
        return None
    # Try as a document ID first (if it looks like a slug/ID, not a name with slashes or spaces)
    if name_or_id and "/" not in name_or_id and " " not in name_or_id:
        item = store.get_item("projects", name_or_id)
        if item:
            return item
    # Fall back to name matching across all projects
    wanted = name_or_id.strip().lower()
    for p in store.list_items("projects"):
        if p.get("name", "").strip().lower() == wanted:
            return p
    return None


def save_project(store, fields, source=""):
    """Create or update a project by id or exact name. Returns the saved project."""
    existing = find_project(store, fields.get("project_id") or fields.get("name"))
    now = utcnow_iso()
    clean = {k: (str(v)[:2000] if isinstance(v, str) else v) for k, v in fields.items()
             if k in ("name", "company", "goal", "owner", "status", "deadline", "summary", "next_steps") and v not in (None, "")}
    
    # Tracker fields: milestones (list), blockers (list), waiting_on_man (dict), tracker_status, last_update_at
    if "milestones" in fields and isinstance(fields["milestones"], list):
        clean["milestones"] = fields["milestones"]
    if "blockers" in fields and isinstance(fields["blockers"], list):
        clean["blockers"] = fields["blockers"]
    if "waiting_on_man" in fields and isinstance(fields["waiting_on_man"], dict):
        clean["waiting_on_man"] = fields["waiting_on_man"]
    if "tracker_status" in fields and fields["tracker_status"] in ("on_track", "at_risk", "blocked", "done", "unknown"):
        clean["tracker_status"] = fields["tracker_status"]
    if "last_update_at" in fields:
        clean["last_update_at"] = str(fields["last_update_at"])[:30]
    
    if existing:
        return store.save_item("projects", existing["id"], {**clean, "updated_at": now})
    if not clean.get("name"):
        return None
    pid = slug(clean["name"], "p-")
    return store.save_item("projects", pid, {"company": "", "goal": "", "owner": "", "status": "active", "deadline": "",
                                             "summary": "", "next_steps": "", "spaces": [], 
                                             "milestones": [], "blockers": [], "waiting_on_man": {}, 
                                             "tracker_status": "unknown", "last_update_at": "", "man_answers": [],
                                             **clean, "source": source[:120], "created_at": now, "updated_at": now})


def brief(store, settings=None, facts_limit=60, compact=False):
    """A compact picture of the knowledge base for a prompt."""
    projects = store.list_items("projects")
    lines = [f"PROJECTS ({len(projects)})"]
    for p in projects[:80]:
        meta = " · ".join(x for x in (p.get("company"), p.get("status"), p.get("owner") and f"owner {p['owner']}",
                                      p.get("deadline") and f"due {p['deadline']}") if x)
        if compact:
            lines.append(f"- {p.get('name')} [{p['id']}]")
        else:
            lines.append(f"- {p.get('name')} [{p['id']}] ({meta}) {p.get('goal') or p.get('summary') or ''}".rstrip())
    if not projects:
        lines.append("- none recorded yet")
    if compact:
        return "\n".join(lines)

    facts = store.list_items("facts")[:facts_limit]
    lines.append(f"\nWHAT YOU'VE LEARNED ({len(facts)} most recent)")
    lines += [f"- {f.get('text')}" + (f" (project {f['project_id']})" if f.get("project_id") else "") for f in facts]
    if not facts:
        lines.append("- nothing yet")

    # Include recent man_answers
    recent_answers = []
    for p in projects:
        for a in (p.get("man_answers") or [])[-3:]:  # Last 3 answers per project
            recent_answers.append((a.get("answered_at", ""), p.get("name"), a.get("question"), a.get("text")))
    recent_answers.sort(key=lambda x: x[0], reverse=True)
    if recent_answers[:10]:
        lines.append(f"\nRECENT ANSWERS FROM MAN ({len(recent_answers[:10])})")
        for answered_at, proj_name, question, text in recent_answers[:10]:
            lines.append(f"- [{proj_name}] Q: {question[:60]} → A: {text[:100]}")

    questions = sorted((q for q in store.list_items("questions") if q.get("status") == "open"),
                       key=lambda q: (q.get("priority", 2), q.get("created_at", "")))
    lines.append(f"\nOPEN QUESTIONS FOR THE OWNER ({len(questions)})")
    lines += [f"- [{q['id']}] {q.get('question')}" for q in questions[:12]]

    systems = store.list_items("systems")
    by_status = {}
    for s in systems:
        by_status.setdefault(s.get("status", "needed"), []).append(s.get("name", s["id"]))
    lines.append("\nSYSTEMS")
    for status in ("connected", "available", "requested", "needed"):
        if by_status.get(status):
            lines.append(f"- {status}: {', '.join(sorted(by_status[status]))}")

    if settings:
        autonomy = settings.get("autonomy", {})
        lines.append("\nAUTONOMY (auto = do it; ask = propose and wait for the owner)")
        lines.append("- automatic actions are " + ("ON" if settings.get("auto_act", True) else "PAUSED (everything asks)"))
        lines += [f"- {AUTONOMY_CATEGORIES[k]}: {autonomy.get(k, 'ask')}" for k in AUTONOMY_CATEGORIES]
    return "\n".join(lines)

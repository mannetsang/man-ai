"""Tests for the cross-team project tracker features."""

import json
import os
import sys
import unittest

os.environ["STORE_BACKEND"] = "memory"
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "cloud_run"))

import knowledge  # noqa: E402
from store import MemoryStore, utcnow_iso  # noqa: E402


class TrackerDataModelTests(unittest.TestCase):
    def setUp(self):
        self.store = MemoryStore()
    
    def test_project_with_tracker_fields(self):
        """A project can have milestones, blockers, waiting_on_man, tracker_status, and last_update_at."""
        project = knowledge.save_project(self.store, {
            "name": "Test Project",
            "owner": "Devon",
            "tracker_status": "on_track",
            "last_update_at": "Nov 1, 3:00 PM EST",
            "milestones": [
                {"title": "Phase 1", "due": "2026-11-15", "done": False},
                {"title": "Launch", "due": "2026-12-01", "done": False}
            ],
            "blockers": [
                {"what": "Waiting for API access", "blocked_by": "IT", "since": "Oct 28"}
            ],
            "waiting_on_man": {
                "needed": "Approve design",
                "since": "Nov 1"
            }
        }, source="test")
        
        self.assertIsNotNone(project)
        self.assertEqual(project["name"], "Test Project")
        self.assertEqual(project["tracker_status"], "on_track")
        self.assertEqual(len(project["milestones"]), 2)
        self.assertEqual(project["milestones"][0]["title"], "Phase 1")
        self.assertEqual(len(project["blockers"]), 1)
        self.assertEqual(project["blockers"][0]["what"], "Waiting for API access")
        self.assertEqual(project["waiting_on_man"]["needed"], "Approve design")
    
    def test_project_backward_compatible(self):
        """Projects without tracker fields still work with sensible defaults."""
        project = knowledge.save_project(self.store, {
            "name": "Legacy Project",
            "owner": "Mark",
            "status": "active"
        }, source="test")
        
        self.assertIsNotNone(project)
        self.assertEqual(project["milestones"], [])
        self.assertEqual(project["blockers"], [])
        self.assertEqual(project["waiting_on_man"], {})
        self.assertEqual(project["tracker_status"], "unknown")
        self.assertEqual(project["last_update_at"], "")
    
    def test_update_project_tracker_fields(self):
        """Updating a project preserves and updates tracker fields."""
        # Create project
        project = knowledge.save_project(self.store, {
            "name": "Evolving Project",
            "tracker_status": "on_track"
        }, source="test")
        
        # Update with new milestone
        updated = knowledge.save_project(self.store, {
            "project_id": project["id"],
            "tracker_status": "at_risk",
            "milestones": [{"title": "New milestone", "due": "2026-11-20", "done": False}]
        }, source="test")
        
        self.assertEqual(updated["tracker_status"], "at_risk")
        self.assertEqual(len(updated["milestones"]), 1)
        self.assertEqual(updated["milestones"][0]["title"], "New milestone")


class TrackerSeedTests(unittest.TestCase):
    def setUp(self):
        self.store = MemoryStore()
    
    def test_seed_tracker_workstreams(self):
        """Seeding from tracker_seed.json creates projects idempotently."""
        seed_data = {
            "workstreams": [
                {
                    "name": "Fix broken .ca link",
                    "owner": "Devon",
                    "status": "On track",
                    "last_update_at": "Oct 29, 10:58 AM EDT",
                    "next_milestone": "Create branch and commit fix",
                    "waiting_on_man": "Devon needs Man's go-ahead to create the branch."
                },
                {
                    "name": "Fill missing OTTO recommendations",
                    "owner": "Mark",
                    "status": "At risk",
                    "last_update_at": "Oct 28, 10:25 PM EDT",
                    "next_milestone": "Completed CSV",
                    "waiting_on_man": "None. First run was interrupted."
                }
            ]
        }
        
        count = knowledge.seed_tracker_workstreams(self.store, seed_data)
        self.assertEqual(count, 2)
        
        # Verify projects were created
        projects = self.store.list_items("projects")
        self.assertEqual(len(projects), 2)
        
        devon_project = next((p for p in projects if p["owner"] == "Devon"), None)
        self.assertIsNotNone(devon_project)
        self.assertEqual(devon_project["tracker_status"], "on_track")
        self.assertTrue(devon_project["waiting_on_man"]["needed"])
        self.assertEqual(len(devon_project["milestones"]), 1)
        
        # Second seed should be idempotent (no duplicates)
        count2 = knowledge.seed_tracker_workstreams(self.store, seed_data)
        self.assertEqual(count2, 0)
        self.assertEqual(len(self.store.list_items("projects")), 2)
    
    def test_seed_handles_done_status(self):
        """Projects with 'Done' status are created with status='done'."""
        seed_data = {
            "workstreams": [
                {
                    "name": "Completed Task",
                    "owner": "Kai",
                    "status": "Done",
                    "last_update_at": "Oct 28, 9:20 PM EDT",
                    "next_milestone": "Next phase unknown",
                    "waiting_on_man": "None."
                }
            ]
        }
        
        knowledge.seed_tracker_workstreams(self.store, seed_data)
        projects = self.store.list_items("projects")
        
        done_project = next((p for p in projects if p["name"] == "Completed Task"), None)
        self.assertIsNotNone(done_project)
        self.assertEqual(done_project["status"], "done")
        self.assertEqual(done_project["tracker_status"], "done")


class TaskProjectLinkTests(unittest.TestCase):
    def setUp(self):
        self.store = MemoryStore()
        self.project = knowledge.save_project(self.store, {
            "name": "Test Project",
            "owner": "Devon"
        }, source="test")
    
    def test_task_can_link_to_project(self):
        """A task can be linked to a project via project_id."""
        now = utcnow_iso()
        task = self.store.save_task("task1", {
            "title": "Test task",
            "project_id": self.project["id"],
            "status": "todo",
            "created_at": now,
            "updated_at": now
        })
        
        self.assertEqual(task["project_id"], self.project["id"])
    
    def test_task_without_project_link(self):
        """A task without a project_id is valid."""
        now = utcnow_iso()
        task = self.store.save_task("task2", {
            "title": "Standalone task",
            "project_id": "",
            "status": "todo",
            "created_at": now,
            "updated_at": now
        })
        
        self.assertEqual(task["project_id"], "")


class TrackerToolsTests(unittest.TestCase):
    """Tests for the AI's tracker tools (tools.py)."""
    
    def setUp(self):
        self.store = MemoryStore()
        # Import tools here to avoid dependency issues in other tests
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "cloud_run"))
        from tools import Toolset
        self.toolset = Toolset(self.store, google=None, caller="test", may_change=False)
        
        # Create a test project
        self.project = knowledge.save_project(self.store, {
            "name": "AI Tool Test Project",
            "owner": "Devon",
            "tracker_status": "on_track"
        }, source="test")
    
    def test_list_projects_includes_tracker_fields(self):
        """list_projects returns tracker fields."""
        result = self.toolset._t_list_projects()
        projects = result["projects"]
        
        self.assertEqual(len(projects), 1)
        p = projects[0]
        self.assertIn("tracker_status", p)
        self.assertIn("milestones", p)
        self.assertIn("blockers", p)
        self.assertIn("waiting_on_man", p)
        self.assertIn("last_update_at", p)
    
    def test_save_project_with_tracker_fields(self):
        """save_project accepts and stores tracker fields."""
        result = self.toolset._t_save_project(
            name="Tracker Test",
            owner="Mark",
            tracker_status="at_risk",
            last_update_at="Nov 2, 10:00 AM",
            milestones=[{"title": "Phase 1", "due": "2026-11-15", "done": False}],
            blockers=[{"what": "Waiting for API", "blocked_by": "IT", "since": "Nov 1"}],
            waiting_on_man={"needed": "Approval", "since": "Nov 1"}
        )
        
        self.assertIn("project", result)
        p = result["project"]
        self.assertEqual(p["tracker_status"], "at_risk")
        self.assertEqual(len(p["milestones"]), 1)
        self.assertEqual(p["milestones"][0]["title"], "Phase 1")
        self.assertEqual(len(p["blockers"]), 1)
        self.assertEqual(p["waiting_on_man"]["needed"], "Approval")
    
    def test_update_tracker_status(self):
        """update_project_tracker can set tracker_status."""
        result = self.toolset._t_update_project_tracker(
            project_id=self.project["id"],
            tracker_status="at_risk"
        )
        
        self.assertTrue(result["updated"])
        updated = self.store.get_item("projects", self.project["id"])
        self.assertEqual(updated["tracker_status"], "at_risk")
    
    def test_add_milestone(self):
        """update_project_tracker can add a milestone."""
        result = self.toolset._t_update_project_tracker(
            project_id=self.project["id"],
            add_milestone={"title": "Launch v2", "due": "2026-12-01"}
        )
        
        self.assertTrue(result["updated"])
        updated = self.store.get_item("projects", self.project["id"])
        self.assertEqual(len(updated["milestones"]), 1)
        self.assertEqual(updated["milestones"][0]["title"], "Launch v2")
        self.assertFalse(updated["milestones"][0]["done"])
    
    def test_complete_milestone(self):
        """update_project_tracker can mark a milestone as done."""
        # First add a milestone
        self.store.save_item("projects", self.project["id"], {
            "milestones": [{"title": "Setup", "due": "2026-11-01", "done": False}]
        })
        
        result = self.toolset._t_update_project_tracker(
            project_id=self.project["id"],
            complete_milestone="Setup"
        )
        
        self.assertTrue(result["updated"])
        updated = self.store.get_item("projects", self.project["id"])
        self.assertTrue(updated["milestones"][0]["done"])
    
    def test_add_blocker(self):
        """update_project_tracker can add a blocker."""
        result = self.toolset._t_update_project_tracker(
            project_id=self.project["id"],
            add_blocker={"what": "Dependency not ready", "blocked_by": "Backend team", "since": "Nov 1"}
        )
        
        self.assertTrue(result["updated"])
        updated = self.store.get_item("projects", self.project["id"])
        self.assertEqual(len(updated["blockers"]), 1)
        self.assertEqual(updated["blockers"][0]["what"], "Dependency not ready")
    
    def test_clear_blocker(self):
        """update_project_tracker can remove a blocker."""
        # First add a blocker
        self.store.save_item("projects", self.project["id"], {
            "blockers": [{"what": "API access", "blocked_by": "IT", "since": "Oct 28"}]
        })
        
        result = self.toolset._t_update_project_tracker(
            project_id=self.project["id"],
            clear_blocker="API access"
        )
        
        self.assertTrue(result["updated"])
        updated = self.store.get_item("projects", self.project["id"])
        self.assertEqual(len(updated["blockers"]), 0)
    
    def test_set_waiting_on_man(self):
        """update_project_tracker can set waiting_on_man."""
        result = self.toolset._t_update_project_tracker(
            project_id=self.project["id"],
            set_waiting_on_man={"needed": "Design approval", "since": "Nov 2"}
        )
        
        self.assertTrue(result["updated"])
        updated = self.store.get_item("projects", self.project["id"])
        self.assertEqual(updated["waiting_on_man"]["needed"], "Design approval")
        self.assertEqual(updated["waiting_on_man"]["since"], "Nov 2")
    
    def test_clear_waiting_on_man(self):
        """update_project_tracker can clear waiting_on_man."""
        # First set it
        self.store.save_item("projects", self.project["id"], {
            "waiting_on_man": {"needed": "Something", "since": "Nov 1"}
        })
        
        result = self.toolset._t_update_project_tracker(
            project_id=self.project["id"],
            clear_waiting_on_man=True
        )
        
        self.assertTrue(result["updated"])
        updated = self.store.get_item("projects", self.project["id"])
        self.assertEqual(updated["waiting_on_man"], {})
    
    def test_update_last_update_timestamp(self):
        """update_project_tracker bumps last_update_at by default."""
        result = self.toolset._t_update_project_tracker(
            project_id=self.project["id"],
            tracker_status="blocked"
        )
        
        self.assertTrue(result["updated"])
        updated = self.store.get_item("projects", self.project["id"])
        self.assertTrue(updated["last_update_at"])  # Should be set
    
    def test_multiple_updates_at_once(self):
        """update_project_tracker can update multiple fields in one call."""
        result = self.toolset._t_update_project_tracker(
            project_id=self.project["id"],
            tracker_status="blocked",
            add_milestone={"title": "Unblock", "due": "2026-11-05"},
            add_blocker={"what": "External dependency", "blocked_by": "Vendor", "since": "Nov 1"},
            set_waiting_on_man={"needed": "Escalate to vendor", "since": "Nov 2"}
        )
        
        self.assertTrue(result["updated"])
        updated = self.store.get_item("projects", self.project["id"])
        self.assertEqual(updated["tracker_status"], "blocked")
        self.assertEqual(len(updated["milestones"]), 1)
        self.assertEqual(len(updated["blockers"]), 1)
        self.assertTrue(updated["waiting_on_man"]["needed"])
    
    def test_update_nonexistent_project(self):
        """update_project_tracker returns error for nonexistent project."""
        result = self.toolset._t_update_project_tracker(
            project_id="nonexistent",
            tracker_status="on_track"
        )
        
        self.assertIn("error", result)
        self.assertEqual(result["error"], "no such project")


if __name__ == "__main__":
    unittest.main()

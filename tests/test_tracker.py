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


if __name__ == "__main__":
    unittest.main()

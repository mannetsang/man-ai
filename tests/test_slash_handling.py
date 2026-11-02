"""Tests for Firestore slash-in-name handling."""

import os
import sys
import unittest

os.environ["STORE_BACKEND"] = "memory"
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "cloud_run"))

import knowledge  # noqa: E402
from store import MemoryStore, utcnow_iso  # noqa: E402


class FirestorePathValidatingStore(MemoryStore):
    """Fake store that rejects document IDs with slashes like real Firestore."""
    
    def _validate_doc_id(self, doc_id):
        if "/" in doc_id:
            raise ValueError(f"A document must have an even number of path elements (got: {doc_id})")
    
    def _get(self, coll, doc_id):
        self._validate_doc_id(doc_id)
        return super()._get(coll, doc_id)
    
    def _set(self, coll, doc_id, data, merge=False):
        self._validate_doc_id(doc_id)
        return super()._set(coll, doc_id, data, merge)
    
    def _delete(self, coll, doc_id):
        self._validate_doc_id(doc_id)
        return super()._delete(coll, doc_id)


class SlashInNameTests(unittest.TestCase):
    """Test that names with slashes don't break Firestore operations."""
    
    def setUp(self):
        self.store = FirestorePathValidatingStore()
    
    def test_find_project_with_slash_in_name(self):
        """find_project handles names with slashes by falling back to name matching."""
        # Create a project with a slash in the name
        project = knowledge.save_project(self.store, {
            "name": "Fix broken .ca link on /superhair-knowledge"
        }, source="test")
        
        self.assertIsNotNone(project)
        self.assertEqual(project["name"], "Fix broken .ca link on /superhair-knowledge")
        
        # Should be able to find it by name
        found = knowledge.find_project(self.store, "Fix broken .ca link on /superhair-knowledge")
        self.assertIsNotNone(found)
        self.assertEqual(found["id"], project["id"])
    
    def test_find_project_with_slash_does_not_use_as_doc_id(self):
        """find_project never passes a name with slash as a document ID."""
        # This should not raise even though we're using the validating store
        # because find_project should skip the get_item call for names with slashes
        found = knowledge.find_project(self.store, "/supplies/ on-page SEO fixes")
        self.assertIsNone(found)  # Doesn't exist yet, but didn't crash
    
    def test_save_project_with_slash_in_name(self):
        """save_project creates safe IDs even for names with slashes."""
        project = knowledge.save_project(self.store, {
            "name": "/supplies/ on-page SEO fixes (title, meta, H1/H2)",
            "owner": "Mark"
        }, source="test")
        
        self.assertIsNotNone(project)
        # ID should be sanitized (no slashes)
        self.assertNotIn("/", project["id"])
        # But name should be preserved
        self.assertEqual(project["name"], "/supplies/ on-page SEO fixes (title, meta, H1/H2)")
    
    def test_update_project_with_slash_in_name(self):
        """Updating a project found by name with slashes works."""
        # Create project
        project = knowledge.save_project(self.store, {
            "name": "Apple Business Spain alert (blocked login, org deleted) and phishing emails",
            "owner": "Elon"
        }, source="test")
        
        # Update using project_id
        updated = knowledge.save_project(self.store, {
            "project_id": project["id"],
            "tracker_status": "blocked"
        }, source="test")
        
        self.assertEqual(updated["tracker_status"], "blocked")
    
    def test_multiple_projects_with_slashes(self):
        """Multiple projects with slashes can coexist."""
        names = [
            "Fix broken .ca link on /superhair-knowledge (OTTO issue 203340165:links:43)",
            "/supplies/ on-page SEO fixes (title, meta, H1/H2, alt text, links, schema)",
            "Apple Business Spain alert (blocked login, org deleted) and phishing emails in Re:amaze"
        ]
        
        projects = []
        for name in names:
            p = knowledge.save_project(self.store, {"name": name}, source="test")
            self.assertIsNotNone(p)
            projects.append(p)
        
        # All should have unique IDs without slashes
        ids = [p["id"] for p in projects]
        self.assertEqual(len(ids), len(set(ids)))  # All unique
        for pid in ids:
            self.assertNotIn("/", pid)
        
        # All should be findable by name
        for name in names:
            found = knowledge.find_project(self.store, name)
            self.assertIsNotNone(found)
            self.assertEqual(found["name"], name)


class SlashInSeedTests(unittest.TestCase):
    """Test seeding with names containing slashes."""
    
    def setUp(self):
        self.store = FirestorePathValidatingStore()
    
    def test_seed_with_slash_names(self):
        """Seeding works with names containing slashes."""
        seed_data = {
            "workstreams": [
                {
                    "name": "Fix broken .ca link on /superhair-knowledge (OTTO issue 203340165:links:43)",
                    "owner": "Devon",
                    "status": "On track",
                    "last_update_at": "Oct 29, 10:58 AM EDT",
                    "next_milestone": "Create branch and commit fix",
                    "waiting_on_man": "Devon needs Man's go-ahead"
                },
                {
                    "name": "/supplies/ on-page SEO fixes",
                    "owner": "Mark",
                    "status": "At risk",
                    "last_update_at": "Oct 28, 9:30 PM EDT",
                    "next_milestone": "HTML/metadata diff",
                    "waiting_on_man": "Mark asked whether Devon or Kai should prepare the diff"
                }
            ]
        }
        
        count = knowledge.seed_tracker_workstreams(self.store, seed_data)
        self.assertEqual(count, 2)
        
        # Both should be findable
        p1 = knowledge.find_project(self.store, "Fix broken .ca link on /superhair-knowledge (OTTO issue 203340165:links:43)")
        self.assertIsNotNone(p1)
        
        p2 = knowledge.find_project(self.store, "/supplies/ on-page SEO fixes")
        self.assertIsNotNone(p2)
    
    def test_seed_with_bad_item_continues(self):
        """One bad seed item doesn't abort the rest."""
        seed_data = {
            "workstreams": [
                {
                    "name": "Good Project 1",
                    "owner": "Alice",
                    "status": "On track"
                },
                {
                    # Missing name - should fail but not abort
                    "owner": "Bob",
                    "status": "On track"
                },
                {
                    "name": "Good Project 2",
                    "owner": "Charlie",
                    "status": "Done"
                }
            ]
        }
        
        count = knowledge.seed_tracker_workstreams(self.store, seed_data)
        self.assertEqual(count, 2)  # Two good ones succeeded
        
        # Flag should still be set
        self.assertTrue(self.store.get_flag("tracker_seeded"))
    
    def test_seed_idempotent_after_partial_failure(self):
        """Seeding is idempotent even after partial failures."""
        seed_data = {
            "workstreams": [
                {"name": "Project A", "owner": "Alice", "status": "On track"},
                {"owner": "Bob", "status": "On track"},  # Missing name
            ]
        }
        
        # First seed
        count1 = knowledge.seed_tracker_workstreams(self.store, seed_data)
        self.assertEqual(count1, 1)
        
        # Second seed should return 0 (already seeded)
        count2 = knowledge.seed_tracker_workstreams(self.store, seed_data)
        self.assertEqual(count2, 0)


class ToolsWithSlashTests(unittest.TestCase):
    """Test AI tools with names containing slashes."""
    
    def setUp(self):
        self.store = FirestorePathValidatingStore()
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "cloud_run"))
        from tools import Toolset
        self.toolset = Toolset(self.store, google=None, caller="test", may_change=False)
    
    def test_save_project_tool_with_slash(self):
        """save_project tool handles names with slashes."""
        result = self.toolset._t_save_project(
            name="Fix /api/endpoint bug in checkout flow",
            owner="Devon",
            tracker_status="on_track"
        )
        
        self.assertIn("project", result)
        p = result["project"]
        self.assertEqual(p["name"], "Fix /api/endpoint bug in checkout flow")
        self.assertNotIn("/", p["id"])
    
    def test_update_project_tracker_with_slash_in_name(self):
        """update_project_tracker works after finding project by name with slashes."""
        # Create project
        p = knowledge.save_project(self.store, {
            "name": "Review /admin/settings page security"
        }, source="test")
        
        # Update via tool
        result = self.toolset._t_update_project_tracker(
            project_id=p["id"],
            tracker_status="at_risk",
            add_blocker={"what": "Security audit incomplete", "blocked_by": "Security team", "since": "Nov 1"}
        )
        
        self.assertTrue(result["updated"])
        updated = self.store.get_item("projects", p["id"])
        self.assertEqual(updated["tracker_status"], "at_risk")
        self.assertEqual(len(updated["blockers"]), 1)
    
    def test_list_projects_includes_slash_names(self):
        """list_projects returns projects with slashes in names."""
        knowledge.save_project(self.store, {
            "name": "Fix /checkout/payment redirect issue"
        }, source="test")
        
        result = self.toolset._t_list_projects()
        projects = result["projects"]
        
        self.assertEqual(len(projects), 1)
        self.assertEqual(projects[0]["name"], "Fix /checkout/payment redirect issue")


if __name__ == "__main__":
    unittest.main()

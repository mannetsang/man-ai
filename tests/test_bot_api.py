"""Tests for bot API key authentication and authorization."""

import json
import os
import sys
import unittest
from unittest import mock

os.environ["STORE_BACKEND"] = "memory"
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "cloud_run"))

import knowledge  # noqa: E402
import main  # noqa: E402
from store import MemoryStore, utcnow_iso  # noqa: E402


class BotApiKeyTests(unittest.TestCase):
    def setUp(self):
        self.store = MemoryStore()
        main.store = self.store
        main.app.testing = True
        self.client = main.app.test_client()
        
        # Mock bot API key
        self.bot_key = "test-bot-key-1234567890abcdef"
        
        # Mock secret_store.get to return the bot key
        self.secret_store_patcher = mock.patch.object(
            main.secret_store, 
            "get",
            side_effect=lambda secret_id: self.bot_key if secret_id == main.BOT_API_KEY_SECRET_ID else None
        )
        self.secret_store_patcher.start()
        
        # Clear and set cache with current timestamp
        import time
        main._bot_api_key_cache = {"key": self.bot_key, "checked_at": time.time()}
        
        # Also set up session auth for comparison tests
        with self.client.session_transaction() as sess:
            sess["email"] = main.OWNER_EMAIL
    
    def tearDown(self):
        # Stop patchers
        self.secret_store_patcher.stop()
        # Clear cache
        main._bot_api_key_cache = {"key": None, "checked_at": None}
    
    def test_list_projects_with_valid_bot_key(self):
        """Bot can list projects with valid API key."""
        project = knowledge.save_project(self.store, {
            "name": "Test Project",
            "status": "active"
        }, source="test")
        
        response = self.client.get(
            "/api/projects",
            headers={"Authorization": f"Bearer {self.bot_key}"}
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("projects", data)
        self.assertEqual(len(data["projects"]), 1)
        self.assertEqual(data["projects"][0]["name"], "Test Project")
    
    def test_get_project_with_valid_bot_key(self):
        """Bot can get a specific project with valid API key."""
        project = knowledge.save_project(self.store, {
            "name": "Test Project",
            "status": "active"
        }, source="test")
        
        response = self.client.get(
            f"/api/projects/{project['id']}",
            headers={"Authorization": f"Bearer {self.bot_key}"}
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["project"]["name"], "Test Project")
    
    def test_create_project_with_valid_bot_key(self):
        """Bot can create projects with valid API key."""
        response = self.client.post(
            "/api/projects",
            headers={"Authorization": f"Bearer {self.bot_key}"},
            json={
                "name": "Bot Created Project",
                "company": "superhairpieces",
                "status": "active",
                "tracker_status": "on_track"
            }
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["project"]["name"], "Bot Created Project")
        
        # Check activity was logged
        actions = list(self.store._list("chat_assistant_actions"))
        bot_actions = [a for a in actions if a.get("type") == "bot_create_project"]
        self.assertEqual(len(bot_actions), 1)
        self.assertEqual(bot_actions[0]["actor"], "bot:jules")
    
    def test_update_project_tracker_fields_with_bot_key(self):
        """Bot can update tracker fields with valid API key."""
        project = knowledge.save_project(self.store, {
            "name": "Test Project",
            "tracker_status": "on_track"
        }, source="test")
        
        response = self.client.patch(
            f"/api/projects/{project['id']}",
            headers={"Authorization": f"Bearer {self.bot_key}"},
            json={
                "tracker_status": "at_risk",
                "last_update_at": "Nov 2, 10:00 AM EST",
                "blockers": [{"what": "Waiting", "blocked_by": "IT", "since": "Nov 1"}]
            }
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["project"]["tracker_status"], "at_risk")
        self.assertEqual(len(data["project"]["blockers"]), 1)
        
        # Check activity was logged
        actions = list(self.store._list("chat_assistant_actions"))
        bot_actions = [a for a in actions if a.get("type") == "bot_update_project"]
        self.assertEqual(len(bot_actions), 1)
        self.assertEqual(bot_actions[0]["actor"], "bot:jules")
    
    def test_bot_patch_ignores_non_tracker_fields(self):
        """Bot PATCH ignores non-tracker fields like company."""
        project = knowledge.save_project(self.store, {
            "name": "Test Project",
            "company": "superhairpieces",
            "tracker_status": "on_track"
        }, source="test")
        
        response = self.client.patch(
            f"/api/projects/{project['id']}",
            headers={"Authorization": f"Bearer {self.bot_key}"},
            json={
                "company": "gencbeauty",  # Should be ignored
                "tracker_status": "at_risk"  # Should be applied
            }
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        
        # Company should remain unchanged
        self.assertEqual(data["project"]["company"], "superhairpieces")
        # tracker_status should be updated
        self.assertEqual(data["project"]["tracker_status"], "at_risk")
    
    def test_get_answers_with_valid_bot_key(self):
        """Bot can fetch answers with valid API key."""
        project = knowledge.save_project(self.store, {"name": "Project 1"}, source="test")
        self.store.save_item("projects", project["id"], {
            "man_answers": [
                {"text": "Answer 1", "answered_at": "2026-11-01T10:00:00Z", "question": "Q1"}
            ]
        })
        
        response = self.client.get(
            "/api/projects/answers",
            headers={"Authorization": f"Bearer {self.bot_key}"}
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(len(data["answers"]), 1)
    
    def test_create_task_with_project_link(self):
        """Bot can create tasks linked to projects."""
        project = knowledge.save_project(self.store, {"name": "Test Project"}, source="test")
        
        response = self.client.post(
            "/api/tasks",
            headers={"Authorization": f"Bearer {self.bot_key}"},
            json={
                "title": "Bot Task",
                "project_id": project["id"],
                "priority": "high"
            }
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["task"]["title"], "Bot Task")
        self.assertEqual(data["task"]["project_id"], project["id"])
        
        # Check activity was logged
        actions = list(self.store._list("chat_assistant_actions"))
        bot_actions = [a for a in actions if a.get("type") == "bot_create_task"]
        self.assertEqual(len(bot_actions), 1)
        self.assertEqual(bot_actions[0]["actor"], "bot:jules")
    
    def test_bot_create_task_without_project_fails(self):
        """Bot cannot create tasks without project_id."""
        response = self.client.post(
            "/api/tasks",
            headers={"Authorization": f"Bearer {self.bot_key}"},
            json={
                "title": "Bot Task"
            }
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn("project", data["error"].lower())
    
    def test_update_task_project_link(self):
        """Bot can update task project_id."""
        project = knowledge.save_project(self.store, {"name": "Test Project"}, source="test")
        
        # Create task as user
        task_resp = self.client.post(
            "/api/tasks",
            headers={"X-Chat-Assistant": "1"},
            json={"title": "Test Task"}
        )
        task = task_resp.get_json()["task"]
        
        # Bot updates project_id
        response = self.client.patch(
            f"/api/tasks/{task['id']}",
            headers={"Authorization": f"Bearer {self.bot_key}"},
            json={"project_id": project["id"]}
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["task"]["project_id"], project["id"])
    
    def test_bot_update_task_other_fields_fails(self):
        """Bot cannot update task fields other than project_id."""
        # Create task as user
        task_resp = self.client.post(
            "/api/tasks",
            headers={"X-Chat-Assistant": "1"},
            json={"title": "Test Task"}
        )
        task = task_resp.get_json()["task"]
        
        # Bot tries to update title
        response = self.client.patch(
            f"/api/tasks/{task['id']}",
            headers={"Authorization": f"Bearer {self.bot_key}"},
            json={"title": "New Title"}
        )
        
        self.assertEqual(response.status_code, 400)
    
    def test_wrong_api_key_rejected(self):
        """Requests with wrong API key are rejected."""
        response = self.client.get(
            "/api/projects",
            headers={"Authorization": "Bearer wrong-key"}
        )
        
        self.assertEqual(response.status_code, 401)
    
    def test_missing_api_key_falls_back_to_session(self):
        """Requests without API key fall back to session auth."""
        project = knowledge.save_project(self.store, {
            "name": "Test Project"
        }, source="test")
        
        # Request with session auth (no bot key)
        response = self.client.get("/api/projects")
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(len(data["projects"]), 1)
    
    def test_bot_cannot_delete_projects(self):
        """Bot cannot delete projects."""
        project = knowledge.save_project(self.store, {
            "name": "Test Project"
        }, source="test")
        
        response = self.client.delete(
            f"/api/projects/{project['id']}",
            headers={"Authorization": f"Bearer {self.bot_key}"}
        )
        
        self.assertEqual(response.status_code, 403)
        data = response.get_json()
        self.assertIn("not allowed", data["error"].lower())
    
    def test_bot_cannot_access_settings(self):
        """Bot cannot access settings endpoints."""
        response = self.client.patch(
            "/api/settings",
            headers={"Authorization": f"Bearer {self.bot_key}"},
            json={"auto_act": False}
        )
        
        self.assertEqual(response.status_code, 403)
    
    def test_bot_cannot_access_actions(self):
        """Bot cannot access action endpoints."""
        response = self.client.post(
            "/api/actions/a-123/send",
            headers={"Authorization": f"Bearer {self.bot_key}"}
        )
        
        self.assertEqual(response.status_code, 403)
    
    def test_missing_secret_disables_bot_auth(self):
        """Missing bot API key secret disables bot auth gracefully."""
        # Clear the cache and mock secret_store to return None
        import time
        main._bot_api_key_cache = {"key": None, "checked_at": time.time()}
        
        # Stop the patcher and create a new one that returns None
        self.secret_store_patcher.stop()
        self.secret_store_patcher = mock.patch.object(
            main.secret_store, 
            "get",
            return_value=None
        )
        self.secret_store_patcher.start()
        
        # Request with Authorization header but missing secret
        response = self.client.get(
            "/api/projects",
            headers={"Authorization": f"Bearer {self.bot_key}"}
        )
        
        # Should reject with 401 (invalid API key, since there's no valid key to compare against)
        self.assertEqual(response.status_code, 401)
    
    def test_request_size_limit(self):
        """Bot requests are limited in size."""
        large_body = {"name": "A" * 60000}  # > 50KB
        
        response = self.client.post(
            "/api/projects",
            headers={"Authorization": f"Bearer {self.bot_key}"},
            json=large_body
        )
        
        self.assertEqual(response.status_code, 413)
    
    def test_bot_key_cache_refresh(self):
        """Bot API key cache refreshes periodically."""
        import time
        
        # Set cache with old timestamp
        main._bot_api_key_cache = {"key": "old-key", "checked_at": time.time() - 400}
        
        # Mock secret_store.get to return new key
        with mock.patch.object(main.secret_store, "get", return_value="new-key"):
            key = main.bot_api_key()
            self.assertEqual(key, "new-key")
    
    def test_bot_auth_uses_constant_time_comparison(self):
        """Bot authentication uses constant-time comparison (hmac.compare_digest)."""
        import hmac
        
        with mock.patch("hmac.compare_digest", wraps=hmac.compare_digest) as mock_compare:
            response = self.client.get(
                "/api/projects",
                headers={"Authorization": f"Bearer {self.bot_key}"}
            )
            
            # Verify hmac.compare_digest was called
            self.assertTrue(mock_compare.called)


if __name__ == "__main__":
    unittest.main()

"""Tests for Man answering 'waiting on Man' items in projects."""

import json
import os
import sys
import unittest

os.environ["STORE_BACKEND"] = "memory"
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "cloud_run"))

import knowledge  # noqa: E402
import main  # noqa: E402
from store import MemoryStore, utcnow_iso  # noqa: E402


class AnswerWaitingOnManTests(unittest.TestCase):
    def setUp(self):
        self.store = MemoryStore()
        main.store = self.store
        main.app.testing = True
        self.client = main.app.test_client()
        
        # Mock authentication
        with self.client.session_transaction() as sess:
            sess["email"] = main.OWNER_EMAIL
    
    def test_answer_clears_waiting_on_man(self):
        """Submitting an answer clears waiting_on_man by default."""
        project = knowledge.save_project(self.store, {
            "name": "Test Project",
            "waiting_on_man": {"needed": "Approve design", "since": "Nov 1"}
        }, source="test")
        
        response = self.client.post(
            f"/api/projects/{project['id']}/answer",
            json={"text": "Design approved, proceed with implementation."},
            headers={"X-Chat-Assistant": "1"}
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        updated = data["project"]
        
        # waiting_on_man should be cleared
        self.assertEqual(updated["waiting_on_man"], {})
        
        # man_answers should have one entry
        self.assertEqual(len(updated["man_answers"]), 1)
        self.assertEqual(updated["man_answers"][0]["text"], "Design approved, proceed with implementation.")
        self.assertEqual(updated["man_answers"][0]["question"], "Approve design")
        self.assertIn("answered_at", updated["man_answers"][0])
    
    def test_answer_with_keep_waiting(self):
        """Submitting an answer with keep_waiting=True keeps waiting_on_man."""
        project = knowledge.save_project(self.store, {
            "name": "Partial Answer Project",
            "waiting_on_man": {"needed": "Clarify requirements", "since": "Nov 1"}
        }, source="test")
        
        response = self.client.post(
            f"/api/projects/{project['id']}/answer",
            json={"text": "Here's part 1, working on the rest.", "keep_waiting": True},
            headers={"X-Chat-Assistant": "1"}
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        updated = data["project"]
        
        # waiting_on_man should still be set
        self.assertEqual(updated["waiting_on_man"]["needed"], "Clarify requirements")
        
        # man_answers should have one entry
        self.assertEqual(len(updated["man_answers"]), 1)
        self.assertEqual(updated["man_answers"][0]["text"], "Here's part 1, working on the rest.")
    
    def test_multiple_answers(self):
        """A project can have multiple answers over time."""
        project = knowledge.save_project(self.store, {
            "name": "Multi Answer Project",
            "waiting_on_man": {"needed": "Question 1", "since": "Nov 1"}
        }, source="test")
        
        # First answer
        r1 = self.client.post(
            f"/api/projects/{project['id']}/answer",
            json={"text": "Answer 1"},
            headers={"X-Chat-Assistant": "1"}
        )
        self.assertEqual(r1.status_code, 200)
        
        # Refetch project from store
        project = self.store.get_item("projects", project["id"])
        
        # Add a new waiting question
        self.store.save_item("projects", project["id"], {
            "waiting_on_man": {"needed": "Question 2", "since": "Nov 2"}
        })
        
        # Second answer
        response = self.client.post(
            f"/api/projects/{project['id']}/answer",
            json={"text": "Answer 2"},
            headers={"X-Chat-Assistant": "1"}
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        updated = data["project"]
        
        # Should have two answers
        self.assertEqual(len(updated["man_answers"]), 2)
        self.assertEqual(updated["man_answers"][0]["text"], "Answer 1")
        self.assertEqual(updated["man_answers"][0]["question"], "Question 1")
        self.assertEqual(updated["man_answers"][1]["text"], "Answer 2")
        self.assertEqual(updated["man_answers"][1]["question"], "Question 2")
    
    def test_answer_validates_empty_text(self):
        """Empty answer text is rejected."""
        project = knowledge.save_project(self.store, {
            "name": "Validation Project",
            "waiting_on_man": {"needed": "Test", "since": "Nov 1"}
        }, source="test")
        
        response = self.client.post(
            f"/api/projects/{project['id']}/answer",
            json={"text": "   "},
            headers={"X-Chat-Assistant": "1"}
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn("error", data)
    
    def test_answer_caps_length(self):
        """Answer text is capped at 4000 chars."""
        project = knowledge.save_project(self.store, {
            "name": "Long Answer Project",
            "waiting_on_man": {"needed": "Long question", "since": "Nov 1"}
        }, source="test")
        
        long_text = "A" * 5000
        response = self.client.post(
            f"/api/projects/{project['id']}/answer",
            json={"text": long_text},
            headers={"X-Chat-Assistant": "1"}
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        updated = data["project"]
        
        # Text should be truncated to 4000
        self.assertEqual(len(updated["man_answers"][0]["text"]), 4000)
    
    def test_answer_with_slash_in_project_name(self):
        """Answering works safely with project names containing slashes."""
        project = knowledge.save_project(self.store, {
            "name": "/supplies/ on-page SEO fixes",
            "waiting_on_man": {"needed": "Approve keywords", "since": "Nov 1"}
        }, source="test")
        
        # Use the project ID (slug) in URL, which should be safe
        response = self.client.post(
            f"/api/projects/{project['id']}/answer",
            json={"text": "Keywords approved"},
            headers={"X-Chat-Assistant": "1"}
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        updated = data["project"]
        
        self.assertEqual(len(updated["man_answers"]), 1)
        self.assertEqual(updated["man_answers"][0]["text"], "Keywords approved")
    
    def test_get_recent_answers_all(self):
        """GET /api/projects/answers returns all answers."""
        # Create projects with answers using save_item directly
        p1 = knowledge.save_project(self.store, {"name": "Project 1"}, source="test")
        self.store.save_item("projects", p1["id"], {
            "man_answers": [
                {"text": "Answer 1A", "answered_at": "2026-11-01T10:00:00Z", "question": "Q1A"}
            ]
        })
        
        p2 = knowledge.save_project(self.store, {"name": "Project 2"}, source="test")
        self.store.save_item("projects", p2["id"], {
            "man_answers": [
                {"text": "Answer 2A", "answered_at": "2026-11-02T10:00:00Z", "question": "Q2A"},
                {"text": "Answer 2B", "answered_at": "2026-11-02T11:00:00Z", "question": "Q2B"}
            ]
        })
        
        response = self.client.get("/api/projects/answers")
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        answers = data["answers"]
        
        # Should have 3 total answers, newest first
        self.assertEqual(len(answers), 3)
        self.assertEqual(answers[0]["answer"], "Answer 2B")
        self.assertEqual(answers[1]["answer"], "Answer 2A")
        self.assertEqual(answers[2]["answer"], "Answer 1A")
        self.assertEqual(answers[0]["project_name"], "Project 2")
    
    def test_get_recent_answers_since_filter(self):
        """GET /api/projects/answers?since= filters by timestamp."""
        p1 = knowledge.save_project(self.store, {"name": "Project 1"}, source="test")
        self.store.save_item("projects", p1["id"], {
            "man_answers": [
                {"text": "Old answer", "answered_at": "2026-11-01T10:00:00Z", "question": "Q1"},
                {"text": "New answer", "answered_at": "2026-11-02T10:00:00Z", "question": "Q2"}
            ]
        })
        
        response = self.client.get("/api/projects/answers?since=2026-11-01T12:00:00Z")
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        answers = data["answers"]
        
        # Should only return answers after the since timestamp
        self.assertEqual(len(answers), 1)
        self.assertEqual(answers[0]["answer"], "New answer")
    
    def test_get_recent_answers_invalid_since(self):
        """GET /api/projects/answers with invalid since returns error."""
        response = self.client.get("/api/projects/answers?since=not-a-date")
        
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn("error", data)
    
    def test_list_projects_tool_includes_man_answers(self):
        """The list_projects tool includes man_answers."""
        from tools import Toolset
        
        project = knowledge.save_project(self.store, {
            "name": "Tool Test Project"
        }, source="test")
        
        # Add man_answers directly to the project
        self.store.save_item("projects", project["id"], {
            "man_answers": [
                {"text": "Test answer", "answered_at": "2026-11-01T10:00:00Z", "question": "Test question"}
            ]
        })
        
        tools = Toolset(self.store)
        result = tools._t_list_projects()
        
        projects = result["projects"]
        self.assertEqual(len(projects), 1)
        self.assertEqual(projects[0]["name"], "Tool Test Project")
        self.assertIn("man_answers", projects[0])
        self.assertEqual(len(projects[0]["man_answers"]), 1)
        self.assertEqual(projects[0]["man_answers"][0]["text"], "Test answer")
    
    def test_answer_records_activity(self):
        """Answering creates an activity entry."""
        project = knowledge.save_project(self.store, {
            "name": "Activity Test Project",
            "waiting_on_man": {"needed": "Test question", "since": "Nov 1"}
        }, source="test")
        
        response = self.client.post(
            f"/api/projects/{project['id']}/answer",
            json={"text": "Test answer"},
            headers={"X-Chat-Assistant": "1"}
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Check that an activity entry was created
        actions = list(self.store._list("chat_assistant_actions"))
        man_answer_actions = [a for a in actions if a.get("type") == "man_answer"]
        
        self.assertEqual(len(man_answer_actions), 1)
        action = man_answer_actions[0]
        self.assertEqual(action["status"], "done")
        self.assertEqual(action["project_name"], "Activity Test Project")
        self.assertIn("Test answer", action["answer_text"])
        self.assertEqual(action["keep_waiting"], False)


if __name__ == "__main__":
    unittest.main()

"""
###
Four  unit tests written by Google Gemini using the following AI prompt
"please write four unit tests for the attached python file."
###
"""

import unittest
from unittest.mock import patch#, MagicMock
from qanda_web import app, QUESTIONS, ANSWERS # Import the app and globals
#from flask import url_for

# Setup the testing environment and mock database access
class QandAWebTest(unittest.TestCase):
    """Unit testing functions"""

    def setUp(self):
        """Set up the test client and mock data."""
        self.app = app.test_client()
        self.app.testing = True

        # Backup original globals
        self.original_questions = list(QUESTIONS)
        self.original_answers = list(ANSWERS)

        # Set up mock data for testing routes
        self.mock_quest = ["Name the French capital", "What color is the sky?", "What is 2+2?"]
        self.mock_ans = ["Paris", "Blue", "4"]

        # Directly manipulate the global state for route testing simplicity
        # Note: In a real-world scenario, mocking load_qas() is safer.
        QUESTIONS.clear()
        QUESTIONS.extend(self.mock_quest)
        ANSWERS.clear()
        ANSWERS.extend(self.mock_ans)

        # Clear session before each test"Q1: What is the capital of France?"
        with self.app as client:
            with client.session_transaction() as session:
                session.clear()

    def tearDown(self):
        """Restore original global data."""
        QUESTIONS.clear()
        QUESTIONS.extend(self.original_questions)
        ANSWERS.clear()
        ANSWERS.extend(self.original_answers)

    # 1. Test the index route with no session data (initial load)
    def test_1_index_initial_load(self):
        """Test the initial state of the index page."""
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Name the French capital", response.data)
        self.assertIn(b"Answers will appear here", response.data)

        # Check that show_answer is False
        self.assertNotIn(b'data-answer-visible="True"', response.data)


    # 2. Test the /next route and subsequent index page state
    def test_2_next_question_rotation(self):
        """Test the /next route cycles through questions and hides the answer."""

        # Initial state: index is not set, defaults to -1, next goes to 0 (Q1)
        response = self.app.get('/next', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Name the French capital", response.data)

        # Second call: index goes to 1 (Q2)
        response = self.app.get('/next', follow_redirects=True)
        self.assertIn(b"What color is the sky?", response.data)

        # Third call: index goes to 2 (Q3)
        response = self.app.get('/next', follow_redirects=True)
        self.assertIn(b"What is 2+2?", response.data)

        # Fourth call: index wraps around using modulo back "Q1: What is the capital of France?"to 0 (Q1)
        response = self.app.get('/next', follow_redirects=True)
        self.assertIn(b"Name the French capital", response.data)

        # Ensure answer is never shown after /next
        self.assertNotIn(b"Paris", response.data)


    # 3. Test the /answer route logic
    def test_3_view_answer(self):
        """Test the /answer route reveals the correct answer."""

        # First, set a question index by calling /next (sets index to 0)
        self.app.get('/next')

        # Now call /answer
        response = self.app.get('/answer', follow_redirects=True)
        self.assertEqual(response.status_code, 200)

        # Check that both the question and the corresponding answer are present
        self.assertIn(b"Name the French capital", response.data)
        self.assertIn(b"Paris", response.data)

        # Check that show_answer is True
        self.assertIn(b'data-answer-visible="True"', response.data)


    # 4. Test the /random route
    # We use unittest.mock.patch to ensure 'random.randrange' returns a fixed value
    @patch('QandAWed.random.randrange', return_value=1)
    def test_4_random_question(self, mock_random):
        """Test the /random route selects the expected random question (Q2)."""

        # The mock ensures QandAWed.random.randrange returns 1, so Q2 should be selected.
        response = self.app.get('/random', follow_redirects=True)
        self.assertEqual(response.status_code, 200)

        # Check that Q2 is displayed
        self.assertIn(b"What color is the sky?", response.data)

        # Check that the answer is hidden
        self.assertIn(b"Answers will appear here", response.data)
        self.assertNotIn(b"Blue", response.data)

        # Verify the mock was called correctly
        mock_random.assert_called_once_with(len(QUESTIONS))

# This block allows you to run the tests directly
if __name__ == '__main__':
    unittest.main()

"""Testing file for unit testing teh qanda_web.py file"""

from unittest.mock import patch
import pytest
from qanda_web import app, QUESTIONS, ANSWERS


@pytest.fixture(name="client")
def fixture_client():
    """Configures the app for testing and provides a test client."""
    app.config['TESTING'] = True

    # Setup: Backup and Mock Data
    original_questions = list(QUESTIONS)
    original_answers = list(ANSWERS)

    mock_quest = ["Name the French capital", "What color is the sky?", "What is 2+2?"]
    mock_ans = ["Paris", "Blue", "4"]

    QUESTIONS.clear()
    QUESTIONS.extend(mock_quest)
    ANSWERS.clear()
    ANSWERS.extend(mock_ans)
    
    # pylint: disable-next=contextmanager-generator-missing-cleanup
    with app.test_client() as client:
        with client.session_transaction() as session:
            session.clear()
        yield client

    # Teardown: Restore original data
    QUESTIONS.clear()
    QUESTIONS.extend(original_questions)
    ANSWERS.clear()
    ANSWERS.extend(original_answers)

# 1. Test the index route with no session data
def test_index_initial_load(client):
    """Test the initial state of the index page."""
    response = client.get('/')
    assert response.status_code == 200
    assert b"Name the French capital" in response.data
    assert b"Answer hidden" in response.data
    assert b'data-answer-visible="True"' not in response.data

# 2. Test the /next route and rotation
def test_next_question_rotation(client):
    """Test the /next route cycles through questions."""
    # First call: index goes to 0 (Q1)
    response = client.get('/next', follow_redirects=True)
    assert b"Name the French capital" in response.data

    # Second call: index goes to 1 (Q2)
    response = client.get('/next', follow_redirects=True)
    assert b"What color is the sky?" in response.data

    # Third call: index goes to 2 (Q3)
    response = client.get('/next', follow_redirects=True)
    assert b"What is 2+2?" in response.data

    # Fourth call: wraps back to 0 (Q1)
    response = client.get('/next', follow_redirects=True)
    assert b"Name the French capital" in response.data
    assert b"Paris" not in response.data

# 3. Test the /answer route logic
def test_view_answer(client):
    """Test the /answer route reveals the correct answer."""
    client.get('/next')  # Set index to 0
    response = client.get('/answer', follow_redirects=True)

    assert response.status_code == 200
    assert b"Name the French capital" in response.data
    assert b"Paris" in response.data
    #assert b'data-answer-visible="True"' in response.data

    # Second call: index goes to 1 (Q2)
    response = client.get('/next', follow_redirects=True)
    response = client.get('/answer', follow_redirects=True)
    assert b"What color is the sky?" in response.data
    assert b"Blue" in response.data

# 4. Test the /random route
@patch('qanda_web.random.randrange', return_value=1)
def test_random_question(mock_random, client):
    """Test the /random route selects the expected random question (Q2)."""
    response = client.get('/random', follow_redirects=True)

    assert response.status_code == 200
    assert b"What color is the sky?" in response.data
    assert b"Answer hidden" in response.data
    assert b"Blue" not in response.data
    mock_random.assert_called_once_with(len(QUESTIONS))

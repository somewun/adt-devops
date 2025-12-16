"""QandAWeb.py

Converted from a PyQt desktop app to a simple Flask web app.

Routes expose: / (index), /next, /random, /answer, /about

Requires Flask to run. If Flask is not installed the app will print a helpful message.
"""

import os
import sys
import random
import sqlite3
from pathlib import Path
from contextlib import contextmanager

try:
    from flask import Flask, render_template, session, redirect, url_for, flash, g
except Exception as e:
    # Provide a helpful message if Flask is missing; 
	# Don't crash on import so static analysis can still read the file
    print("Flask is required to run this web app. Install it with: pip install flask")
    raise

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / '.wrangler/state/d1/DB.db'  # Local D1 database path
@contextmanager
def get_db():
    """Get database connection (development mode uses SQLite, production uses D1)."""
    if 'db' not in g:
        # In production, this would use Cloudflare D1's connection
        # For local development, we use SQLite
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    
    try:
        yield g.db
    finally:
        if 'db' in g:
            g.db.close()
            g.pop('db')

def load_qas():
    """Load questions and answers from D1 database.
    
    Returns two lists: questions, answers.
    """
    questions = []
    answers = []
    
    if not DB_PATH.exists():
        print(f"Database not found at {DB_PATH}. Run migrations first.")
        return questions, answers
        
    try:
        with get_db() as db:
            cursor = db.execute('SELECT question, answer FROM questions ORDER BY id')
            rows = cursor.fetchall()
            for row in rows:
                questions.append(row['question'])
                answers.append(row['answer'])
    except Exception as e:
        print(f"Database error: {e}")
        
    return questions, answers
# Ensure Flask locates templates relative to this file's directory (BASE_DIR)
# This avoids TemplateNotFound when running the script from a different CWD.
app = Flask(__name__, template_folder=str(BASE_DIR / ''))
# Use a simple secret for session; in production set a secure fixed secret via env var
app.secret_key = os.environ.get('FLASK_SECRET', 'dev-secret-change-me')
#config the app for using the database


@app.teardown_appcontext
def close_db(error):
    """Close database connection at the end of request."""
    if 'db' in g:
        g.db.close()
        g.pop('db')

with app.app_context():
# Load Q/A once at startup
	QUESTIONS, ANSWERS = load_qas()


@app.context_processor
def inject_counts():
	"""Calculates the amount of questions available"""
	return dict(total_questions=len(QUESTIONS))


@app.route('/')
def index():
	"""Default welcome texts when no questions are loaded or before first Next is pressed"""
	default_question = "Questions will appear here, press Next Q or Random Q to get a question"
	default_answer = "Answers will appear here, press Answer to show the answer"

	q_index = session.get('q_index')
	show_answer = session.get('show_answer', False)

	if q_index is None or not QUESTIONS:
		question_text = default_question if not QUESTIONS else QUESTIONS[0]
		answer_text = default_answer
	else:
		# ensure index in range
		q_index = max(0, min(q_index, len(QUESTIONS) - 1))
		question_text = QUESTIONS[q_index]
		answer_text = ANSWERS[q_index] if show_answer and ANSWERS else default_answer

	return render_template('index.html', question=question_text, answer=answer_text, show_answer=show_answer)


@app.route('/next')
def next_q():
	"""Moves user to the next question"""
	if not QUESTIONS:
		flash('No questions available. Ensure QandA.csv exists and has data.')
		return redirect(url_for('index'))

	q_index = session.get('q_index', -1)
	q_index = (q_index + 1) % len(QUESTIONS)
	session['q_index'] = q_index
	session['show_answer'] = False
	return redirect(url_for('index'))


@app.route('/random')
def random_q():
	"""Moves user to the a random question"""
	if not QUESTIONS:
		flash('No questions available. Ensure QandA.csv exists and has data.')
		return redirect(url_for('index'))

	q_index = random.randrange(len(QUESTIONS))
	session['q_index'] = q_index
	session['show_answer'] = False
	return redirect(url_for('index'))


@app.route('/answer')
def view_answer():
	"""Displays the answer to teh current question"""
	if 'q_index' not in session:
		flash('No current question selected. Press Next Q or Random Q first.')
		return redirect(url_for('index'))

	session['show_answer'] = True
	return redirect(url_for('index'))


@app.route('/about')
def about():
	"""Moves to teh about QandA page"""
	return render_template('about.html')


if __name__ == '__main__':
	# When run directly, start the Flask dev server
	if not QUESTIONS:
		print('Warning: No questions loaded. Update the database with format: ID,Question,Answer')

	# If running in an interactive environment (notebook), disable the reloader
	# because the reloader spawns a child and exits the parent with SystemExit(1).
	use_reloader = True
	if hasattr(sys, 'ps1') or 'ipykernel' in sys.modules or 'get_ipython' in globals():
		use_reloader = False

	#app.run(host='127.0.0.1', port=5002, debug=True, use_reloader=use_reloader)



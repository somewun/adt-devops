"""QandAWed.py

Converted from a PyQt desktop app to a simple Flask web app.

Routes expose: / (index), /next, /random, /answer, /about

Requires Flask to run. If Flask is not installed the app will print a helpful message.
"""

import os
import sys
import csv
import random
from pathlib import Path

try:
	from flask import Flask, render_template, session, redirect, url_for, flash
except Exception as e:
	# Provide a helpful message if Flask is missing; don't crash on import so static analysis can still read the file
	print("Flask is required to run this web app. Install it with: pip install flask")
	raise

BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR / 'QandA.csv'


def load_qas(csv_path=CSV_PATH):
	"""Load questions and answers from a CSV file.

	Expects format: ID,Question,Answer (with header or without). Returns two lists: questions, answers.
	"""
	questions = []
	answers = []
	if not csv_path.exists():
		return questions, answers

	with open(csv_path, newline='', encoding='utf-8') as fh:
		reader = csv.reader(fh)
		for row in reader:
			if not row:
				continue
			# tolerate an optional header row
			if row[0].strip().lower() in ('id', 'i', 'index') or row[1].strip().lower() == 'question':
				# skip header if detected
				try:
					int(row[0])
				except Exception:
					continue

			# Expect at least 3 columns: ID, Question, Answer. If shorter, skip.
			if len(row) < 3:
				continue
			questions.append(row[1])
			answers.append(row[2])

	return questions, answers


app = Flask(__name__)
# Use a simple secret for session; in production set a secure fixed secret via env var
app.secret_key = os.environ.get('FLASK_SECRET', 'dev-secret-change-me')

# Load Q/A once at startup
QUESTIONS, ANSWERS = load_qas()


@app.context_processor
def inject_counts():
	return dict(total_questions=len(QUESTIONS))


@app.route('/')
def index():
	# Default welcome texts when no questions are loaded or before first Next is pressed
	default_question = "Questions will appear here, press Next Q to get the first question or Random Q for a random question from the list"
	default_answer = "Answers will appear here, press Answer to get the answer"

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
	if not QUESTIONS:
		flash('No questions available. Ensure QandA.csv exists and has data.')
		return redirect(url_for('index'))

	q_index = random.randrange(len(QUESTIONS))
	session['q_index'] = q_index
	session['show_answer'] = False
	return redirect(url_for('index'))


@app.route('/answer')
def view_answer():
	if 'q_index' not in session:
		flash('No current question selected. Press Next Q or Random Q first.')
		return redirect(url_for('index'))

	session['show_answer'] = True
	return redirect(url_for('index'))


@app.route('/about')
def about():
	return render_template('about.html')


if __name__ == '__main__':
	# When run directly, start the Flask dev server
	if not QUESTIONS:
		print('Warning: No questions loaded from QandA.csv. Create a CSV with format: ID,Question,Answer')
	# If running in an interactive environment (notebook), disable the reloader
	# because the reloader spawns a child and exits the parent with SystemExit(1).
	use_reloader = True
	if hasattr(sys, 'ps1') or 'ipykernel' in sys.modules or 'get_ipython' in globals():
		use_reloader = False

	app.run(host='127.0.0.1', port=5000, debug=True, use_reloader=use_reloader)


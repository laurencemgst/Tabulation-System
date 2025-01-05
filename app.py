from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mysqldb import MySQL
import numpy as np
from jinja2 import Environment
from flask_socketio import SocketIO, emit

from db_config import MySQLConfig

app = Flask(__name__)

# Define custom Jinja2 filter for enumeration
def jinja2_enumerate(iterable, start=1):
    return enumerate(iterable, start)

# Register the custom filter
app.jinja_env.filters['enumerate'] = jinja2_enumerate

# Configure MySQL
app.config.from_object(MySQLConfig)

app.secret_key = 'tabulation001'  # Set a secret key for sessions

mysql = MySQL(app)
socketio = SocketIO(app)

@app.route('/')
def index():
    if 'loggedin' in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        cursor = mysql.connection.cursor()
        cursor.execute('SELECT username, is_admin, userID, name FROM users WHERE username = %s AND password = %s', (username, password))
        user = cursor.fetchone()
        cursor.close()
        
        if user:
            session['loggedin'] = True
            session['username'] = user[0]  # Accessing username using index 0
            session['is_admin'] = user[1]  # Accessing is_admin using index 1
            session['userID'] = user[2]    # Storing userID in session
            session['name'] = user[3] if len(user) > 3 else None  # Storing name if available, otherwise None
            print(user)  # For debugging
            return redirect(url_for('dashboard'))
        else:
            flash(f"Invalid username or password")
            return render_template('login.html', error='Invalid username or password')
    
    return render_template('login.html', error='')

@app.route('/dashboard')
def dashboard():
    if 'loggedin' in session:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT candidate_number, candidate_name, candidate_represent FROM candidates")
        candidates = cursor.fetchall()
        cursor.execute("SELECT candidate_number, candidate_name, candidate_represent FROM candidates WHERE final_segment = 1")
        final_candidates = cursor.fetchall()
        cursor.execute("SELECT userID, name, username, password, user_type FROM users WHERE is_admin=0")
        judges = cursor.fetchall()
        cursor.execute("SELECT segmentID, name FROM segments")
        segments = cursor.fetchall()
        cursor.close()

        # Render user or admin dashboard based on session data
        if session['is_admin']:
            return render_template('admin_dashboard.html', username=session['username'], candidates=candidates, judges=judges, segments=segments)
        else:
            return render_template('judges_dashboard.html', username=session['username'], name=session['name'], candidates=candidates, userID=session['userID'], final_candidates=final_candidates)
    return redirect(url_for('index'))

@app.route('/submit', methods=['POST'])
def submit():
    if request.method == 'POST':
        # Loop through the submitted form data for each candidate
        for candidate_id in request.form.getlist('candidate_id'):
            judge_id = request.form['judge_id']
            segment_id = request.form['segment_id']
            criteria1_value = int(request.form[f'criteria1_value_{candidate_id}'])
            criteria2_value = int(request.form[f'criteria2_value_{candidate_id}'])
            criteria3_value = int(request.form[f'criteria3_value_{candidate_id}'])
            criteria4_value = int(request.form[f'criteria4_value_{candidate_id}'])
            segment_total_score = criteria1_value + criteria2_value + criteria3_value + criteria4_value

            # Check if the judge has already submitted scores for this candidate
            cursor = mysql.connection.cursor()
            cursor.execute("SELECT * FROM scores WHERE segment_ID = %s AND judge_ID = %s AND candidate_number = %s", (segment_id, judge_id, candidate_id))
            existing_score = cursor.fetchone()
            cursor.close()

            if existing_score:
                flash(f"You've already submitted scores for this segment.")
                # Redirect or render a page indicating the error
                return redirect(url_for('index'))  # Redirect to the index for example

            # Insert scores into the database
            cursor = mysql.connection.cursor()
            cursor.execute("INSERT INTO scores (segment_ID, judge_ID, candidate_number, segment_total_score, criteria1_score, criteria2_score, criteria3_score, criteria4_score) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                           (segment_id, judge_id, candidate_id, segment_total_score, criteria1_value, criteria2_value, criteria3_value, criteria4_value))
            mysql.connection.commit()
            cursor.close()

    # You can return a response or redirect as needed
    # For example, redirect to a thank you page
    flash(f"Score is submitted! Thank you!", "success")
    if segment_id == '5':
        return render_template('thank_you.html')
    else:
        return redirect(url_for('index'))
    #return render_template('thank_you.html')


def fetch_candidates_and_scores(segment_id):
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT s.candidate_number, c.candidate_name, GROUP_CONCAT(s.segment_total_score ORDER BY s.judge_ID) FROM scores s JOIN candidates c ON s.candidate_number = c.candidate_number WHERE s.segment_ID = %s GROUP BY s.candidate_number", (segment_id,))
    candidates_data = cursor.fetchall()
    cursor.close()
    candidates_with_averages = []
    for candidate in candidates_data:
        scores = [int(score) for score in candidate[2].split(',')]
        average_score = np.mean(scores)
        candidates_with_averages.append((candidate[0], candidate[1], scores, average_score))
    candidates_with_averages.sort(key=lambda x: x[3], reverse=True)
    return candidates_with_averages

def update_score_final(segment_id, candidates_with_averages):
    cursor = mysql.connection.cursor()
    for candidate_number, _, _, average_score in candidates_with_averages:
        cursor.execute("SELECT * FROM score_final WHERE segment_id = %s AND candidate_number = %s", (segment_id, candidate_number))
        existing_row = cursor.fetchone()
        if existing_row:
            cursor.execute("UPDATE score_final SET segment_average_score = %s WHERE segment_id = %s AND candidate_number = %s", (average_score, segment_id, candidate_number))
        else:
            cursor.execute("INSERT INTO score_final (segment_id, candidate_number, segment_average_score) VALUES (%s, %s, %s)", (segment_id, candidate_number, average_score))
    mysql.connection.commit()

@app.route('/result/segment=<int:segment_id>')
def segment_result(segment_id):
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT userID, name, user_type FROM users WHERE is_admin = '0'")
    judges_data = cursor.fetchall()
    judge_names = {judge[0]: judge[1] for judge in judges_data}
    judge_info = {judge[1]: judge[2] for judge in judges_data}

    candidates_with_averages = fetch_candidates_and_scores(segment_id)
    update_score_final(segment_id, candidates_with_averages)

    return render_template(f'results/segment{segment_id}_result.html', candidates=candidates_with_averages, judges=judge_names, judge_info=judge_info)

# Function to calculate the total average segment score for each candidate
def calculate_total_average(scores):
    total_score = 0
    for segment_id, score in scores.items():
        if segment_id == 4:
            total_score += score * 0.4
        else:
            total_score += score * 0.2
    return total_score

# Function to update the score_final table with the total average for segment_id=5
def update_segment_5(cursor, candidate_number, total_average):
    cursor.execute("INSERT INTO score_final (segment_id, candidate_number, segment_average_score) VALUES (6, %s, %s)", (candidate_number, total_average))

# Function to fetch top 5 candidates for segment_id=6
def fetch_top_candidates(cursor):
    cursor.execute("SELECT candidate_number FROM score_final WHERE segment_id=6 ORDER BY segment_average_score DESC LIMIT 5")
    top_candidates = [row[0] for row in cursor.fetchall()]
    return top_candidates

# Function to update candidates table with final_segment=1 for top 5 candidates
def update_candidates_table(cursor, top_candidates):
    for candidate_number in top_candidates:
        cursor.execute("UPDATE candidates SET final_segment=1 WHERE candidate_number=%s", (candidate_number,))

# Flask route to perform the calculation and update the database
@app.route('/compute_top_finalists')
def calculate_and_update():
    cursor = mysql.connection.cursor()

    # Fetch data from the score_final table
    cursor.execute("SELECT candidate_number, segment_id, segment_average_score FROM score_final")
    results = cursor.fetchall()

    candidates_scores = {}
    for candidate_number, segment_id, segment_average_score in results:
        if candidate_number not in candidates_scores:
            candidates_scores[candidate_number] = {}
        candidates_scores[candidate_number][segment_id] = segment_average_score

    # Calculate total average and update the score_final table with segment_id=5
    for candidate_number, scores in candidates_scores.items():
        total_average = calculate_total_average(scores)
        update_segment_5(cursor, candidate_number, total_average)

    # Fetch top 5 candidates for segment_id=6
    top_candidates = fetch_top_candidates(cursor)

    # Update candidates table with final_segment=1 for top 5 candidates
    update_candidates_table(cursor, top_candidates)

    mysql.connection.commit()
    flash(f"Top finalists computed and updated successfully!!", "success")
    return redirect(url_for('index'))

@app.route('/finalist_candidates')
def final_candidates():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT s.candidate_number, c.candidate_name, c. candidate_represent, s.segment_average_score FROM score_final s JOIN candidates c ON s.candidate_number = c.candidate_number WHERE s.segment_ID = 6 GROUP BY s.candidate_number ORDER BY s.segment_average_score DESC")
    finalists_candidates = cursor.fetchall();
    cursor.close()
    return render_template('results/candidates_finalists.html', finalists_candidates=finalists_candidates)

@socketio.on('admin_action1')
def handle_admin_action(action):
    # Forward admin action to user dashboard
    emit('user_action1', action, broadcast=True)

@socketio.on('admin_action2')
def handle_admin_action(action):
    # Forward admin action to user dashboard
    emit('user_action2', action, broadcast=True)

@socketio.on('admin_action3')
def handle_admin_action(action):
    # Forward admin action to user dashboard
    emit('user_action3', action, broadcast=True)

@socketio.on('admin_action4')
def handle_admin_action(action):
    # Forward admin action to user dashboard
    emit('user_action4', action, broadcast=True)

@socketio.on('admin_action5')
def handle_admin_action(action):
    # Forward admin action to user dashboard
    emit('user_action5', action, broadcast=True)

#admin functions start here
@app.route('/updateCandidate', methods=['POST'])
def update_candidate():
    cursor = mysql.connection.cursor()
    candidate_number = request.form['candidate_number']
    candidate_name = request.form['candidate_name']
    candidate_represent = request.form['candidate_represent']
    cursor.execute("UPDATE candidates SET candidate_name=%s, candidate_represent=%s WHERE candidate_number=%s", (candidate_name, candidate_represent, candidate_number))
    mysql.connection.commit()
    # Perform update operation using request.form
    flash(f"Candidate {candidate_number} updated: Name - {candidate_name}, Represent - {candidate_represent}")
    return redirect(url_for('index'))

@app.route('/deleteCandidate', methods=['POST'])
def delete_candidate():
    cursor = mysql.connection.cursor()
    candidate_number = request.form['candidate_number']
    cursor.execute(f"DELETE FROM candidates WHERE candidate_number={candidate_number}")
    mysql.connection.commit()
    flash(f"Candidate number {candidate_number} deleted")
    return redirect(url_for('index'))

@app.route('/add_candidate', methods=['POST'])
def add_candidate():
    cursor = mysql.connection.cursor()
    # Handle candidate addition logic here
    candidate_number = request.form['candidate_number']
    candidate_name = request.form['candidate_name']
    candidate_represent = request.form['candidate_represent']
    cursor.execute("INSERT INTO candidates (candidate_number, candidate_name, candidate_represent) VALUES (%s, %s, %s)", ({candidate_number}, {candidate_name}, {candidate_represent}))
    mysql.connection.commit()
    flash(f"Candidate added: Number - {candidate_number}, Name - {candidate_name}, Represent - {candidate_represent}")
    return redirect(url_for('index'))

@app.route('/addJudge', methods=['POST'])
def add_judge():
    cursor = mysql.connection.cursor()
    # Handle candidate addition logic here
    judge_name = request.form['judge_name']
    judge_username = request.form['judge_username']
    judge_password = request.form['judge_password']
    judge_type = request.form['judge_type']
    cursor.execute("INSERT INTO users (name, username, password, user_type) VALUES (%s, %s, %s, %s)", ({judge_name}, {judge_username}, {judge_password}, {judge_type}))
    mysql.connection.commit()
    flash(f"Judge added: name - {judge_name}")
    return redirect(url_for('index'))

@app.route('/judgeUpdate', methods=['POST'])
def update_judge():
    cursor = mysql.connection.cursor()
    # Handle candidate addition logic here
    judge_id = request.form['judge_id']
    judge_name = request.form['judge_name']
    judge_username = request.form['judge_username']
    judge_password = request.form['judge_password']
    judge_type = request.form['judge_type']
    cursor.execute("UPDATE users SET name=%s, username=%s, password=%s, user_type=%s WHERE userID=%s", ({judge_name}, {judge_username}, {judge_password}, {judge_type}, {judge_id}))
    mysql.connection.commit()
    flash(f"Judge Updated: name - {judge_name}")
    return redirect(url_for('index'))

@app.route('/judgeDelete', methods=['POST'])
def delete_judge():
    cursor = mysql.connection.cursor()
    judge_id = request.form['judge_id']
    judge_name = request.form['judge_name']
    cursor.execute(f"DELETE FROM users WHERE userID={judge_id}")
    mysql.connection.commit()
    flash(f"judge name {judge_name} deleted")
    return redirect(url_for('index'))

@app.route('/addSegment', methods=['POST'])
def add_Segment():
    cursor = mysql.connection.cursor()
    # Handle candidate addition logic here
    segmentid = request.form['segment_id']
    segment_name = request.form['segment_name']
    cursor.execute("INSERT INTO segments (segmentID, name) VALUES (%s, %s)", ({segmentid}, {segment_name}))
    mysql.connection.commit()
    flash(f"Segment added: name - {segment_name}")
    return redirect(url_for('index'))

@app.route('/updateSegment', methods=['POST'])
def update_Segment():
    cursor = mysql.connection.cursor()
    # Handle candidate addition logic here
    segmentid = request.form['segment_id']
    segment_name = request.form['segment_name']
    cursor.execute("UPDATE segments SET name=%s WHERE segmentID=%s", ({segment_name}, {segmentid}))
    mysql.connection.commit()
    flash(f"Segment updated: name - {segment_name}")
    return redirect(url_for('index'))

@app.route('/deleteSegment', methods=['POST'])
def delete_Segment():
    cursor = mysql.connection.cursor()
    # Handle candidate addition logic here
    segmentid = request.form['segment_id']
    segment_name = request.form['segment_name']
    cursor.execute("DELETE FROM segments WHERE segmentID=%s", ({segmentid}))
    mysql.connection.commit()
    flash(f"Segment deleted: name - {segment_name}")
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('username', None)
    session.pop('is_admin', None)
    session.pop('user_id', None)
    session.pop('name', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
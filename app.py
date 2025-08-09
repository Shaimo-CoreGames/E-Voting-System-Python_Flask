from flask import Flask
from flask_mysqldb import MySQL
from flask_session import Session
from flask import render_template, request, redirect, session, flash, url_for
# from werkzeug.security import generate_password_hash, check_password_hash
import MySQLdb.cursors
from flask import jsonify
from datetime import timedelta
def make_session_permanent():
    session.permanent = True
    app.permanent_session_lifetime = timedelta(minutes=30)  # or however long you want


app = Flask(__name__)

# MySQL Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'SL@serverroot'
app.config['MYSQL_DB'] = 'evoting_db'

# Session Configuration
app.config['SESSION_TYPE'] = 'filesystem'
app.secret_key = '123'

mysql = MySQL(app)
Session(app)


@app.route('/')
def index():
    return render_template('index.html')

def query_db(query, args=(), one=False):
    cur = mysql.connection.cursor()
    cur.execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

@app.route('/register', methods=['GET', 'POST'])
def register():
    role = request.args.get('role')  # 'voter' or 'admin'
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        cnic = request.form['cnic']

        is_admin = 1 if role == 'admin' else 0

        # CNIC validation
        if not cnic.isdigit() or len(cnic) != 13:
            flash('CNIC must be exactly 13 digits.')
            return redirect(url_for('register', role=role))

        cur = mysql.connection.cursor()

        # Only one admin allowed
        if is_admin:
            existing_admin = query_db("SELECT * FROM Users WHERE is_admin = 1", one=True)
            if existing_admin:
                flash("An admin already exists. Only one admin allowed.")
                return redirect(url_for('register', role=role))

        # Check for duplicate username or CNIC
        cur.execute("SELECT * FROM Users WHERE username = %s OR cnic = %s", (username, cnic))
        existing_user = cur.fetchone()
        if existing_user:
            flash("Username or CNIC already exists.")
            cur.close()
            return redirect(url_for('register', role=role))

        # Register new user
        try:
            cur.execute(
                "INSERT INTO Users (username, password, cnic, is_admin) VALUES (%s, %s, %s, %s)",
                (username, password, cnic, is_admin)
            )
            mysql.connection.commit()
            flash('Registration successful. Please log in.')
            return redirect(url_for('login'))
        except Exception as e:
            flash("Error during registration.")
            print(e)
            return redirect(url_for('register', role=role))
        finally:
            cur.close()

    selected_role = 1 if role == 'admin' else 0
    return render_template('register.html', selected_role=selected_role)

@app.route('/login', methods=['GET', 'POST'])
def login():
    print("Login endpoint hit. Method:", request.method, "User type:", request.args.get('user_type'))

    user_type = request.args.get('user_type', 'voter')  # default: voter

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cur.execute("SELECT * FROM Users WHERE username = %s", (username,))
        user = cur.fetchone()
        cur.close()

        # ⚠️ Plain-text password comparison (not recommended for production)
        if user and user['password'] == password:
            if user_type == 'admin' and user['is_admin'] != 1:
                flash('You are not authorized as Admin.')
                return redirect(url_for('login', user_type='admin'))

            session['loggedin'] = True
            session['username'] = user['username']
            session['user_id'] = user['id']
            session['is_admin'] = int(user['is_admin'])  # not as string

            return redirect(url_for('dashboard'))

        else:
            flash('Invalid username or password.')
            return redirect(url_for('login', user_type=user_type))

    return render_template('login.html', user_type=user_type)

@app.route('/dashboard')
def dashboard():
    # Check if user is logged in
    if 'username' not in session:
        flash("Please login to access the dashboard.", "warning")
        return redirect('/login')

    username = session['username']
    is_admin = int(session.get('is_admin', 0))  # Ensure it's an integer

    flash(f"Welcome back, {username}!", "success")

    if is_admin == 1:
        return render_template('adminDashboard.html', username=username, is_admin=True)
    else:
        return render_template('voterDashboard.html', username=username, is_admin=False)


@app.route('/admin/add_province', methods=['GET', 'POST'])
def add_province():
    if not session.get('is_admin'):
        flash("Access denied.")
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        name = request.form['name']
        cur = mysql.connection.cursor()
        try:
            cur.execute("INSERT INTO Provinces (name) VALUES (%s)", (name,))
            mysql.connection.commit()
            flash("Province added successfully.")
        except:
            flash("Province already exists.")
        finally:
            cur.close()
        return redirect(url_for('add_province'))

    return render_template('addProvince.html')

@app.route('/admin/add_district', methods=['GET', 'POST'])
def add_district():
    # Check admin access
    if not session.get('is_admin'):
        flash("Access denied.")
        return redirect(url_for('dashboard'))

    cur = mysql.connection.cursor()
    
    # Fetch all provinces to show in the dropdown
    cur.execute("SELECT id, name FROM Provinces")
    provinces = cur.fetchall()

    if request.method == 'POST':
        name = request.form['name']
        province_id = request.form['province_id']

        try:
            # Insert new district
            cur.execute("INSERT INTO Districts (name, province_id) VALUES (%s, %s)", (name, province_id))
            mysql.connection.commit()
            flash("District added successfully.")
        except:
            flash("Error while adding district.")
        return redirect(url_for('add_district'))

    cur.close()
    return render_template('addDistrict.html', provinces=provinces)

@app.route('/admin/add_candidate', methods=['GET', 'POST'])
def add_candidate():
    if not session.get('is_admin'):
        flash("Access denied.")
        return redirect(url_for('dashboard'))

    cur = mysql.connection.cursor()

    # Fetch provinces and districts
    cur.execute("SELECT id, name FROM Provinces")
    provinces = cur.fetchall()

    cur.execute("SELECT id, name FROM Districts")
    districts = cur.fetchall()

    if request.method == 'POST':
        name = request.form['name']
        type_ = request.form['type']
        province_id = request.form['province_id']
        district_id = request.form['district_id']

        cur.execute("INSERT INTO Candidates (name, type, province_id, district_id) VALUES (%s, %s, %s, %s)",
                    (name, type_, province_id, district_id))
        mysql.connection.commit()
        flash("Candidate added successfully.")
        return redirect(url_for('add_candidate'))

    cur.close()
    return render_template('addCandidate.html', provinces=provinces, districts=districts)

@app.route('/get_districts/<int:province_id>')
def get_districts(province_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT id, name FROM Districts WHERE province_id = %s", (province_id,))
    districts = cur.fetchall()
    cur.close()

    return jsonify(districts)
@app.route('/submit_vote', methods=['POST'])
def submit_vote():
    if 'user_id' not in session:
        flash('Please login first to vote.', 'warning')
        return redirect('/login')

    candidate_id = request.form.get('candidate_id')
    voter_id = session['user_id']

    conn = mysql.connection
    cursor = conn.cursor()

    # ✅ Get candidate role based on selected candidate
    cursor.execute("SELECT role FROM Candidates WHERE id = %s", (candidate_id,))
    result = cursor.fetchone()

    if not result:
        flash("Invalid candidate selected.", "danger")
        return redirect('/dashboard')

    candidate_role = result[0]  # This will be 'MPA' or 'MNA'

    # ✅ Check if user already voted for this role
    cursor.execute("""
        SELECT * FROM Votes 
        WHERE voter_id = %s 
        AND candidate_id IN (SELECT id FROM Candidates WHERE role = %s)
    """, (voter_id, candidate_role))
    already_voted = cursor.fetchone()

    if already_voted:
        flash("You have already voted for this position!", "danger")
        return redirect('/dashboard')

    # ✅ Update vote count
    cursor.execute("UPDATE Candidates SET votes = votes + 1 WHERE id = %s", (candidate_id,))

    # ✅ Insert into Votes table
    cursor.execute("INSERT INTO Votes (candidate_id, voter_id) VALUES (%s, %s)", (candidate_id, voter_id))

    conn.commit()
    cursor.close()

    flash("Vote submitted successfully!", "success")
    return redirect('/dashboard')

@app.route('/cast_vote/<int:candidate_id>') 
def cast_vote(candidate_id):
    user_cnic = session.get('cnic')
    if not user_cnic:
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()

    # Get candidate type (MPA or MNA)
    cur.execute("SELECT type FROM Candidates WHERE id = %s", (candidate_id,))
    candidate = cur.fetchone()
    if not candidate:
        return "Candidate not found", 404

    position = candidate[0]  # 'MPA' or 'MNA'

    # Check if user has already voted for this position
    cur.execute("SELECT * FROM Votes WHERE cnic = %s AND vote_type = %s", (user_cnic, position))
    existing_vote = cur.fetchone()
    if existing_vote:
        return "You have already voted for " + position

    # Cast vote
    cur.execute("INSERT INTO Votes (cnic, candidate_id, vote_type) VALUES (%s, %s, %s)",
                (user_cnic, candidate_id, position))
    
    # Optional: only if 'votes' column exists
    cur.execute("UPDATE Candidates SET votes = votes + 1 WHERE id = %s", (candidate_id,))
    
    mysql.connection.commit()
    cur.close()

    return render_template('voteCasted.html')

@app.route('/vote/<position>/<int:region_id>')
def vote_by_region_and_position(position, region_id):
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if position == 'MPA':
        cur.execute("SELECT id, name, type FROM Candidates WHERE type='MPA' AND district_id=%s", (region_id,))
    else:
        cur.execute("SELECT id, name, type FROM Candidates WHERE type='MNA' AND province_id=%s", (region_id,))

    candidates = cur.fetchall()
    cur.close()
    return render_template('showCandidates.html', candidates=candidates, position=position)










@app.route('/select_region/<vote_type>')
def select_region(vote_type):
    cur = mysql.connection.cursor()
    if vote_type == 'MPA':
        cur.execute("SELECT id, name FROM Provinces")
    elif vote_type == 'MNA':
        cur.execute("SELECT id, name FROM Provinces")
    provinces = cur.fetchall()
    cur.close()
    return render_template('region.html', region=provinces, vote_type=vote_type)

@app.route('/select_district/<int:province_id>/<vote_type>')
def select_district(province_id, vote_type):
    cur = mysql.connection.cursor()
    cur.execute("SELECT id, name FROM Districts WHERE province_id = %s", (province_id,))
    districts = cur.fetchall()
    cur.close()
    return render_template('districts.html', districts=districts, vote_type=vote_type)

@app.route('/vote/MPA/<int:district_id>', methods=['GET', 'POST'])
def vote_mpa_submit(district_id):
    if request.method == 'POST':
        candidate_id = request.form.get('candidate')
        if candidate_id:
            cursor = mysql.connection.cursor()
            # ✅ correct
            cursor.execute("INSERT INTO Votes (candidate_id, voter_id) VALUES (%s, %s)", (candidate_id, session['user_id']))

            mysql.connection.commit()
            cursor.close()
            return f"MPA Vote submitted for candidate ID {candidate_id} in district {district_id}"
        return "No candidate selected."

    # GET: Show MPA candidates from the given district
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM Candidates WHERE type='MPA' AND district_id=%s", (district_id,))
    candidates = cursor.fetchall()
    cursor.close()
    return render_template("vote_mpa.html", candidates=candidates, district_id=district_id)

@app.route('/vote/MNA/<int:province_id>', methods=['GET', 'POST'])
def vote_mna_submit(province_id):
    if request.method == 'POST':
        candidate_id = request.form.get('candidate')
        if candidate_id:
            voter_id = session['user_id']  # ✅ FIXED: Define voter_id from session
            cursor = mysql.connection.cursor()
            cursor.execute("INSERT INTO Votes (candidate_id, voter_id) VALUES (%s, %s)", (candidate_id, voter_id))
            mysql.connection.commit()
            cursor.close()
            return f"MNA Vote submitted for candidate ID {candidate_id} in province {province_id}"
        return "No candidate selected."

    # GET: Show candidate selection
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM Candidates WHERE type='MNA' AND province_id=%s", (province_id,))
    candidates = cursor.fetchall()
    cursor.close()
    return render_template("vote_mna.html", candidates=candidates, province_id=province_id)

@app.route('/results')
def results():
    if 'user_id' not in session:
        flash("Please login to view results.", "warning")
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()

    # Fetch all MPA candidates
    cur.execute("SELECT * FROM Candidates WHERE type='MPA'")
    mpa_candidates = cur.fetchall()

    # Fetch all MNA candidates
    cur.execute("SELECT * FROM Candidates WHERE type='MNA'")
    mna_candidates = cur.fetchall()

    # ✅ CM: Top MPA per province (use subquery)
    cur.execute("""
        SELECT c1.province_id, c1.name, c1.votes
        FROM Candidates c1
        JOIN (
            SELECT province_id, MAX(votes) AS max_votes
            FROM Candidates
            WHERE type = 'MPA'
            GROUP BY province_id
        ) c2 ON c1.province_id = c2.province_id AND c1.votes = c2.max_votes
        WHERE c1.type = 'MPA'
    """)
    cm_results = cur.fetchall()

    # ✅ PM: Top MNA overall
    cur.execute("""
        SELECT name, votes 
        FROM Candidates 
        WHERE type = 'MNA'
        ORDER BY votes DESC 
        LIMIT 1
    """)
    pm_result = cur.fetchone()

    cur.close()

    return render_template(
        'results.html',
        mpa_candidates=mpa_candidates,
        mna_candidates=mna_candidates,
        cm_results=cm_results,
        pm_result=pm_result
    )





@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
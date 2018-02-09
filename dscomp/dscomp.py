import os
import sqlite3
from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash, redirect
import pandas as pd
from sklearn.model_selection import train_test_split 
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = set(['csv'])

app = Flask(__name__)
app.config.from_object(__name__)

UPLOAD_FOLDER = os.path.join(app.root_path, 'csvs')
app.config.update(dict(
    DATABASE = os.path.join(app.root_path, 'dscomp.db'),
    SECRET_KEY = 'devkey',
    USERNAME = 'admin',
    PASSWORD = 'default',
    UPLOAD_FOLDER = UPLOAD_FOLDER
))

app.config.from_envvar('FLASKR_SETTINGS', silent=True)

def connect_db():
    rv = sqlite3.connect(app.config['DATABASE'])
    rv.row_factory = sqlite3.Row
    return rv

def get_db():
    """Opens a new database connection if one does not already exist."""
    if not hasattr(g, 'sqlite_db'):
        g.sqlite_db = connect_db()
    return g.sqlite_db

@app.teardown_appcontext
def close_db(error):
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()

def init_db():
    db = get_db()
    with app.open_resource('schema.sql', mode = 'r') as f:
        db.cursor().executescript(f.read())
    db.commit()

@app.cli.command('initdb')
def initdb_command():
    """Initializes the database."""
    init_db()
    print('Initialized the database')

def query_db(query, args=(), one=False):
    """Queries the database and returns a list of dictionaries."""
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    return (rv[0] if rv else None) if one else rv

def get_user_id(username):
    """Convenience method to look up the id for a username."""
    rv = query_db('select userid from users where username = ?', [username], one=True)
    return rv[0] if rv else None

@app.before_request
def before_request():
    g.user = None
    if 'userid' in session:
        g.user = query_db('select * from users where userid = ?',
	[session['userid']], one=True)

@app.route('/')
def show_index():
    db = get_db()
    cur = db.execute('select subid, userid, publicscore from submissions order by publicscore desc limit 10')
    entries = cur.fetchall()
    return render_template('index.html')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

from sklearn.metrics import mean_squared_error

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        csvFile = request.files['file']
        if csvFile.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if csvFile and allowed_file(csvFile.filename):
            filename = secure_filename(csvFile.filename)
            user_csv = pd.read_csv(csvFile)
            scoring_csv = pd.read_csv(os.path.join(app.root_path, "privatecsvs/true_labels.csv"))
            publicCSV, privateCSV = train_test_split(scoring_csv, test_size = 0.5, random_state = os.getenv('RAND_SEED', 0))
            joinedCSV = publicCSV.merge(user_csv, on='index_num', how='inner')
            print(mean_squared_error(joinedCSV['label'].values, joinedCSV['true_label'].values))
            #print(pd.read_csv(csvFile).head)
            print(joinedCSV)
            csvFile.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            return redirect(url_for('uploaded_file', filename=filename))
    return render_template('upload.html') 

from flask import send_from_directory

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'],
                               filename)


from passlib.hash import pbkdf2_sha256 as sha256
 
def generate_password_hash(plaintext):
    return sha256.encrypt(plaintext, rounds=200000, salt_size=16)

def check_password_hash(plaintext, pwhash):
    return sha256.verify(plaintext, pwhash)
    
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Logs the user in."""
    if g.user:
        return redirect(url_for('show_index'))
    error = None
    if request.method == 'POST':
        user = query_db('''select * from users where
            username = ?''', [request.form['username']], one=True)
        if user is None:
            error = 'Invalid username'
        elif not check_password_hash(request.form['password'],
                user['password']):
            error = 'Invalid password'
        else:
            flash('You were logged in')
            session['userid'] = user['userid']
            return redirect(url_for('show_index'))
    return render_template('login.html', error=error)


@app.route('/register', methods=['GET', 'POST'])
def register():
    """Registers the user."""
    if g.user:
        return redirect(url_for('show_index'))
    error = None
    if request.method == 'POST':
        if not request.form['username']:
            error = 'You have to enter a username'
        elif not request.form['email'] or \
                '@' not in request.form['email']:
            error = 'You have to enter a valid email address'
        elif not request.form['password']:
            error = 'You have to enter a password'
        elif request.form['password'] != request.form['password2']:
            error = 'The two passwords do not match'
        elif get_user_id(request.form['username']) is not None:
            error = 'The username is already taken'
        else:
            db = get_db()
            db.execute('''insert into users (
              username, email, name, password) values (?, ?, ?, ?)''',
              [request.form['username'], request.form['email'], request.form['name'],
               generate_password_hash(request.form['password'])])
            db.commit()
            flash('You were successfully registered and can login now')
            return redirect(url_for('login'))
    return render_template('register.html', error=error)

@app.route('/logout')
def logout():
    """Logs the user out."""
    flash('You were logged out')
    session.pop('userid', None)
    return redirect(url_for('show_index'))

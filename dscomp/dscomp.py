import os
import sqlite3
from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash, redirect
from flask_misaka import Misaka
import pandas as pd
from sklearn.model_selection import train_test_split 
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = set(['csv'])
N_SUBMISSIONS_PER_DAY = 1

app = Flask(__name__)
Misaka(app)
app.config.from_object(__name__)

UPLOAD_FOLDER = os.path.join(app.root_path, 'csvs')
PRIVATECSV_FOLDER = os.path.join(app.root_path, 'privatecsvs')

app.config.update(dict(
    DATABASE = os.path.join(app.root_path, 'dscomp.db'),
    SECRET_KEY = 'devkey',
    USERNAME = 'admin',
    PASSWORD = 'default',
    UPLOAD_FOLDER = UPLOAD_FOLDER,
    PRIVATECSV_FOLDER = PRIVATECSV_FOLDER
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

@app.before_request
def before_request():
    g.user = None
    if 'userid' in session:
        g.user = query_db('select * from users where userid = ?',
	[session['userid']], one=True)

@app.route('/leaderboard')
def leaderboard():
    db = get_db()
    cur = db.execute('select users.name, min(publicscore) as publicscore, count(subid) as numsubs, datetime(timestamp) as timestamp from submissions inner join users on users.userid = submissions.userid group by submissions.userid order by publicscore asc limit 20')
    entries = cur.fetchall()
    return render_template('leaderboard.html', entries=entries)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

from sklearn.metrics import mean_squared_error
import datetime

@app.route('/', methods=['GET'])
def about():
    about = query_db('''select content from pages where page = 'about';''', one = True)
    return render_template('about.html', about = about)

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    error = None
    if not g.user:
        return redirect(url_for('login')) 
    if request.method == 'POST':
        subs_today = query_db('''select * from submissions where userid = ? and strftime('%m - %d', timestamp) = strftime('%m - %d', 'now')''',
                [g.user['userid']])
        if subs_today is not None and len(subs_today) >= N_SUBMISSIONS_PER_DAY:
            error = 'Already have {} submission(s) today (resets at midnight UTC)'.format(N_SUBMISSIONS_PER_DAY)
            return render_template('upload.html', error=error)
        if 'file' not in request.files:
            error = 'Must select a file'
            return render_template('upload.html', error=error)
        csvFile = request.files['file']
        if csvFile.filename == '':
            error = 'Must select a file'
            return render_template('upload.html', error=error)
        if not allowed_file(csvFile.filename):
            error = 'Must upload a csv file.'
            return render_template('upload.html', error=error)
        if csvFile and allowed_file(csvFile.filename):
            try:
                filename = secure_filename(csvFile.filename)
                csvFile.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                user_csv = pd.read_csv(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                scoring_csv = pd.read_csv(os.path.join(app.config['PRIVATECSV_FOLDER'], "test_labels.csv"))
                publicCSV, privateCSV = train_test_split(scoring_csv, test_size = 0.5, random_state = os.getenv('RAND_SEED', 0))
                publicMerged = publicCSV.merge(user_csv, on='index_num', how='inner')
                privateMerged = privateCSV.merge(user_csv, on = 'index_num', how='inner')
                publicMSE = mean_squared_error(publicMerged['label'].values, publicMerged['true_label'].values)
                privateMSE = mean_squared_error(privateMerged['label'].values, privateMerged['true_label'].values)
                db = get_db()
                db.execute('''insert into submissions (
                  userid, timestamp, privatescore, publicscore) values (?, ?, ?, ?)''',
                  [g.user['userid'], datetime.datetime.utcnow(), privateMSE, publicMSE])
                db.commit()
                return redirect(url_for('recent_submission'))
            except Exception as ex:
                print(str(ex))
                error = 'There was an error reading your submission. Make sure you read the submission styling guidelines carefully. If you think it''s an error on our end, please contact us and describe the error to the best of your ability.'
                return render_template('upload.html', error=error)
    return render_template('upload.html') 

from flask import send_from_directory

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    print("test")
    return send_from_directory(os.path.join(app.root_path,
                               'csvs'), filename)

@app.route('/submissions/recent')
def recent_submission():
    if not g.user:
        return redirect(url_for('login'))
    submission = query_db('select subid, publicscore, timestamp from submissions where submissions.userid = ? order by timestamp desc limit 1', [g.user['userid']], one=True)
    return render_template('recent.html', submission=submission)

from passlib.hash import pbkdf2_sha256 as sha256
 
def generate_password_hash(plaintext):
    return sha256.encrypt(plaintext, rounds=200000, salt_size=16)

def check_password_hash(plaintext, pwhash):
    return sha256.verify(plaintext, pwhash)

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if g.user['admin']==0:
        return redirect(url_for('about'))
    if not request.method == 'POST':
        db = get_db()
        cur = db.execute('select users.name, min(privatescore) as privatescore, count(subid) as numsubs, datetime(timestamp) as timestamp from submissions inner join users on users.userid = submissions.userid group by submissions.userid order by privatescore asc limit 20')
        entries = cur.fetchall()
        return render_template('admin.html', entries = entries)
    filetypes = [inputlabel for inputlabel in request.files]
    if len(filetypes) == 0:
        error = 'Must select a file'
        return render_template('admin.html', error=error) 
    if len(filetypes) > 1:
        error = 'Must upload files one at a time'
        return render_template('admin.html', error=error)
    csvFile = request.files[filetypes[0]]
    if csvFile.filename == '':
        error = 'Must select a file'
        return render_template('admin.html', error=error)
    if not allowed_file(csvFile.filename):
        error = 'Must upload a csv file.'
        return render_template('admin.html', error=error)
    if csvFile and allowed_file(csvFile.filename):
        try:
            input_to_filename = {
                    'testnolabels': os.path.join(app.config['UPLOAD_FOLDER'], 'test.csv'),
                    'train': os.path.join(app.config['UPLOAD_FOLDER'], 'train.csv'),
                    'testlabels': os.path.join(app.config['PRIVATECSV_FOLDER'], 'test_labels.csv')
            }
            if filetypes[0] in input_to_filename.keys():
                csvFile.save(input_to_filename[filetypes[0]])
                return redirect(url_for('data'))
            else:
                error = 'Must use the approved file inputs.'
                return render_template('admin.html', error=error)
        except Exception as ex:
            error = 'Something unknown went wrong, contact us.'
            return render_template('admin.html', error=error)
    return render_template('admin.html')

@app.route('/data', methods=['GET', 'POST'])
def data():
    content = query_db('''select content from pages where page = 'train' or page = 'test';''')
    return render_template('data.html', content=content)

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    """Logs the user in."""
    if g.user:
        return redirect(url_for('about'))
    if request.method == 'POST':
        user = query_db('''select * from users where
            email = ?''', [request.form['email']], one=True)
        if user is None:
            error = 'Invalid email'
        elif not check_password_hash(request.form['password'],
                user['password']):
            error = 'Invalid password'
        else:
            session['userid'] = user['userid']
            return redirect(url_for('about'))
    return render_template('login.html', error=error)

ADMIN_SECRET = 'admin'

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Registers the user."""
    if g.user:
        return redirect(url_for('about'))
    error = None
    if request.method == 'POST':
        if not request.form['email'] or \
                '@' not in request.form['email']:
            error = 'You have to enter a valid email address'
        elif not request.form['password']:
            error = 'You have to enter a password'
        elif request.form['password'] != request.form['password2']:
            error = 'The two passwords do not match'
        elif not request.form['email'].lower().endswith('uidaho.edu'):
            error = 'You must have a uidaho email address to compete.'
        elif query_db('''select * from users where email = ?''', [request.form['email'].lower()], one=True) is not None:
            error = 'That email is already in use'
        else:
            db = get_db()
            if request.form['admin'] == ADMIN_SECRET:
                admin = 1
            else:
                admin = 0
            db.execute('''insert into users (
              email, name, password, admin) values (?, ?, ?, ?)''',
              [request.form['email'].lower(), request.form['fullname'],
               generate_password_hash(request.form['password']), admin])
            db.commit()
            return redirect(url_for('login'))
    return render_template('register.html', error=error)

@app.route('/logout')
def logout():
    """Logs the user out."""
    flash('You were logged out')
    session.pop('userid', None)
    return redirect(url_for('about'))

import os
import sqlite3
from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash, redirect
import pandas as pd
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

@app.route('/')
def show_index():
    db = get_db()
    cur = db.execute('select subid, userid, publicscore from submissions order by publicscore desc limit 10')
    entries = cur.fetchall()
    return render_template('index.html')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


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
            print(pd.read_csv(csvFile).head)
            csvFile.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            return redirect(url_for('uploaded_file', filename=filename))
    return '''
        <!doctype html>
        <title>Upload new File</title>
        <h1>Upload new File</h1>
        <form method=post enctype=multipart/form-data>
        <p><input type=file name=file>
        <input type=submit value=Upload>
        </form>
        '''

from flask import send_from_directory

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'],
                               filename)

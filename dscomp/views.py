import os
from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash, redirect, send_from_directory
import pandas as pd
from sklearn.model_selection import train_test_split 
from werkzeug.utils import secure_filename
from sklearn.metrics import mean_squared_error
import datetime
from dscomp.utilities.security import allowed_file, generate_password_hash, check_password_hash
from dscomp.utilities.database import *
from dscomp import app

N_SUBMISSIONS_PER_DAY = 1

@app.before_request
def before_request():
    g.user = None
    if 'userid' in session:
        g.user = query_db('select * from users where userid = ?',
	[session['userid']], one=True)

@app.route('/', methods=['GET'])
def about():
    about = query_db('''select content from pages where page = 'about';''', one = True)
    return render_template('about.html', about = about)

@app.route('/admin/leaderboard', methods=['GET'])
def admin_leaderboard():
    entries = query_db('select users.name, min(privatescore) as privatescore, count(subid) as numsubs, datetime(timestamp) as timestamp from submissions inner join users on users.userid = submissions.userid group by submissions.userid order by privatescore asc limit 20')
    return render_template('admin_leaderboard.html', entries = entries)

@app.route('/admin/edit', methods=['GET', 'POST'])
def admin_edit():
    if request.method == 'GET':
        all_pages = query_db('select page, content from pages')
        pages = {page: content for (page, content) in all_pages}
        return render_template('admin_edit.html', pages=pages)
    for page in request.form.keys():
        db = get_db()
        cur = db.execute('update pages set content = ? where page = ?',
                [request.form[page], page])
        db.commit()
    return redirect(url_for('admin_edit'))

@app.route('/admin/upload', methods=['GET', 'POST'])
def admin_upload():
    if g.user['admin'] == 0:
        return redirect(url_for('about'))
    if request.method == "GET":
        return render_template('admin_upload.html')
    filetypes = [inputlabel for inputlabel in request.files]
    error = None
    if len(filetypes) == 0:
        error = 'Must select a file'
    if len(filetypes) > 1:
        error = 'Must upload files one at a time'
    csvFile = request.files[filetypes[0]]
    if csvFile.filename == '' or not csvFile:
        error = 'Must select a file'
    if not allowed_file(csvFile.filename):
        error = 'Must upload a csv file.'
    if error is not None:
        return render_template('admin_upload.html', error=error) 
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
            return render_template('admin_upload.html', error=error)
    except Exception as ex:
        error = 'Something unknown went wrong, contact us.'
        return render_template('admin_upload.html', error=error)
    return render_template('admin_upload.html')

@app.route('/data', methods=['GET'])
def data():
    content = query_db('''select content from pages where page = 'train' or page = 'test';''')
    return render_template('data.html', content=content)

@app.route('/leaderboard')
def leaderboard():
    entries = query_db('select users.name, min(publicscore) as publicscore, count(subid) as numsubs, datetime(timestamp) as timestamp from submissions inner join users on users.userid = submissions.userid group by submissions.userid order by publicscore asc limit 20')
    return render_template('leaderboard.html', entries=entries)

@app.route('/scoring', methods=['GET'])
def scoring():
    content = query_db('''select content from pages where page = 'scoring';''', one=True)
    return render_template('scoring.html', content=content)

@app.route('/submissions')
def submissions():
    if not g.user:
        return redirect(url_for('login'))
    submissions = query_db('select subid, publicscore, timestamp, notes from submissions where submissions.userid = ? order by timestamp desc', [g.user['userid']])
    return render_template('submissions.html', submissions=submissions)

@app.route('/submissions/recent')
def recent_submission():
    if not g.user:
        return redirect(url_for('login'))
    submission = query_db('select subid, publicscore, timestamp from submissions where submissions.userid = ? order by timestamp desc limit 1', [g.user['userid']], one=True)
    return render_template('recent.html', submission=submission)

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    error = None
    if not g.user:
        return redirect(url_for('login')) 
    if request.method == 'GET':
        return render_template('upload.html')
    subs_today = query_db('''select * from submissions where userid = ? and strftime('%m - %d', timestamp) = strftime('%m - %d', 'now')''',
            [g.user['userid']])
    if subs_today is not None and len(subs_today) >= N_SUBMISSIONS_PER_DAY:
        error = 'Already have {} submission(s) today (resets at midnight UTC)'.format(N_SUBMISSIONS_PER_DAY)
    if 'file' not in request.files:
        error = 'Must select a file'
    csvFile = request.files['file']
    if csvFile.filename == '' or not csvFile:
        error = 'Must select a file'
    if not allowed_file(csvFile.filename):
        error = 'Must upload a csv file.' 
    if error is not None:
        return render_template('upload.html', error=error)
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
          userid, timestamp, privatescore, publicscore, notes) values (?, ?, ?, ?, ?)''',
          [g.user['userid'], datetime.datetime.utcnow(), privateMSE, publicMSE, request.form['notes']])
        db.commit()
        return redirect(url_for('recent_submission'))
    except Exception as ex:
        print(str(ex))
        error = 'There was an error reading your submission. Make sure you read the submission styling guidelines carefully. If you think it''s an error on our end, please contact us and describe the error to the best of your ability.'
        return render_template('upload.html', error=error)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(os.path.join(app.root_path,
                               'csvs'), filename)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Logs the user in."""
    error = None
    if g.user:
        return redirect(url_for('about'))
    if request.method == 'GET':
        return render_template('login.html')
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
            if request.form['admin'] == os.getenv("ADMIN_SECRET", "admin"):
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

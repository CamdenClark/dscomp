import os
import uuid
import random
from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash, redirect, send_from_directory
import pandas as pd
from sklearn.model_selection import train_test_split 
from werkzeug.utils import secure_filename
from sklearn.metrics import accuracy_score 
import datetime
from dscomp.utilities.security import allowed_file, generate_password_hash, check_password_hash, send_code
from dscomp.utilities.database import *
from dscomp import app, limiter

N_SUBMISSIONS_PER_DAY = 5

@app.before_request
def before_request():
    g.user = None
    if 'userid' in session:
        g.user = query_db('select * from users where userid = %s', (session['userid'],), one=True)

@app.route('/', methods=['GET'])
def about():
    about = query_db('''select content from pages where page = 'about';''', one = True)
    return render_template('about.html', about = about)

@app.route('/admin/dataviz', methods=['GET'])
def admin_dataviz():
    if g.user['confirmed'] == 0:
        return redirect(url_for('confirmation'))
    if not g.user or not g.user['admin'] == 1:
        return redirect(url_for('admin'))
    entries = query_db('select users.name, timestamp, uuid, extension, notes from submissions inner join users on users.userid = submissions.userid where isDataViz = 1 order by timestamp desc')
    return render_template('admin_dataviz.html', entries = entries)

@app.route('/admin/leaderboard', methods=['GET'])
def admin_leaderboard():
    if not g.user or not g.user['admin'] == 1:
        return redirect(url_for('about'))
    if g.user['confirmed'] == 0:
        return redirect(url_for('confirmation'))
    entries = query_db('select users.name, max(privatescore) as privatescore, count(subid) as numsubs, uuid, extension, timestamp from submissions inner join users on users.userid = submissions.userid where isDataViz = 0 group by submissions.userid order by privatescore desc limit 20')
    return render_template('admin_leaderboard.html', entries = entries)

@app.route('/admin/edit', methods=['GET', 'POST'])
def admin_edit():
    if not g.user or not g.user['admin'] == 1:
        return redirect(url_for('about'))
    if g.user['confirmed'] == 0:
        return redirect(url_for('confirmation'))
    if request.method == 'GET':
        all_pages = query_db('select page, content from pages')
        all_pages = {page['page']: page['content'] for page in all_pages} 
        return render_template('admin_edit.html', pages=all_pages)
    for page in request.form.keys():
        db = get_db()
        cur = db.cursor()
        cur.execute('update pages set content = %s where page = %s',
                (request.form[page], page))
        db.commit()
    return redirect(url_for('admin_edit'))

@app.route('/admin/upload', methods=['GET', 'POST'])
def admin_upload():
    if not g.user or not g.user['admin'] == 1:
        return redirect(url_for('about'))
    if g.user['confirmed'] == 0:
        return redirect(url_for('confirmation'))
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
                'testlabels': os.path.join(app.config['PRIVATECSV_FOLDER'], 'test_labels.csv'),
                'vizdata': os.path.join(app.config['UPLOAD_FOLDER'], 'vizdata.csv')
        }
        if filetypes[0] in input_to_filename.keys():
            csvFile.save(input_to_filename[filetypes[0]])
            return redirect(url_for('data'))
        else:
            error = 'Must use the approved file inputs.'
            return render_template('admin_upload.html', error=error)
    except Exception as ex:
        app.logger.error(ex)
        error = 'Something unknown went wrong, contact us.'
        return render_template('admin_upload.html', error=error)
    return render_template('admin_upload.html')

@app.route('/data', methods=['GET'])
def data():
    content = query_db('''select content from pages where page = 'train' or page = 'test' or page = 'dataviz';''')
    return render_template('data.html', content=content)

@app.route('/leaderboard')
def leaderboard():
    entries = query_db('select users.name, max(publicscore) as publicscore, count(subid) as numsubs, timestamp from submissions inner join users on users.userid = submissions.userid where isDataViz = 0 group by submissions.userid order by publicscore desc limit 20')
    return render_template('leaderboard.html', entries=entries)

@app.route('/scoring', methods=['GET'])
def scoring():
    content = query_db('''select content from pages where page = 'scoring';''', one=True)
    return render_template('scoring.html', content=content)

@app.route('/submissions')
def submissions():
    if not g.user:
        return redirect(url_for('login'))
    if g.user['confirmed'] == 0:
        return redirect(url_for('confirmation'))
    submissions = query_db('select subid, publicscore, uuid, timestamp, notes, isDataViz from submissions where submissions.userid = %s order by timestamp desc', (g.user['userid'],))
    return render_template('submissions.html', submissions=submissions)

@app.route('/register/confirm/resend')
def resend_confirmation():
    if not g.user:
        return redirect(url_for('login'))
    if g.user['confirmed']:
        return redirect(url_for('about'))
    if request.method == 'GET':
        send_code(g.user['email'], g.user['code'])
        return redirect(url_for('about'))

@app.route('/register/confirm', methods=['GET', 'POST'])
def confirmation():
    if not g.user:
        return redirect(url_for('login'))
    if g.user['confirmed']:
        return redirect(url_for('about'))
    error = None
    if request.method == 'GET':
        return render_template('confirmation.html')
    if not request.form['confirm'] == g.user['code']:
        error = 'Invalid confirmation code.'
    else:
        db = get_db()
        db.cursor().execute('''update users set confirmed = %s where userid = %s''', (1, int(g.user['userid'])))
        db.commit()
        return redirect(url_for('about'))
    return render_template('confirmation.html', error=error)

@app.route('/reset', methods=['GET', 'POST'])
def reset_password():
    if g.user:
        return redirect(url_for('about'))
    error = None
    if request.method == 'GET':
        return render_template('reset_password.html')
    user = query_db('''select * from users where email = %s''', (request.form['email'], ), one=True)
    if not user:
        return render_template('reset_password.html', error = 'No account associated with that email.')
    code = str(uuid.uuid1())[:5]
    db = get_db()
    db.cursor().execute('''update users set code = %s where email = %s''', (code, user['email']))
    db.commit()
    send_code(user['email'], code, activation=False)
    return render_template('reset_password.html', success='Sent a link to reset your password')

@app.route('/reset/password', methods=['GET', 'POST'])
def reset_password_code():
    if g.user:
        return redirect(url_for('about'))
    if request.method == 'GET':
        return render_template('reset_password_code.html')
    user = query_db('select * from users where code = %s', (request.form['code'], ), one=True)
    if not user:
        return render_template('reset_password_code.html', error = 'Invalid code.')
    if not request.form['password']:
        return render_template('reset_password_code.html', error = 'You forgot a password.')
    if not request.form['password'] == request.form['password2']:
        return render_template('reset_password_code.html', error = 'Passwords don''t match.')
    hashed_pass = generate_password_hash(request.form['password'])
    db = get_db()
    db.cursor().execute('''update users set password = %s where userid = %s''', (hashed_pass, user['userid']))
    db.commit()
    return redirect(url_for('login'))

@app.route('/submissions/recent')
def recent_submission():
    if not g.user:
        return redirect(url_for('login'))
    submission = query_db('select subid, publicscore, timestamp from submissions where submissions.userid = %s order by timestamp desc limit 1', (g.user['userid'],), one=True)
    return render_template('recent.html', submission=submission)

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    error = None
    if not g.user:
        return redirect(url_for('login')) 
    if request.method == 'GET':
        return render_template('upload.html')
    subs_today = query_db('''select * from submissions where userid = %s and date(timestamp) = curdate()''',
            (g.user['userid'],))
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
        uuid_filename = str(uuid.uuid1())
        extension = csvFile.filename.split('.')[-1]
        filename = uuid_filename + "." + extension
        csvFile.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        db = get_db()
        if int(request.form['whichCompetition']) == 0:
            user_csv = pd.read_csv(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            scoring_csv = pd.read_csv(os.path.join(app.config['PRIVATECSV_FOLDER'], "test_labels.csv"))
            publicCSV, privateCSV = train_test_split(scoring_csv, test_size = 0.5, random_state = os.getenv('RAND_SEED', 0))
            publicMerged = publicCSV.merge(user_csv, on='index', how='inner')
            privateMerged = privateCSV.merge(user_csv, on = 'index', how='inner')
            publicAccuracy = accuracy_score(publicMerged['true_label'].values,publicMerged['label'].values)
            privateAccuracy = accuracy_score(privateMerged['true_label'].values, privateMerged['label'].values)
            db.cursor().execute('''insert into submissions (
          userid, timestamp, privatescore, publicscore, notes, uuid, isDataViz, extension) values (%s, %s, %s, %s, %s, %s, %s, %s)''',
          (g.user['userid'], datetime.datetime.utcnow(), float(privateAccuracy), float(publicAccuracy), request.form['notes'], uuid_filename, 0, extension))
            db.commit()
            return redirect(url_for('recent_submission'))
        else:
            db.cursor().execute('''insert into submissions (userid, timestamp, notes, uuid, isDataViz, extension) values (%s, %s, %s, %s, %s, %s)''', (g.user['userid'], datetime.datetime.utcnow(), request.form['notes'], uuid_filename, 1, extension))
            db.commit()
            return redirect(url_for('submissions'))
    except Exception as ex:
        app.logger.error(str(ex))
        error = 'There was an error reading your submission. Make sure you read the submission styling guidelines carefully. If you think it''s an error on our end, please contact us and describe the error to the best of your ability.'
        return render_template('upload.html', error=error)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    if g.user['admin'] == 1:
        return send_from_directory(os.path.join(app.root_path, 'csvs'), filename)
    if filename not in ['train.csv', 'test.csv', 'vizdata.csv']:
        return redirect(url_for('upload'))
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
        email = %s''', (request.form['email'],), one=True)
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
        elif query_db('''select * from users where email = %s''', (request.form['email'].lower(),), one=True) is not None:
            error = 'That email is already in use'
        else:
            code = str(uuid.uuid1())[:5] 
            send_code(request.form['email'], code)
            if request.form['admin'] == app.config['ADMIN_SECRET']:
                admin = 1
            else:
                admin = 0
            db = get_db()
            db.cursor().execute('''insert into users (
              email, name, password, admin, code, confirmed) values (%s, %s, %s, %s, %s, %s)''',
              (request.form['email'].lower(), request.form['fullname'],
               generate_password_hash(request.form['password']), admin, code, 0))
            db.commit()
            return redirect(url_for('login'))
    return render_template('register.html', error=error)

@app.route('/logout')
def logout():
    """Logs the user out."""
    session.pop('userid', None)
    return redirect(url_for('about'))

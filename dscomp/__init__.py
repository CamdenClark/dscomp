from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash, redirect, send_from_directory
import os
import sqlite3
from flask_misaka import Misaka

ADMIN_SECRET = 'admin'
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

import dscomp.views

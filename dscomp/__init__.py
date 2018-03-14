from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash, redirect, send_from_directory
import os
import sqlite3
from flask_misaka import Misaka

app = Flask(__name__)
Misaka(app)

app.config.from_object(__name__)

UPLOAD_FOLDER = os.path.join(app.root_path, 'csvs')
PRIVATECSV_FOLDER = os.path.join(app.root_path, 'privatecsvs')

app.config.update(dict(
    DATABASE = 'dscomp',
    DATABASE_HOST = 'localhost',
    USERNAME = 'admin',
    PASSWORD = 'default',
    SECRET_KEY = 'devkey',
    ADMIN_SECRET = 'admin',
    UPLOAD_FOLDER = UPLOAD_FOLDER,
    PRIVATECSV_FOLDER = PRIVATECSV_FOLDER
))

app.config.from_envvar('FLASKR_SETTINGS', silent=True)

import dscomp.utilities.database
import dscomp.views

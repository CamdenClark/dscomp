from dscomp import app
import os
import mysql.connector
from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash, redirect, send_from_directory

def connect_db():
    return mysql.connector.connect(
        user=app.config['USERNAME'],
        password=app.config['PASSWORD'],
        host=app.config['DATABASE_HOST'],
        database=app.config['DATABASE']
    )

def get_db():
    """Opens a new database connection if one does not already exist."""
    if not hasattr(g, 'db_connection'):
        g.db_connection = connect_db()
    return g.db_connection

@app.teardown_appcontext
def close_db(error):
    if hasattr(g, 'db_connection'):
        g.db_connection.close()

def init_db():
    db = get_db()
    with app.open_resource('schema.sql', mode = 'r') as f:
        # It seems that we need to actually iterate over the results
        # for the multi query to fully execute.
        for result in db.cursor().execute(f.read(), multi=True):
            print(result.statement)
    db.commit()

@app.cli.command('initdb')
def initdb_command():
    """Initializes the database."""
    init_db()
    print('Initialized the database')

def query_db(query, args=(), one=False):
    """Queries the database and returns a list of dictionaries."""
    cur = get_db().cursor(dictionary=True)
    cur.execute(query, args)
    rv = cur.fetchall()
    return (rv[0] if rv else None) if one else rv

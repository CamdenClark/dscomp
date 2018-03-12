from passlib.hash import pbkdf2_sha256 as sha256
import smtplib
import random
from dscomp.utilities.database import *


ALLOWED_EXTENSIONS = set(['csv', 'ipynb', 'pdf', 'png', 'jpg'])

def send_code(email, code, activation=True):
    TO = email
    if activation:
        SUBJECT = 'UIDataScience Competition: Activation Code'
        TEXT = '''Your activation code is: {}
        
        Confirm your email at http://dscomp.ibest.uidaho.edu/register/confirm'''.format(code)
    else:
        SUBJECT = 'UIDataScience Competition: Reset your password'
        TEXT = '''Your reset code is: {}
        
        Reset your password at http://dscomp.ibest.uidaho.edu/reset/password'''.format(code)
    gmail_sender = app.config['EMAIL_ADDRESS']
    gmail_passwd = app.config['EMAIL_PASSWORD']

    server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
    server.login(gmail_sender, gmail_passwd)
    
    BODY = '\r\n'.join(['To: %s' % TO,
        'From: %s' % gmail_sender,
        'Subject: %s' % SUBJECT,
        '', TEXT])

    try:
        server.sendmail(gmail_sender, [TO], BODY)
        print ('email sent')
    except:
        print ('error sending mail')
    
    server.quit()


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def check_password_hash(plaintext, pwhash):
    return sha256.verify(plaintext, pwhash)

def generate_password_hash(plaintext):
    return sha256.encrypt(plaintext, rounds=200000, salt_size=16)

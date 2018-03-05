from passlib.hash import pbkdf2_sha256 as sha256
import smtplib
import random
from dscomp.utilities.database import *


ALLOWED_EXTENSIONS = set(['csv', 'ipynb'])

def send_code(email, code):
    TO = email
    SUBJECT = 'UIDataScience Competition: Activation Code'
    TEXT = 'Your activation code is: {}'.format(code)

    gmail_sender = 'uidatascience@gmail.com'
    gmail_passwd = 'machinelearning'

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

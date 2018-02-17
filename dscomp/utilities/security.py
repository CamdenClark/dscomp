from passlib.hash import pbkdf2_sha256 as sha256
from dscomp.utilities.database import *

ALLOWED_EXTENSIONS = set(['csv'])

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def check_password_hash(plaintext, pwhash):
    return sha256.verify(plaintext, pwhash)

def generate_password_hash(plaintext):
    return sha256.encrypt(plaintext, rounds=200000, salt_size=16)

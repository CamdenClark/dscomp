from passlib.hash import pbkdf2_sha256 as sha256

def generate_password_hash(plaintext):
    return sha256.encrypt(plaintext, rounds=200000, salt_size=16)

def check_password_hash(plaintext, pwhash):
    return sha256.verify(plaintext, pwhash)

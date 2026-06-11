import pyotp

def verify_mfa(secret, code):
    totp = pyotp.TOTP(secret)
    return totp.verify(code)
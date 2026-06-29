import base64
import io

import pyotp
import qrcode


def generate_qr_secret(user_id):
    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret)
    provisioning_uri = totp.provisioning_uri(name=user_id, issuer_name="CTU Portal")

    qr_image = qrcode.make(provisioning_uri)
    buffer = io.BytesIO()
    qr_image.save(buffer, format="PNG")
    qr_code_base64 = base64.b64encode(buffer.getvalue()).decode("ascii")

    return secret, qr_code_base64

def generate_qr_image(username, secret):
    totp = pyotp.TOTP(secret)

    provisioning_uri = totp.provisioning_uri(name=username, issuer_name='CTU Portal')

    qr_image = qrcode.make(provisioning_uri)
    buffer = io.BytesIO()
    qr_image.save(buffer, format="PNG")
    qr_code_base64 = base64.b64encode(buffer.getvalue()).decode("ascii")

    return qr_code_base64


def verify_totp(secret, code):
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=1)
import os

print("Current folder:", os.getcwd())

import pyotp
import qrcode

#  Generate a secret key
secret = pyotp.random_base32()
print("Secret key:", secret)

# Create TOTP object

totp = pyotp.TOTP(secret)

# Generate QR code link
uri = totp.provisioning_uri(
    name="student@example.com",
    issuer_name="CTU Portal"
)

# 4. Create QR code image
img = qrcode.make(uri)
img.save("mfa_qr.png")

print("QR code created! Scan mfa_qr.png with Google Authenticator")
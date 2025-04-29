from cryptography.fernet import Fernet
import base64
import hashlib

def get_encryption_key():
    base_key = b"culinary-chaos-secret-98765"
    salted_key = base_key + b"-secure-salt"
    return base64.urlsafe_b64encode(hashlib.sha256(salted_key).digest())

key = get_encryption_key()
fernet = Fernet(key)

# Replace with your actual values
bot_token = b"7685546024:AAHNlmkypvEqE7xgmNsFQ1SuqjwkvW8dkZk"
chat_id = b"6214817938"

encrypted_bot_token = fernet.encrypt(bot_token)
encrypted_chat_id = fernet.encrypt(chat_id)

print(f"Encrypted BOT_TOKEN: {encrypted_bot_token}")
print(f"Encrypted CHAT_ID: {encrypted_chat_id}")
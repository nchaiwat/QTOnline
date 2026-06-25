from cryptography.fernet import Fernet
import os

# Read key from file to be sure
with open('instance/sig.key', 'rb') as f:
    key = f.read()

print(f"Key: {key}")
cipher = Fernet(key)

# Find the latest user_sig file
upload_dir = 'instance/uploads'
files = [f for f in os.listdir(upload_dir) if f.startswith('user_sig_') and f.endswith('.enc')]
if not files:
    print("No signature files found.")
    exit()

latest_file = sorted(files)[-1]
file_path = os.path.join(upload_dir, latest_file)
print(f"Testing file: {file_path}")

try:
    with open(file_path, 'rb') as f:
        encrypted_data = f.read()
    
    decrypted_data = cipher.decrypt(encrypted_data)
    print("Decryption successful!")
    print(f"Decrypted size: {len(decrypted_data)}")
except Exception as e:
    print(f"Decryption failed: {e}")

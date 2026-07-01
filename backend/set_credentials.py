import os
import sys
import secrets
from dotenv import set_key, get_key

def update_env(username, password):
    env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env'))
    if not os.path.exists(env_path):
        with open(env_path, 'w') as f:
            f.write("")
            
    set_key(env_path, "AUTH_USERNAME", username)
    set_key(env_path, "AUTH_PASSWORD", password)
    
    token = get_key(env_path, "API_TOKEN")
    if not token:
        set_key(env_path, "API_TOKEN", secrets.token_hex(16))
        
if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python set_credentials.py <username> <password>")
        sys.exit(1)
    update_env(sys.argv[1], sys.argv[2])

import os
import uuid
import re

def main():
    print("==========================================")
    print("     AutoSubs AI - User Configuration     ")
    print("==========================================")
    print()
    
    username = input("Enter new username: ").strip()
    if not username:
        print("Username cannot be empty. Aborting.")
        return
        
    password = input("Enter new password: ").strip()
    if not password:
        print("Password cannot be empty. Aborting.")
        return
        
    api_token = uuid.uuid4().hex
    
    env_file = ".env"
    env_lines = []
    
    if os.path.exists(env_file):
        with open(env_file, "r", encoding="utf-8") as f:
            env_lines = f.readlines()
            
    # Remove existing auth keys
    new_env_lines = []
    for line in env_lines:
        if line.startswith("AUTH_USERNAME=") or line.startswith("AUTH_PASSWORD=") or line.startswith("API_TOKEN="):
            continue
        new_env_lines.append(line)
        
    # Add new auth keys
    # Note: we use single quotes for the values as in the original .env
    new_env_lines.append(f"AUTH_USERNAME='{username}'\n")
    new_env_lines.append(f"AUTH_PASSWORD='{password}'\n")
    new_env_lines.append(f"API_TOKEN='{api_token}'\n")
    
    with open(env_file, "w", encoding="utf-8") as f:
        f.writelines(new_env_lines)
        
    print()
    print("[SUCCESS] Credentials updated successfully!")
    print(f"Username: {username}")
    print(f"Password: {password}")
    print(f"New API Token generated: {api_token}")
    print("\nPlease restart AutoSubs AI for the changes to take effect.")

if __name__ == "__main__":
    main()

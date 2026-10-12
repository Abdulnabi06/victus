#!/usr/bin/env python3

file_path = r"C:\Users\SHAIK ABDUL NABI\OneDrive\Desktop\VICTUS\backend\services\nemotron_service.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Replace the broken Authorization header
old_auth = '            "Authorization": f"******",'
new_auth = '            "Authorization": f"Bearer {self.api_key}",'

if old_auth in content:
    content = content.replace(old_auth, new_auth)
    print("Fixed authorization header in nemotron_service.py")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("File updated successfully")
else:
    print("Authorization header already fixed or pattern not found")

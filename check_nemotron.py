#!/usr/bin/env python3
import sys

file_path = r"C:\Users\SHAIK ABDUL NABI\OneDrive\Desktop\VICTUS\backend\services\nemotron_service.py"

with open(file_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

print("Current state of nemotron_service.py:\n")
print("Line 16-18 (NemotronChatRequest model):")
for i in range(15, 18):
    print(f"{i+1}: {lines[i]}", end="")

print("\nLine 27 (NemotronService model initialization):")
print(f"27: {lines[26]}", end="")

print("\nLine 43 (Authorization header):")
print(f"43: {lines[42]}", end="")

print("\n")
print("Checking for issues:")
if "meta/llama" in lines[26]:
    print("❌ Line 27: Still has hardcoded llama model")
else:
    print("✅ Line 27: Model correctly uses settings")

if "Bearer" in lines[42]:
    print("✅ Line 43: Authorization header uses Bearer token")
elif "***" in lines[42]:
    print("❌ Line 43: Authorization header still has placeholder")

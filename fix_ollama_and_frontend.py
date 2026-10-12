#!/usr/bin/env python3
import os

# 1. Fix settings.py - remove Ollama configuration
settings_file = r"C:\Users\SHAIK ABDUL NABI\OneDrive\Desktop\VICTUS\backend\config\settings.py"

with open(settings_file, "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
skip_mode = False
for i, line in enumerate(lines):
    # Skip Ollama configuration section (lines 9-14 approximately)
    if "# Ollama Local Configuration" in line:
        skip_mode = True
        new_lines.append("    # Ollama removed - use NVIDIA Nemotron instead\n")
        continue
    
    if skip_mode and ("OLLAMA_" in line or line.strip().startswith("OLLAMA_")):
        continue  # Skip ollama lines
    
    if skip_mode and line.startswith("    # Gemini"):
        skip_mode = False
    
    new_lines.append(line)

with open(settings_file, "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print("Ollama configuration removed from settings.py")

# 2. Fix main.py - remove ollama router comment
main_file = r"C:\Users\SHAIK ABDUL NABI\OneDrive\Desktop\VICTUS\backend\main.py"

with open(main_file, "r", encoding="utf-8") as f:
    content = f.read()

# Remove the ollama router comment
content = content.replace("# Register Routers\n# app.include_router(ollama_router)\n", "# Routers automatically registered from blueprints\n")

with open(main_file, "w", encoding="utf-8") as f:
    f.write(content)

print("Ollama router removed from main.py")

# 3. Fix frontend model sending
frontend_file = r"C:\Users\SHAIK ABDUL NABI\OneDrive\Desktop\VICTUS\frontend\app.js"

with open(frontend_file, "r", encoding="utf-8") as f:
    content = f.read()

# Replace model: "Zyricon" with actual model
content = content.replace('model: "Zyricon"', 'model: "nvidia/nemotron-voicechat"')

with open(frontend_file, "w", encoding="utf-8") as f:
    f.write(content)

print("Frontend model updated to nvidia/nemotron-voicechat")

print("\nCleanup complete!")

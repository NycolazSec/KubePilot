import os
import importlib
import requests
from config import APP_ID, BOT_TOKEN

def load_commands():
    registry = {}
    definitions = []
    commands_path = os.path.join(os.path.dirname(__file__), "commands")

    for filename in os.listdir(commands_path):
        if filename.endswith(".py") and not filename.startswith("__"):
            module_name = filename[:-3]
            module = importlib.import_module(f"bot.commands.{module_name}")
            
            if hasattr(module, "definition") and hasattr(module, "execute"):
                registry[module.definition["name"]] = module
                definitions.append(module.definition)
    return registry, definitions

def declare_slash_commands(command_definitions):
    url = f"https://discord.com/api/v10/applications/{APP_ID}/commands"
    headers = {"Authorization": f"Bot {BOT_TOKEN}", "Content-Type": "application/json"}
    rep = requests.put(url, headers=headers, json=command_definitions)
    if rep.status_code == 200:
        print(f"✅ {len(command_definitions)} '/' commands synchronized successfully.")
    else:
        print(f"❌ HTTP synchronization error: {rep.text}")
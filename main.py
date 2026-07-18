import asyncio
from bot.command_loader import load_commands, declare_slash_commands
from bot.core import listen_to_discord

if __name__ == "__main__":
    print("=== STARTING KUBERNETES BOT ===\n")
    
    command_registry, command_definitions = load_commands()
    
    declare_slash_commands(command_definitions)
    
    try:
        asyncio.run(listen_to_discord(command_registry))
    except KeyboardInterrupt:
        print("\n[✓] System shutdown successful.")
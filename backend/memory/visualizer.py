from tabulate import tabulate
from pathlib import Path
import json

class MemoryVisualizer:
    def __init__(self, memory_dir="data/memory"):
        self.memory_dir = Path(memory_dir)
    
    def show_conversations(self, limit=5):
        conv_file = self.memory_dir / "conversations.json"
        if not conv_file.exists():
            print("Aucune conversation enregistrée")
            return
        
        with open(conv_file, "r") as f:
            lines = f.readlines()[-limit:]
            conversations = [json.loads(line) for line in lines]
            
            table = []
            for i, conv in enumerate(reversed(conversations), 1):
                table.append([
                    i,
                    conv["timestamp"],
                    conv["user"][:30] + "...",
                    conv["bot"][:30] + "..."
                ])
            
            print(tabulate(
                table,
                headers=["#", "Timestamp", "User", "Bot"],
                tablefmt="pretty"
            ))
import json
from datetime import datetime
from pathlib import Path
import os

class MemoryManager:
    def __init__(self, storage_path="data/memory"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(exist_ok=True)
        
        # Check if directory is writable
        if not os.access(self.storage_path, os.W_OK):
            raise PermissionError(f"Cannot write to directory: {self.storage_path}")
        
        self.conversations_file = self.storage_path / "conversations.json"
        self.facts_file = self.storage_path / "facts.json"

    def add_conversation(self, user_message: str, bot_response: str, metadata: dict = None):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "user": user_message,
            "bot": bot_response,
            "metadata": metadata or {}
        }
        
        with open(self.conversations_file, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def generate_context(self, current_message: str, limit: int = 3) -> str:
        try:
            with open(self.conversations_file, "r") as f:
                lines = f.readlines()[-limit:]
                conversations = [json.loads(line) for line in lines]
                
                context = "Historique récent:\n"
                for conv in conversations:
                    context += f"User: {conv['user']}\nBot: {conv['bot']}\n---\n"
                
                return context
        except FileNotFoundError:
            return "Aucun historique disponible"
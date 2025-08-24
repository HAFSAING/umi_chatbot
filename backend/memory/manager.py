import json
import sqlite3
from datetime import datetime
from pathlib import Path
import os
import threading
from typing import List, Dict, Optional, Any
import hashlib

class MemoryManager:
    """Gestionnaire de mémoire persistante pour chatbot avec base de données SQLite"""
    
    def __init__(self, storage_path="data/memory"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Vérifier les permissions d'écriture
        if not os.access(self.storage_path, os.W_OK):
            raise PermissionError(f"Impossible d'écrire dans le répertoire: {self.storage_path}")
        
        self.db_path = self.storage_path / "chatbot_memory.db"
        self.lock = threading.Lock()
        
        # Initialiser la base de données
        self._init_database()
        
        print(f"✅ MemoryManager initialisé: {self.db_path}")

    def _init_database(self):
        """Initialise la base de données SQLite avec les tables nécessaires"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Table des conversations
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    user_message TEXT NOT NULL,
                    bot_response TEXT NOT NULL,
                    session_id TEXT,
                    message_hash TEXT UNIQUE,
                    metadata TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Table des faits/connaissances persistantes
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS facts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT UNIQUE NOT NULL,
                    value TEXT NOT NULL,
                    category TEXT DEFAULT 'general',
                    confidence REAL DEFAULT 1.0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Table des préférences utilisateur
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_preferences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT DEFAULT 'default',
                    preference_key TEXT NOT NULL,
                    preference_value TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, preference_key)
                )
            ''')
            
            # Index pour améliorer les performances
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_conversations_timestamp ON conversations(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_conversations_session ON conversations(session_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_facts_category ON facts(category)')
            
            conn.commit()

    def _generate_message_hash(self, user_message: str, bot_response: str) -> str:
        """Génère un hash unique pour éviter les doublons"""
        content = f"{user_message}|{bot_response}"
        return hashlib.md5(content.encode()).hexdigest()

    def add_conversation(self, user_message: str, bot_response: str, 
                        session_id: str = None, metadata: Dict[str, Any] = None):
        """Ajoute une conversation à la mémoire"""
        with self.lock:
            try:
                timestamp = datetime.now().isoformat()
                message_hash = self._generate_message_hash(user_message, bot_response)
                metadata_json = json.dumps(metadata or {})
                
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT OR IGNORE INTO conversations 
                        (timestamp, user_message, bot_response, session_id, message_hash, metadata)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (timestamp, user_message, bot_response, session_id, message_hash, metadata_json))
                    
                    if cursor.rowcount > 0:
                        print(f"💾 Conversation sauvegardée (ID: {cursor.lastrowid})")
                    else:
                        print("⚠️ Conversation déjà existante (doublons évités)")
                        
            except Exception as e:
                print(f"❌ Erreur sauvegarde conversation: {e}")

    def get_recent_conversations(self, limit: int = 5, session_id: str = None) -> List[Dict]:
        """Récupère les conversations récentes"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if session_id:
                    cursor.execute('''
                        SELECT timestamp, user_message, bot_response, metadata
                        FROM conversations 
                        WHERE session_id = ?
                        ORDER BY created_at DESC 
                        LIMIT ?
                    ''', (session_id, limit))
                else:
                    cursor.execute('''
                        SELECT timestamp, user_message, bot_response, metadata
                        FROM conversations 
                        ORDER BY created_at DESC 
                        LIMIT ?
                    ''', (limit,))
                
                conversations = []
                for row in cursor.fetchall():
                    conversations.append({
                        'timestamp': row[0],
                        'user_message': row[1],
                        'bot_response': row[2],
                        'metadata': json.loads(row[3]) if row[3] else {}
                    })
                
                return list(reversed(conversations))  # Plus ancien en premier
                
        except Exception as e:
            print(f"❌ Erreur récupération conversations: {e}")
            return []

    def generate_context(self, current_message: str, limit: int = 3, 
                        session_id: str = None) -> str:
        """Génère un contexte basé sur l'historique récent"""
        try:
            conversations = self.get_recent_conversations(limit, session_id)
            
            if not conversations:
                return "Aucun historique disponible."
            
            context_parts = ["=== Historique récent ==="]
            
            for i, conv in enumerate(conversations, 1):
                context_parts.append(f"\n[{i}] Utilisateur: {conv['user_message']}")
                context_parts.append(f"    Assistant: {conv['bot_response'][:100]}{'...' if len(conv['bot_response']) > 100 else ''}")
                
                # Ajouter métadonnées importantes
                metadata = conv.get('metadata', {})
                if metadata.get('rag_used'):
                    context_parts.append("    [Utilisé: Documents RAG]")
                if metadata.get('has_image'):
                    context_parts.append("    [Contenait: Image]")
            
            context_parts.append(f"\n=== Message actuel ===")
            context_parts.append(f"Utilisateur: {current_message}")
            
            return "\n".join(context_parts)
            
        except Exception as e:
            print(f"❌ Erreur génération contexte: {e}")
            return f"Erreur contexte: {str(e)}"

    def add_fact(self, key: str, value: str, category: str = "general", confidence: float = 1.0):
        """Ajoute ou met à jour un fait dans la base de connaissances"""
        with self.lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT OR REPLACE INTO facts 
                        (key, value, category, confidence, updated_at)
                        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ''', (key, value, category, confidence))
                    
                    print(f"📚 Fait ajouté: {key} = {value} (catégorie: {category})")
                    
            except Exception as e:
                print(f"❌ Erreur ajout fait: {e}")

    def get_facts(self, category: str = None, limit: int = 10) -> List[Dict]:
        """Récupère les faits de la base de connaissances"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if category:
                    cursor.execute('''
                        SELECT key, value, category, confidence, updated_at
                        FROM facts 
                        WHERE category = ?
                        ORDER BY confidence DESC, updated_at DESC
                        LIMIT ?
                    ''', (category, limit))
                else:
                    cursor.execute('''
                        SELECT key, value, category, confidence, updated_at
                        FROM facts 
                        ORDER BY confidence DESC, updated_at DESC
                        LIMIT ?
                    ''', (limit,))
                
                facts = []
                for row in cursor.fetchall():
                    facts.append({
                        'key': row[0],
                        'value': row[1],
                        'category': row[2],
                        'confidence': row[3],
                        'updated_at': row[4]
                    })
                
                return facts
                
        except Exception as e:
            print(f"❌ Erreur récupération faits: {e}")
            return []

    def set_user_preference(self, preference_key: str, preference_value: str, user_id: str = "default"):
        """Définit une préférence utilisateur"""
        with self.lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT OR REPLACE INTO user_preferences 
                        (user_id, preference_key, preference_value)
                        VALUES (?, ?, ?)
                    ''', (user_id, preference_key, preference_value))
                    
                    print(f"⚙️ Préférence définie: {preference_key} = {preference_value}")
                    
            except Exception as e:
                print(f"❌ Erreur définition préférence: {e}")

    def get_user_preference(self, preference_key: str, user_id: str = "default", default_value: str = None) -> Optional[str]:
        """Récupère une préférence utilisateur"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT preference_value FROM user_preferences 
                    WHERE user_id = ? AND preference_key = ?
                ''', (user_id, preference_key))
                
                result = cursor.fetchone()
                return result[0] if result else default_value
                
        except Exception as e:
            print(f"❌ Erreur récupération préférence: {e}")
            return default_value

    def get_memory_stats(self) -> Dict[str, Any]:
        """Retourne des statistiques sur la mémoire"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Compter les conversations
                cursor.execute('SELECT COUNT(*) FROM conversations')
                total_conversations = cursor.fetchone()[0]
                
                # Compter les faits
                cursor.execute('SELECT COUNT(*) FROM facts')
                total_facts = cursor.fetchone()[0]
                
                # Compter les préférences
                cursor.execute('SELECT COUNT(*) FROM user_preferences')
                total_preferences = cursor.fetchone()[0]
                
                # Conversation la plus récente
                cursor.execute('SELECT MAX(created_at) FROM conversations')
                last_conversation = cursor.fetchone()[0]
                
                # Taille du fichier de base de données
                db_size = self.db_path.stat().st_size if self.db_path.exists() else 0
                
                return {
                    'total_conversations': total_conversations,
                    'total_facts': total_facts,
                    'total_preferences': total_preferences,
                    'last_conversation': last_conversation,
                    'database_size_bytes': db_size,
                    'database_size_mb': round(db_size / (1024 * 1024), 2),
                    'database_path': str(self.db_path)
                }
                
        except Exception as e:
            print(f"❌ Erreur statistiques mémoire: {e}")
            return {'error': str(e)}

    def clear_old_conversations(self, days_to_keep: int = 30):
        """Supprime les conversations anciennes pour éviter l'accumulation"""
        with self.lock:
            try:
                cutoff_date = datetime.now().replace(day=datetime.now().day - days_to_keep)
                
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        DELETE FROM conversations 
                        WHERE created_at < ?
                    ''', (cutoff_date.isoformat(),))
                    
                    deleted_count = cursor.rowcount
                    print(f"🧹 {deleted_count} conversations anciennes supprimées")
                    
            except Exception as e:
                print(f"❌ Erreur nettoyage conversations: {e}")

    def export_memory(self, export_path: str = None) -> str:
        """Exporte la mémoire vers un fichier JSON"""
        try:
            if not export_path:
                export_path = self.storage_path / f"memory_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            export_data = {
                'export_timestamp': datetime.now().isoformat(),
                'conversations': self.get_recent_conversations(limit=1000),
                'facts': self.get_facts(limit=1000),
                'stats': self.get_memory_stats()
            }
            
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            print(f"📤 Mémoire exportée vers: {export_path}")
            return str(export_path)
            
        except Exception as e:
            print(f"❌ Erreur export mémoire: {e}")
            return None

    def __del__(self):
        """Nettoyage lors de la destruction de l'objet"""
        try:
            # Fermer proprement les connexions si nécessaire
            pass
        except:
            pass
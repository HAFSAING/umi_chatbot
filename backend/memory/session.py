import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import json
import re

class SessionManager:
    """Gestionnaire de sessions pour le chatbot avec mémoire contextuelle"""
    
    def __init__(self, memory_manager):
        self.memory_manager = memory_manager
        self.active_sessions = {}  # session_id -> session_info
        self.session_timeout = timedelta(hours=2)  # Timeout par défaut
        
    def create_session(self, user_id: str = "default", metadata: Dict[str, Any] = None) -> str:
        """Crée une nouvelle session"""
        session_id = str(uuid.uuid4())
        
        session_info = {
            'session_id': session_id,
            'user_id': user_id,
            'created_at': datetime.now(),
            'last_activity': datetime.now(),
            'message_count': 0,
            'user_name': None,  # Nom de l'utilisateur
            'metadata': metadata or {}
        }
        
        self.active_sessions[session_id] = session_info
        
        # Sauvegarder la session comme fait
        try:
            self.memory_manager.add_fact(
                key=f"session_{session_id}",
                value=json.dumps(session_info, default=str),
                category="sessions"
            )
        except Exception as e:
            print(f"⚠️ Erreur sauvegarde session: {e}")
        
        print(f"🆔 Nouvelle session créée: {session_id}")
        return session_id
    
    def extract_user_name(self, message: str) -> Optional[str]:
        """Extrait le nom de l'utilisateur depuis un message"""
        if not message:
            return None
            
        # Patterns pour détecter quand quelqu'un donne son nom
        patterns = [
            r"je m'appelle\s+([a-zA-ZÀ-ÿ\s\-]+)",
            r"mon nom est\s+([a-zA-ZÀ-ÿ\s\-]+)",
            r"je suis\s+([a-zA-ZÀ-ÿ\s\-]+)",
            r"c'est\s+([a-zA-ZÀ-ÿ\s\-]+)",
            r"moi c'est\s+([a-zA-ZÀ-ÿ\s\-]+)",
            r"appelle[z]?[-\s]moi\s+([a-zA-ZÀ-ÿ\s\-]+)",
            r"my name is\s+([a-zA-Z\s\-]+)",
            r"i am\s+([a-zA-Z\s\-]+)",
            r"call me\s+([a-zA-Z\s\-]+)",
            r"i'm\s+([a-zA-Z\s\-]+)"
        ]
        
        message_lower = message.lower().strip()
        
        for pattern in patterns:
            match = re.search(pattern, message_lower, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                
                # Nettoyer le nom (enlever les mots parasites)
                stop_words = r'\b(un|une|le|la|les|de|du|des|et|ou|mais|donc|car|ni|or|aussi|très|bien|content|heureux)\b'
                name = re.sub(stop_words, '', name, flags=re.IGNORECASE)
                name = ' '.join(name.split())  # Nettoyer les espaces multiples
                
                # Validation du nom
                if (len(name) >= 2 and len(name) <= 50 and 
                    not any(char.isdigit() for char in name) and
                    not any(char in '@#$%^&*()+=[]{}|;:,.<>?/~`' for char in name)):
                    return name.title()  # Première lettre en majuscule
        
        return None
    
    def update_user_name(self, session_id: str, user_name: str):
        """Met à jour le nom de l'utilisateur pour une session"""
        if session_id in self.active_sessions:
            self.active_sessions[session_id]['user_name'] = user_name
            
            try:
                # Sauvegarder comme préférence utilisateur
                self.memory_manager.set_user_preference(
                    preference_key="user_name",
                    preference_value=user_name,
                    user_id=session_id
                )
                
                # Sauvegarder comme fait
                self.memory_manager.add_fact(
                    key=f"user_name_{session_id}",
                    value=user_name,
                    category="user_info",
                    confidence=0.9
                )
                
                print(f"👤 Nom utilisateur mis à jour: {user_name} (session: {session_id[:8]}...)")
            except Exception as e:
                print(f"⚠️ Erreur sauvegarde nom: {e}")
    
    def get_user_name(self, session_id: str) -> Optional[str]:
        """Récupère le nom de l'utilisateur pour une session"""
        if session_id in self.active_sessions:
            user_name = self.active_sessions[session_id].get('user_name')
            if user_name:
                return user_name
        
        # Essayer de récupérer depuis les préférences
        try:
            return self.memory_manager.get_user_preference("user_name", session_id)
        except Exception as e:
            print(f"⚠️ Erreur récupération nom: {e}")
            return None
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Récupère les informations d'une session"""
        if not session_id:
            return None
            
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            
            # Vérifier si la session n'a pas expiré
            if datetime.now() - session['last_activity'] > self.session_timeout:
                self.close_session(session_id)
                return None
            
            return session
        
        return None
    
    def update_session_activity(self, session_id: str):
        """Met à jour l'activité d'une session"""
        if session_id in self.active_sessions:
            self.active_sessions[session_id]['last_activity'] = datetime.now()
            self.active_sessions[session_id]['message_count'] += 1
    
    def close_session(self, session_id: str):
        """Ferme une session"""
        if session_id in self.active_sessions:
            session_info = self.active_sessions[session_id]
            
            try:
                # Marquer la session comme fermée
                session_info['closed_at'] = datetime.now()
                session_info['duration'] = session_info['closed_at'] - session_info['created_at']
                
                # Sauvegarder les statistiques finales
                self.memory_manager.add_fact(
                    key=f"session_{session_id}_final",
                    value=json.dumps(session_info, default=str),
                    category="session_stats"
                )
            except Exception as e:
                print(f"⚠️ Erreur fermeture session: {e}")
            
            del self.active_sessions[session_id]
            print(f"🔒 Session fermée: {session_id[:8]}...")
    
    def cleanup_expired_sessions(self):
        """Nettoie les sessions expirées"""
        expired_sessions = []
        
        for session_id, session_info in self.active_sessions.items():
            if datetime.now() - session_info['last_activity'] > self.session_timeout:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            self.close_session(session_id)
        
        if expired_sessions:
            print(f"🧹 {len(expired_sessions)} sessions expirées nettoyées")
    
    def get_session_context(self, session_id: str, message_limit: int = 5) -> str:
        """Génère un contexte spécifique à la session avec le nom de l'utilisateur"""
        session = self.get_session(session_id)
        if not session:
            return "Session non trouvée ou expirée."
        
        # Récupérer le nom de l'utilisateur
        user_name = self.get_user_name(session_id)
        
        # Récupérer l'historique de la session
        try:
            context = self.memory_manager.generate_context(
                current_message="",
                limit=message_limit,
                session_id=session_id
            )
        except Exception as e:
            print(f"⚠️ Erreur génération contexte: {e}")
            context = "Pas d'historique disponible"
        
        # Ajouter les informations de session avec le nom
        session_context = f"""=== Informations de session ===
Session ID: {session_id}
Utilisateur: {session['user_id']}
Nom de l'utilisateur: {user_name if user_name else 'Non défini'}
Créée le: {session['created_at'].strftime('%Y-%m-%d %H:%M:%S')}
Messages échangés: {session['message_count']}
Dernière activité: {session['last_activity'].strftime('%Y-%m-%d %H:%M:%S')}

{context}
"""
        
        return session_context
    
    def get_personalized_greeting(self, session_id: str) -> str:
        """Génère un message de salutation personnalisé"""
        user_name = self.get_user_name(session_id)
        
        if user_name:
            greetings = [
                f"Bonjour {user_name} ! Comment puis-je vous aider aujourd'hui ?",
                f"Salut {user_name} ! Que puis-je faire pour vous ?",
                f"Hello {user_name} ! En quoi puis-je vous être utile ?",
                f"Ravi de vous revoir {user_name} ! Comment allez-vous ?",
                f"Bonjour {user_name} ! J'espère que vous allez bien !"
            ]
            import random
            return random.choice(greetings)
        else:
            return "Bonjour ! Comment puis-je vous aider ? N'hésitez pas à me dire votre nom si vous le souhaitez."
    
    def get_active_sessions_count(self) -> int:
        """Retourne le nombre de sessions actives"""
        self.cleanup_expired_sessions()
        return len(self.active_sessions)
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Retourne des statistiques sur les sessions"""
        self.cleanup_expired_sessions()
        
        total_messages = sum(session['message_count'] for session in self.active_sessions.values())
        users_with_names = sum(1 for session in self.active_sessions.values() if session.get('user_name'))
        
        return {
            'active_sessions': len(self.active_sessions),
            'users_with_names': users_with_names,
            'total_messages_in_active_sessions': total_messages,
            'session_timeout_hours': self.session_timeout.total_seconds() / 3600,
            'sessions_info': [
                {
                    'session_id': session_id[:8] + "...",  # Tronquer pour la sécurité
                    'user_id': info['user_id'],
                    'user_name': info.get('user_name'),
                    'message_count': info['message_count'],
                    'duration_minutes': (datetime.now() - info['created_at']).total_seconds() / 60
                }
                for session_id, info in self.active_sessions.items()
            ]
        }
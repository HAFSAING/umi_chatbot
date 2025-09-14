from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import ollama
import sys
import json
import os
from pathlib import Path
import time
import requests
from quick_responses import QuickResponseSystem
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    from rag.retriever import RagRetriever
    from rag.vector_db import VectorDB
    from rag.loader import DocumentLoader
    from memory.manager import MemoryManager
    from memory.session import SessionManager
    RAG_AVAILABLE = True
    logger.info("✅ Modules RAG et Mémoire importés avec succès")
except ImportError as e:
    logger.warning(f"⚠️ Modules RAG non disponibles: {e}")
    logger.info("💡 Le chatbot fonctionnera sans RAG")
    RAG_AVAILABLE = False

app = Flask(__name__) 
CORS(app)

logger.info("🚀 Démarrage du serveur Flask...")

# Messages d'erreur simples pour les utilisateurs
USER_ERROR_MESSAGES = {
    'server_unavailable': "Service temporairement indisponible. Réessayez dans quelques instants.",
    'model_error': "Je rencontre des difficultés techniques. Réessayez plus tard.",
    'timeout_error': "⏱️ La réponse prend trop de temps. Essayez avec un message plus court.",
    'connection_error': "🔌 Problème de connexion temporaire. Veuillez patienter.",
    'file_error': "📎 Problème avec le fichier envoyé. Essayez un autre format.",
    'general_error': "😅 Une erreur inattendue s'est produite. Réessayez dans un moment."
}

# Initialisation des composants RAG
rag_retriever = None
memory_manager = None
session_manager = None
document_loader = None
rag_initialized = False

def log_error_safely(error, context=""):
    """Log les erreurs dans le terminal sans les exposer à l'utilisateur"""
    logger.error(f"🔥 ERREUR {context}: {str(error)}")
    if hasattr(error, '__traceback__'):
        import traceback
        logger.error(f"📍 Traceback: {traceback.format_exc()}")

def test_ollama_connection():
    """Test de connexion Ollama amélioré avec retry et API REST"""
    max_retries = 3
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            # Log détaillé uniquement dans le terminal
            logger.info(f"🔍 Test de connexion à Ollama (tentative {attempt + 1}/{max_retries})...")
            
            response = requests.get("http://localhost:11434/api/tags", timeout=10)
            
            if response.status_code != 200:
                logger.error(f"Ollama API HTTP {response.status_code}")  # Terminal seulement
                raise Exception("Service indisponible")  # Message simple
            
            data = response.json()
            models = data.get('models', [])
            model_names = [model.get('name', '') for model in models]
            
            logger.info(f"✅ Modèles disponibles: {model_names}")
            
            llava_models = [name for name in model_names if 'llava' in name.lower()]
            
            if not llava_models:
                logger.warning("⚠️ Aucun modèle llava trouvé!")
                logger.info("💡 Installez-le avec: ollama pull llava:latest")
                raise Exception("Service en maintenance")  # Message simple
            
            logger.info(f"✅ Modèles llava disponibles: {llava_models}")
            return True, llava_models
            
        except requests.exceptions.ConnectionError:
            logger.error(f"❌ Tentative {attempt + 1} échouée: Ollama service non accessible")
        except requests.exceptions.Timeout:
            logger.error(f"❌ Tentative {attempt + 1} échouée: Timeout")
        except Exception as e:
            # Log détaillé dans terminal, exception simple pour l'utilisateur
            logger.error(f"❌ Tentative {attempt + 1} échouée: {e}")
        
        if attempt < max_retries - 1:
            logger.info(f"⏳ Nouvelle tentative dans {retry_delay} secondes...")
            time.sleep(retry_delay)
    
    logger.error("❌ Toutes les tentatives de connexion ont échoué")
    logger.info("💡 Vérifiez que Ollama est démarré: ollama serve")
    return False, []


def get_best_llava_model():
    """Trouve le meilleur modèle llava disponible"""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code != 200:
            return None
            
        data = response.json()
        model_names = [model.get('name', '') for model in data.get('models', [])]
        
        # Priorités des modèles llava (du meilleur au moins bon)
        preferred_models = [
            'llava:latest',
            'llava:13b',
            'llava:7b',
            'llava:34b',
            'llava'
        ]
        
        for preferred in preferred_models:
            for available in model_names:
                if preferred.lower() == available.lower():
                    return available
        
        # Fallback: n'importe quel modèle contenant "llava"
        for available in model_names:
            if 'llava' in available.lower():
                return available
                
        return None
    except Exception as e:
        log_error_safely(e, "get_best_llava_model")
        return None
    
def initialize_rag_system():
    """Initialise le système RAG ET MÉMOIRE si possible"""
    global rag_retriever, memory_manager, session_manager, document_loader, rag_initialized
    
    if not RAG_AVAILABLE:
        logger.warning("⚠️ RAG non disponible - modules non importés")
        return False
    
    try:
        logger.info("📄 Initialisation du système RAG et Mémoire...")
        
        # Créer les dossiers nécessaires
        os.makedirs("data/documents", exist_ok=True)
        os.makedirs("data/vector_db", exist_ok=True)
        os.makedirs("data/memory", exist_ok=True)
        
        # PRIORITÉ 1 : Initialiser la mémoire (fonctionne toujours)
        try:
            memory_manager = MemoryManager()
            session_manager = SessionManager(memory_manager)
            logger.info("✅ Système de mémoire initialisé!")
        except Exception as e:
            log_error_safely(e, "init memory")
            return False
        
        try:
            document_loader = DocumentLoader("data/documents")
            docs_info = document_loader.scan_documents()
            logger.info(f"📊 Documents scannés: {docs_info['total_files']} total, {docs_info['supported_files']} supportés")
            
            if docs_info['supported_files'] > 0:
                vector_db = VectorDB()
                vector_db.initialize()
                rag_retriever = RagRetriever()
                logger.info("✅ Base vectorielle initialisée avec documents")
            else:
                logger.info("⚠️ Aucun document trouvé - RAG désactivé")
                rag_retriever = None
                
        except Exception as e:
            log_error_safely(e, "init RAG")
            rag_retriever = None
            
        rag_initialized = True
        logger.info("✅ Système initialisé (mémoire + RAG optionnel)!")
        return True
            
    except Exception as e:
        log_error_safely(e, "initialize_rag_system")
        return False

def test_model_response(model_name):
    """Test si un modèle répond correctement via API REST"""
    try:
        logger.info(f"🧪 Test du modèle {model_name}...")
        
        payload = {
            "model": model_name,
            "messages": [
                {"role": "user", "content": "Hello, respond with just 'OK' to confirm you work."}
            ],
            "stream": False,
            "options": {"temperature": 0.1, "num_predict": 10}
        }
        
        response = requests.post(
            "http://localhost:11434/api/chat",
            json=payload,
            timeout=20
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result.get('message', {}).get('content', '')
            logger.info(f"✅ Modèle {model_name} fonctionne! Réponse: '{content[:30]}'")
            return True
        else:
            logger.error(f"❌ Erreur test modèle {model_name}: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        log_error_safely(e, f"test_model_response {model_name}")
        return False

def enhance_prompt_with_rag(user_message):
    """Enrichit le prompt avec le contexte RAG"""
    if not rag_initialized or not rag_retriever or not user_message.strip():
        return user_message, False
    
    try:
        context = rag_retriever.search(user_message, k=3)
        if context.strip():
            enhanced_prompt = f"""Contexte basé sur les documents disponibles:
{context}

Question de l'utilisateur: {user_message}

Réponds en utilisant prioritairement les informations du contexte fourni."""
            return enhanced_prompt, True
        else:
            return user_message, False
    except Exception as e:
        log_error_safely(e, "enhance_prompt_with_rag")
        return user_message, False

def get_or_create_session(request_data):
    """Récupère ou crée une session utilisateur"""
    session_id = request_data.get('session_id')
    
    if not session_id or not session_manager:
        # Créer une nouvelle session
        if session_manager:
            session_id = session_manager.create_session()
            logger.info(f"🆔 Nouvelle session créée: {session_id[:8]}...")
        else:
            session_id = "default"
            logger.info("⚠️ Session par défaut (pas de gestionnaire)")
    else:
        # Vérifier que la session existe toujours
        if session_manager and not session_manager.get_session(session_id):
            session_id = session_manager.create_session()
            logger.info(f"🔄 Session expirée, nouvelle créée: {session_id[:8]}...")
    
    return session_id

def process_user_message(message, session_id):
    """Traite le message utilisateur pour extraire des informations personnelles"""
    if not session_manager or not message:
        return message, False
    
    try:
        # Vérifier si l'utilisateur donne son nom
        user_name = session_manager.extract_user_name(message)
        name_detected = False
        
        if user_name:
            old_name = session_manager.get_user_name(session_id)
            if old_name != user_name:
                session_manager.update_user_name(session_id, user_name)
                name_detected = True
                logger.info(f"👤 Nom détecté et sauvegardé: {user_name} (session: {session_id[:8]}...)")
            else:
                logger.info(f"👤 Nom déjà connu: {user_name}")
        
        # Mettre à jour l'activité de la session
        session_manager.update_session_activity(session_id)
        
        return message, name_detected
    except Exception as e:
        log_error_safely(e, "process_user_message")
        return message, False

def generate_personalized_response(bot_response, session_id, name_detected=False):
    """Génère une réponse personnalisée avec le nom de l'utilisateur"""
    if not session_manager:
        return bot_response
    
    try:
        user_name = session_manager.get_user_name(session_id)
        
        
        if name_detected and user_name:
            confirmation_messages = [
                f"Enchanté de faire votre connaissance, {user_name} ! ",
                f"Ravi de vous rencontrer, {user_name} ! ",
                f"Parfait, je me souviendrai que vous êtes {user_name} ! ",
                f"Merci {user_name}, je retiendrai votre nom ! "
            ]
            import random
            confirmation = random.choice(confirmation_messages)
            bot_response = confirmation + bot_response
        
        # Pour les réponses longues, personnaliser naturellement
        elif user_name and len(bot_response) > 30:
            # Remplacer les salutations génériques par des salutations personnalisées
            salutations = {
                'Bonjour': f'Bonjour {user_name}',
                'Salut': f'Salut {user_name}', 
                'Hello': f'Hello {user_name}',
                'Bonsoir': f'Bonsoir {user_name}',
                'Bonne journée': f'Bonne journée {user_name}',
                'À bientôt': f'À bientôt {user_name}'
            }
            
            for generic, personalized in salutations.items():
                if bot_response.startswith(generic + ' ') or bot_response.startswith(generic + '!'):
                    bot_response = bot_response.replace(generic, personalized.split(' ')[0] + ' ' + user_name, 1)
                    break
        
        return bot_response
    except Exception as e:
        log_error_safely(e, "generate_personalized_response")
        return bot_response

quick_response_system = None

def initialize_quick_responses():
    """Initialise le système de réponses rapides"""
    global quick_response_system
    try:
        quick_response_system = QuickResponseSystem()
        logger.info("✅ Système de réponses rapides initialisé")
        return True
    except Exception as e:
        log_error_safely(e, "initialize_quick_responses")
        return False

@app.route('/')
def serve_html():
    """Servir le fichier HTML depuis le dossier frontend"""
    try:
        return send_from_directory('../frontend', 'chatbot.html')
    except Exception as e:
        log_error_safely(e, "serve_html")
        return "Service temporairement indisponible", 503

@app.route('/api/status', methods=['GET'])
def status():
    """Endpoint de diagnostic complet - version simplifiée pour l'utilisateur"""
    try:
        ollama_ok, llava_models = test_ollama_connection()
        
        user_status = {
            'status': 'ok' if ollama_ok else 'maintenance',
            'service_available': ollama_ok and len(llava_models) > 0,
            'message': 'Service opérationnel' if ollama_ok else 'Service en maintenance'
        }
        
        # Log détaillé pour le développeur (terminal uniquement)
        if ollama_ok:
            logger.info(f"✅ Status OK - Modèles: {llava_models}")
        else:
            logger.error("❌ Status KO - Ollama inaccessible")
        
        return jsonify(user_status)
        
    except Exception as e:
        log_error_safely(e, "status endpoint")
        return jsonify({
            'status': 'maintenance',
            'service_available': False,
            'message': 'Service temporairement indisponible'
        }), 503

@app.route('/api/test', methods=['GET'])
def test_endpoint():
    """Endpoint de test basique"""
    return jsonify({
        'message': 'Service disponible',
        'status': 'ok',
        'timestamp': time.time()
    })

@app.route('/api/initialize-rag', methods=['POST'])
def initialize_rag_endpoint():
    """Endpoint pour initialiser/réinitialiser le RAG"""
    try:
        success = initialize_rag_system()
        return jsonify({
            "success": success,
            "message": "Système initialisé" if success else "Erreur d'initialisation"
        })
    except Exception as e:
        log_error_safely(e, "initialize_rag_endpoint")
        return jsonify({
            "success": False,
            "message": "Service temporairement indisponible"
        }), 503

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        logger.info("📨 Nouvelle requête chat")

        data = request.json
        if not data:
            return jsonify({'error': 'Données manquantes'}), 400
            
        user_message = data.get('message', '').strip()
        image_b64 = data.get('image')
        files_data = data.get('files', [])

        session_id = get_or_create_session(data)

        if not user_message and not image_b64 and not files_data:
            return jsonify({'error': 'Message requis'}), 400

        logger.info(f"💬 Message: '{user_message[:50]}{'...' if len(user_message) > 50 else ''}'")
        logger.info(f"🏞️ Image: {'Oui' if image_b64 else 'Non'}")
        logger.info(f"📎 Fichiers: {len(files_data)}")
        logger.info(f"🆔 Session: {session_id[:8]}...")

        if user_message and not image_b64 and not files_data and quick_response_system:
            logger.info("🔍 Vérification réponses rapides...")
            
            try:
                quick_response = quick_response_system.get_quick_response(user_message)
                
                if quick_response and quick_response.get('confidence', 0) >= 0.7:
                    logger.info(f"⚡ Réponse rapide utilisée (confiance: {quick_response['confidence']})")
                    
                    # Traitement du nom utilisateur
                    processed_message, name_detected = process_user_message(user_message, session_id)
                    
                    # Personnaliser la réponse
                    bot_response = generate_personalized_response(
                        quick_response['response'], 
                        session_id, 
                        name_detected
                    )
                    
                    # Sauvegarder en mémoire
                    if memory_manager:
                        try:
                            memory_manager.add_conversation(
                                user_message=user_message,
                                bot_response=bot_response,
                                session_id=session_id,
                                metadata={
                                    "quick_response": True,
                                    "category": quick_response.get('category', 'contact'),
                                    "confidence": quick_response.get('confidence'),
                                    "processing_time": "< 100ms",
                                    "user_name": session_manager.get_user_name(session_id) if session_manager else None
                                }
                            )
                            logger.info("💾 Réponse rapide sauvegardée en mémoire")
                        except Exception as e:
                            log_error_safely(e, "save quick response to memory")
                    
                    return jsonify({
                        'response': bot_response,
                        'status': 'success',
                        'session_id': session_id,
                        'quick_response': True,
                        'processing_time': '< 100ms',
                        'category': quick_response.get('category', 'info'),
                        'quick_replies': quick_response.get('quick_replies', []),
                        'user_name': session_manager.get_user_name(session_id) if session_manager else None,
                        'name_detected': name_detected
                    })
                else:
                    logger.info("🤖 Réponse rapide non trouvée - utilisation d'Ollama")
            except Exception as e:
                log_error_safely(e, "quick response processing")
                # Continuer vers Ollama en cas d'erreur

        # Traitement du message utilisateur (extraction du nom, etc.)
        processed_message, name_detected = process_user_message(user_message, session_id)
        print("achraf")
        # Trouver le meilleur modèle llava disponible
        model_to_use = get_best_llava_model()
        if not model_to_use:
            logger.error("❌ Aucun modèle llava disponible")
            return jsonify({
                'error': USER_ERROR_MESSAGES['server_unavailable']
            }), 503

        logger.info(f"🎯 Utilisation du modèle: {model_to_use}")

        # Test rapide du modèle avant utilisation
        if not test_model_response(model_to_use):
            logger.error(f"❌ Modèle {model_to_use} ne répond pas")
            return jsonify({
                'error': USER_ERROR_MESSAGES['model_error']
            }), 503

        rag_used = False
        if user_message and not image_b64:
            # Ajouter le contexte de session au message
            session_context = ""
            if session_manager:
                user_name = session_manager.get_user_name(session_id)
                if user_name:
                    session_context = f"L'utilisateur s'appelle {user_name}. "
            
            enhanced_message, rag_used = enhance_prompt_with_rag(processed_message)
            if rag_used:
                logger.info("📚 Message enrichi avec RAG")
            
            # Ajouter le contexte de session
            if session_context:
                enhanced_message = session_context + enhanced_message
        else:
            enhanced_message = processed_message or "Analysez ce contenu en détail"

        payload = {
            "model": model_to_use,
            "messages": [
                {
                    "role": "user",
                    "content": enhanced_message
                }
            ],
            "stream": False,
            "options": {
                "temperature": 0.7,
                "num_predict": 512,
                "num_ctx": 2048
            }
        }
        
        if image_b64:
            payload["messages"][0]["images"] = [image_b64]

        logger.info("🤖 Appel à Ollama via API REST...")
        
        try:
            response = requests.post(
                "http://localhost:11434/api/chat",
                json=payload,
                timeout=60
            )
            
            if response.status_code != 200:
                logger.error(f"❌ Ollama API HTTP {response.status_code}: {response.text[:300]}")
                return jsonify({
                    'error': USER_ERROR_MESSAGES['server_unavailable']
                }), 503
            
            result = response.json()
            
            if 'message' not in result or 'content' not in result['message']:
                logger.error("❌ Réponse Ollama invalide - structure inattendue")
                return jsonify({
                    'error': USER_ERROR_MESSAGES['model_error']
                }), 503
            
            bot_response = result['message']['content'].strip()
            
            if not bot_response:
                bot_response = "Désolé, je n'ai pas pu générer une réponse appropriée à votre demande."

            bot_response = generate_personalized_response(bot_response, session_id, name_detected)
            
            logger.info(f"✅ Réponse générée: {len(bot_response)} caractères")
            
            # Sauvegarder dans la mémoire
            if memory_manager:
                try:
                    memory_manager.add_conversation(
                        user_message=user_message or "Contenu multimédia envoyé",
                        bot_response=bot_response,
                        session_id=session_id,
                        metadata={
                            "rag_used": rag_used,
                            "has_image": bool(image_b64),
                            "has_files": len(files_data) > 0,
                            "model": model_to_use,
                            "name_detected": name_detected,
                            "quick_response": False,
                            "user_name": session_manager.get_user_name(session_id) if session_manager else None
                        }
                    )
                    logger.info("💾 Conversation sauvegardée en mémoire")
                except Exception as e:
                    log_error_safely(e, "save conversation to memory")
            
            return jsonify({
                'response': bot_response,
                'status': 'success', 
                'session_id': session_id,
                'model_used': model_to_use,
                'rag_used': rag_used,
                'quick_response': False,
                'user_name': session_manager.get_user_name(session_id) if session_manager else None,
                'name_detected': name_detected
            })
            
        except requests.exceptions.Timeout:
            logger.error("⏱️ Timeout Ollama (>90s)")
            return jsonify({
                'error': USER_ERROR_MESSAGES['timeout_error']
            }), 503
        except requests.exceptions.ConnectionError:
            logger.error("🔌 Connexion Ollama impossible")
            return jsonify({
                'error': USER_ERROR_MESSAGES['connection_error']
            }), 503
        except Exception as e:
            log_error_safely(e, "Ollama API call")
            return jsonify({
                'error': USER_ERROR_MESSAGES['server_unavailable']
            }), 503
            
    except Exception as e:
        log_error_safely(e, "chat endpoint")
        return jsonify({
            'error': USER_ERROR_MESSAGES['general_error']
        }), 500

@app.route('/api/memory/status', methods=['GET'])
def memory_status():
    """Endpoint pour vérifier le statut de la mémoire"""
    try:
        if not memory_manager:
            return jsonify({
                'status': 'unavailable',
                'message': 'Service de mémoire non disponible'
            }), 503
        
        stats = memory_manager.get_memory_stats()
        session_stats = session_manager.get_session_stats() if session_manager else {}
        
        return jsonify({
            'status': 'ok',
            'memory_initialized': True,
            'message': 'Mémoire opérationnelle'
        })
    except Exception as e:
        log_error_safely(e, "memory_status")
        return jsonify({
            'status': 'error',
            'message': 'Erreur de service'
        }), 500

@app.route('/api/memory/clear', methods=['POST'])
def clear_memory():
    """Endpoint pour nettoyer la mémoire"""
    try:
        if not memory_manager:
            return jsonify({'error': 'Service non disponible'}), 503
        
        memory_manager.clear_old_conversations(days_to_keep=7)
        return jsonify({
            'status': 'ok', 
            'message': 'Nettoyage effectué'
        })
    except Exception as e:
        log_error_safely(e, "clear_memory")
        return jsonify({'error': 'Erreur lors du nettoyage'}), 500

@app.route('/api/session/<session_id>/info', methods=['GET'])
def get_session_info(session_id):
    """Récupère les informations d'une session"""
    try:
        if not session_manager:
            return jsonify({'error': 'Service non disponible'}), 503
        
        session = session_manager.get_session(session_id)
        if not session:
            return jsonify({'error': 'Session non trouvée'}), 404
        
        user_name = session_manager.get_user_name(session_id)
        
        return jsonify({
            'session_id': session_id,
            'user_name': user_name,
            'message_count': session['message_count'],
            'created_at': session['created_at'].isoformat(),
            'last_activity': session['last_activity'].isoformat()
        })
        
    except Exception as e:
        log_error_safely(e, "get_session_info")
        return jsonify({'error': 'Erreur de service'}), 500

@app.route('/api/session/<session_id>/greeting', methods=['GET'])
def get_personalized_greeting(session_id):
    """Récupère un message de salutation personnalisé"""
    try:
        if not session_manager:
            return jsonify({'greeting': 'Bonjour ! Comment puis-je vous aider ?'})
        
        greeting = session_manager.get_personalized_greeting(session_id)
        return jsonify({'greeting': greeting})
        
    except Exception as e:
        log_error_safely(e, "get_personalized_greeting")
        return jsonify({'greeting': 'Bonjour ! Comment puis-je vous aider ?'})

# Endpoints de debug (optionnels, pour développement uniquement)
@app.route('/api/debug/ollama', methods=['GET'])
def debug_ollama():
    """Endpoint de debug pour Ollama - DÉVELOPPEMENT UNIQUEMENT"""
    # Cet endpoint ne devrait être utilisé qu'en développement
    # En production, désactivez-le ou protégez-le
    if not app.debug:
        return jsonify({'error': 'Debug non disponible'}), 403
    
    try:
        debug_info = {}
        
        # Test connexion basique
        try:
            response = requests.get("http://localhost:11434/api/version", timeout=5)
            if response.status_code == 200:
                debug_info['ollama_version'] = response.json()
                debug_info['ollama_accessible'] = True
            else:
                debug_info['ollama_accessible'] = False
                debug_info['ollama_error'] = f"HTTP {response.status_code}"
        except Exception as e:
            debug_info['ollama_accessible'] = False
            debug_info['ollama_error'] = str(e)
        
        # Liste des modèles
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=10)
            if response.status_code == 200:
                models_data = response.json()
                debug_info['models'] = models_data.get('models', [])
                debug_info['llava_models'] = [
                    m['name'] for m in debug_info['models'] 
                    if 'llava' in m['name'].lower()
                ]
            else:
                debug_info['models_error'] = f"HTTP {response.status_code}"
        except Exception as e:
            debug_info['models_error'] = str(e)
        
        return jsonify(debug_info)
        
    except Exception as e:
        log_error_safely(e, "debug_ollama")
        return jsonify({'debug_error': 'Erreur de diagnostic'}), 500

@app.route('/api/quick-responses/test', methods=['GET'])
def test_quick_responses_endpoint():
    """Endpoint pour tester le système de réponses rapides"""
    if not app.debug:
        return jsonify({'error': 'Test non disponible'}), 403
        
    try:
        if not quick_response_system:
            return jsonify({'error': 'Système de réponses rapides non initialisé'}), 503
        
        test_messages = [
            "Comment vous contacter?",
            "Quel est votre numéro de téléphone?", 
            "Je veux des infos sur les admissions",
            "Quels sont les frais de scolarité?",
            "Où se trouve le campus?",
        ]
        
        results = []
        for message in test_messages:
            quick_resp = quick_response_system.get_quick_response(message)
            results.append({
                'message': message,
                'has_quick_response': quick_resp is not None,
                'confidence': quick_resp.get('confidence', 0) if quick_resp else 0,
                'category': quick_resp.get('category') if quick_resp else None,
                'response_preview': quick_resp['response'][:100] + '...' if quick_resp else None
            })
        
        return jsonify({
            'status': 'ok',
            'total_tests': len(test_messages),
            'successful_responses': len([r for r in results if r['has_quick_response']]),
            'results': results
        })
    except Exception as e:
        log_error_safely(e, "test_quick_responses_endpoint")
        return jsonify({'error': 'Erreur de test'}), 500

if __name__ == '__main__':
    logger.info("🔧 Tests de démarrage...")
    
    # Test Ollama au démarrage
    ollama_ok, llava_models = test_ollama_connection()
    
    if ollama_ok and llava_models:
        logger.info(f"✅ Ollama opérationnel avec {len(llava_models)} modèles llava!")
        
        # Test rapide du premier modèle
        if test_model_response(llava_models[0]):
            logger.info("✅ Modèle testé et fonctionnel!")
        else:
            logger.warning("⚠️ Problème avec le modèle - le chatbot peut dysfonctionner")
    else:
        logger.error("❌ Problèmes Ollama critiques détectés!")
        logger.info("💡 Solutions possibles:")
        logger.info("   1. Vérifiez qu'Ollama est démarré: ollama serve")
        logger.info("   2. Installez llava: ollama pull llava:latest")
        logger.info("   3. Redémarrez Ollama si nécessaire")
        logger.info("   4. Testez manuellement: ollama run llava:latest 'hello'")
    
    # Tentative d'initialisation RAG
    rag_ok = initialize_rag_system()
    if rag_ok:
        logger.info("✅ Système RAG opérationnel!")
    else:
        logger.warning("⚠️ RAG non initialisé (fonctionnement en mode simple)")
    
    # Initialisation réponses rapides
    quick_ok = initialize_quick_responses()
    if quick_ok:
        logger.info("⚡ Système de réponses rapides opérationnel!")
    else:
        logger.warning("⚠️ Réponses rapides non initialisées")
    
    logger.info("\n🌐 Serveur Flask démarré sur:")
    logger.info("   - Frontend: http://localhost:5000")
    logger.info("   - API Test: http://localhost:5000/api/test")
    logger.info("   - API Status: http://localhost:5000/api/status")
    
    if app.debug:
        logger.info("   - Debug Ollama: http://localhost:5000/api/debug/ollama")
    
    logger.info("\n🔧 Pour déboguer:")
    logger.info("   1. Testez: http://localhost:5000/api/test")
    logger.info("   2. Status: http://localhost:5000/api/status")  
    if app.debug:
        logger.info("   3. Debug Ollama: http://localhost:5000/api/debug/ollama")
    logger.info("   4. Si problèmes: Vérifiez les logs dans le terminal")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
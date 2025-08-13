from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import ollama
import sys
import json
import os
from pathlib import Path
import time

# Import des modules RAG et memory (avec gestion d'erreur)
try:
    from rag.retriever import RagRetriever
    from rag.vector_db import VectorDB
    from rag.loader import DocumentLoader
    from memory.manager import MemoryManager
    RAG_AVAILABLE = True
    print("✅ Modules RAG importés avec succès")
except ImportError as e:
    print(f"⚠️  Modules RAG non disponibles: {e}")
    print("💡 Le chatbot fonctionnera sans RAG")
    RAG_AVAILABLE = False

app = Flask(__name__) 
CORS(app)

print("🚀 Démarrage du serveur Flask...")

# Initialisation des composants RAG
rag_retriever = None
memory_manager = None
document_loader = None
rag_initialized = False

def test_ollama_connection():
    """Test de connexion Ollama amélioré avec retry"""
    max_retries = 3
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            print(f"🔍 Test de connexion à Ollama (tentative {attempt + 1}/{max_retries})...")
            
            # Test de base avec timeout
            response = ollama.list()
            
            if not response or 'models' not in response:
                raise Exception("Réponse Ollama invalide")
                
            model_names = [model.get('name', '') for model in response.get('models', [])]
            print(f"✅ Modèles disponibles: {model_names}")
            
            # Vérifier llava spécifiquement
            llava_models = [name for name in model_names if 'llava' in name.lower()]
            
            if not llava_models:
                print("⚠️ Aucun modèle llava trouvé!")
                print("💡 Installez-le avec: ollama pull llava:latest")
                return False, []
            
            print(f"✅ Modèles llava disponibles: {llava_models}")
            return True, llava_models
            
        except Exception as e:
            print(f"❌ Tentative {attempt + 1} échouée: {e}")
            if attempt < max_retries - 1:
                print(f"⏳ Nouvelle tentative dans {retry_delay} secondes...")
                time.sleep(retry_delay)
            else:
                print("❌ Toutes les tentatives de connexion ont échoué")
                print("💡 Vérifiez que Ollama est démarré: ollama serve")
                return False, []

def get_best_llava_model():
    """Trouve le meilleur modèle llava disponible"""
    try:
        response = ollama.list()
        model_names = [model.get('name', '') for model in response.get('models', [])]
        
        # Priorités des modèles llava (du meilleur au moins bon)
        preferred_models = [
            'llava:latest',
            'llava:13b',
            'llava:7b',
            'llava'
        ]
        
        for preferred in preferred_models:
            for available in model_names:
                if preferred in available.lower():
                    return available
        
        # Fallback: n'importe quel modèle contenant "llava"
        for available in model_names:
            if 'llava' in available.lower():
                return available
                
        return None
    except Exception:
        return None

def initialize_rag_system():
    """Initialise le système RAG si possible"""
    global rag_retriever, memory_manager, document_loader, rag_initialized
    
    if not RAG_AVAILABLE:
        print("⚠️  RAG non disponible - modules non importés")
        return False
    
    try:
        print("📄 Initialisation du système RAG...")
        
        # Créer les dossiers nécessaires
        os.makedirs("data/documents", exist_ok=True)
        os.makedirs("data/vector_db", exist_ok=True)
        os.makedirs("data/memory", exist_ok=True)
        
        # Initialiser le document loader
        document_loader = DocumentLoader("data/documents")
        
        # Scanner les documents disponibles
        docs_info = document_loader.scan_documents()
        print(f"📊 Documents scannés:")
        print(f"   - Total fichiers: {docs_info['total_files']}")
        print(f"   - Fichiers supportés: {docs_info['supported_files']}")
        print(f"   - Types supportés: {', '.join(document_loader.get_supported_extensions())}")
        
        if docs_info['supported_files'] == 0:
            print("⚠️  Aucun document supporté trouvé")
            print("💡 Le système RAG sera initialisé sans documents")
        
        # Initialiser les composants (même sans documents)
        try:
            vector_db = VectorDB()
            # Charger les documents seulement s'ils existent
            if docs_info['supported_files'] > 0:
                vector_db.initialize()
                print("✅ Base vectorielle initialisée avec documents")
            else:
                print("✅ Base vectorielle initialisée (vide)")
            
            rag_retriever = RagRetriever()
            memory_manager = MemoryManager()
            
            rag_initialized = True
            print("✅ Système RAG initialisé!")
            return True
            
        except Exception as e:
            print(f"⚠️ Erreur initialisation composants RAG: {e}")
            print("💡 Le système fonctionnera sans RAG")
            return False
            
    except Exception as e:
        print(f"❌ Erreur RAG: {e}")
        return False

def test_model_response(model_name):
    """Test si un modèle répond correctement"""
    try:
        print(f"🧪 Test du modèle {model_name}...")
        
        response = ollama.chat(
            model=model_name,
            messages=[{
                'role': 'user',
                'content': 'Hello, respond with just "OK" to confirm you work.'
            }],
            options={'temperature': 0.1}
        )
        
        if response and 'message' in response and 'content' in response['message']:
            print(f"✅ Modèle {model_name} fonctionne!")
            return True
        else:
            print(f"❌ Réponse invalide du modèle {model_name}")
            return False
            
    except Exception as e:
        print(f"❌ Erreur test modèle {model_name}: {e}")
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
        print(f"⚠️  Erreur recherche RAG: {e}")
        return user_message, False

@app.route('/')
def serve_html():
    """Servir le fichier HTML depuis le dossier parent"""
    try:
        # Le HTML est dans ../frontend par rapport au script backend/app.py
        return send_from_directory('../frontend', 'chatbot.html')
    except Exception as e:
        return f"Erreur: Impossible de charger chatbot.html - {e}", 404

@app.route('/api/status', methods=['GET'])
def status():
    """Endpoint de diagnostic complet"""
    try:
        # Test Ollama avec retry
        ollama_ok, llava_models = test_ollama_connection()
        
        # Informations sur les documents
        docs_info = {'total_files': 0, 'supported_files': 0, 'files_by_type': {}}
        if document_loader:
            try:
                docs_info = document_loader.scan_documents()
            except Exception as e:
                print(f"Erreur scan documents: {e}")
        
        return jsonify({
            'status': 'ok' if ollama_ok else 'warning',
            'ollama_connected': ollama_ok,
            'models_available': llava_models,
            'llava_ready': len(llava_models) > 0,
            'rag_available': RAG_AVAILABLE,
            'rag_initialized': rag_initialized,
            'documents': {
                'total_files': docs_info['total_files'],
                'supported_files': docs_info['supported_files'],
                'files_by_type': docs_info.get('files_by_type', {}),
                'supported_extensions': document_loader.get_supported_extensions() if document_loader else ['.pdf']
            }
        })
        
    except Exception as e:
        print(f"❌ Erreur status: {e}")
        return jsonify({
            'status': 'error',
            'ollama_connected': False,
            'rag_available': RAG_AVAILABLE,
            'rag_initialized': False,
            'error': str(e)
        }), 503

@app.route('/api/test', methods=['GET'])
def test_endpoint():
    """Endpoint de test basique"""
    return jsonify({
        'message': 'Server is running!',
        'status': 'ok',
        'timestamp': time.time()
    })

@app.route('/api/initialize-rag', methods=['POST'])
def initialize_rag_endpoint():
    """Endpoint pour initialiser/réinitialiser le RAG"""
    success = initialize_rag_system()
    
    docs_info = {}
    if document_loader:
        try:
            docs_info = document_loader.scan_documents()
        except Exception as e:
            print(f"Erreur scan documents: {e}")
    
    return jsonify({
        "success": success,
        "rag_initialized": rag_initialized,
        "message": "RAG system initialized" if success else "RAG initialization failed",
        "documents_info": docs_info
    })

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        print(f"📨 Nouvelle requête chat")
        
        # Validation des données
        data = request.json
        if not data:
            return jsonify({'error': 'Données JSON manquantes'}), 400
            
        user_message = data.get('message', '').strip()
        image_b64 = data.get('image')
        
        if not user_message and not image_b64:
            return jsonify({'error': 'Message ou image requis'}), 400

        print(f"💬 Message: '{user_message[:50]}{'...' if len(user_message) > 50 else ''}'")
        print(f"🖼️  Image: {'Oui' if image_b64 else 'Non'}")

        # Trouver le meilleur modèle llava disponible
        model_to_use = get_best_llava_model()
        if not model_to_use:
            return jsonify({
                'error': 'Aucun modèle llava disponible. Installez avec: ollama pull llava:latest'
            }), 503

        print(f"🎯 Utilisation du modèle: {model_to_use}")

        # Test rapide du modèle avant utilisation
        if not test_model_response(model_to_use):
            return jsonify({
                'error': f'Le modèle {model_to_use} ne répond pas correctement'
            }), 503

        # Enrichissement avec RAG (seulement pour les messages texte sans image)
        rag_used = False
        if user_message and not image_b64:
            enhanced_message, rag_used = enhance_prompt_with_rag(user_message)
            if rag_used:
                print("📚 Message enrichi avec RAG")
        else:
            enhanced_message = user_message or "Décris cette image en détail"

        # Préparation du message pour Ollama
        messages = [{
            'role': 'user',
            'content': enhanced_message
        }]
        
        if image_b64:
            messages[0]['images'] = [image_b64]

        print("🤖 Appel à Ollama...")
        
        try:
            response = ollama.chat(
                model=model_to_use,
                messages=messages,
                options={
                    'temperature': 0.7,
                    'num_predict': 512,  # Limiter la longueur de réponse
                    'timeout': 60       # Timeout plus long
                }
            )
            
            if not response or 'message' not in response or 'content' not in response['message']:
                raise Exception("Réponse Ollama invalide")
            
            bot_response = response['message']['content'].strip()
            
            if not bot_response:
                bot_response = "Désolé, je n'ai pas pu générer une réponse appropriée."
            
            print(f"✅ Réponse générée: {len(bot_response)} caractères")
            
            # Sauvegarder dans la mémoire si disponible
            if memory_manager:
                try:
                    memory_manager.add_conversation(
                        user_message=user_message,
                        bot_response=bot_response,
                        metadata={
                            "rag_used": rag_used,
                            "has_image": bool(image_b64),
                            "model": model_to_use
                        }
                    )
                except Exception as e:
                    print(f"⚠️  Erreur sauvegarde mémoire: {e}")
            
            return jsonify({
                'response': bot_response,
                'status': 'success',
                'model_used': model_to_use,
                'rag_used': rag_used
            })
            
        except Exception as e:
            print(f"❌ Erreur Ollama détaillée: {e}")
            error_msg = str(e)
            
            if "connection" in error_msg.lower():
                error_msg = "Impossible de se connecter à Ollama. Vérifiez qu'Ollama est démarré."
            elif "timeout" in error_msg.lower():
                error_msg = "Timeout: La génération a pris trop de temps."
            elif "model" in error_msg.lower():
                error_msg = f"Problème avec le modèle {model_to_use}. Essayez de le réinstaller."
            
            return jsonify({
                'error': f'Erreur Ollama: {error_msg}'
            }), 503
            
    except Exception as e:
        print(f"❌ Erreur serveur: {e}")
        return jsonify({
            'error': f'Erreur serveur interne: {str(e)}'
        }), 500

if __name__ == '__main__':
    print("🔧 Tests de démarrage...")
    
    # Test Ollama au démarrage
    ollama_ok, llava_models = test_ollama_connection()
    
    if ollama_ok and llava_models:
        print(f"✅ Ollama opérationnel avec {len(llava_models)} modèles llava!")
        
        # Test rapide du premier modèle
        if test_model_response(llava_models[0]):
            print("✅ Modèle testé et fonctionnel!")
        else:
            print("⚠️ Problème avec le modèle - le chatbot peut dysfonctionner")
    else:
        print("❌ Problèmes Ollama critiques détectés!")
        print("💡 Solutions possibles:")
        print("   1. Vérifiez qu'Ollama est démarré: ollama serve")
        print("   2. Installez llava: ollama pull llava:latest")
        print("   3. Redémarrez Ollama si nécessaire")
    
    # Tentative d'initialisation RAG
    rag_ok = initialize_rag_system()
    if rag_ok:
        print("✅ Système RAG opérationnel!")
    else:
        print("⚠️  RAG non initialisé (fonctionnement en mode simple)")
    
    print("\n🌐 Serveur Flask démarré sur:")
    print("   - Frontend: http://localhost:5000")
    print("   - API Test: http://localhost:5000/api/test")
    print("   - API Status: http://localhost:5000/api/status")
    print("\n🔧 Pour déboguer:")
    print("   1. Testez: http://localhost:5000/api/test")
    print("   2. Status: http://localhost:5000/api/status")
    print("   3. Si problèmes: Vérifiez les logs ci-dessus")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
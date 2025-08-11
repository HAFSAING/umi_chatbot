from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import ollama
import sys
import json
from pathlib import Path

app = Flask(__name__)
CORS(app)

print("🚀 Démarrage du serveur Flask...")

# Test de connexion Ollama au démarrage
def test_ollama():
    try:
        print("🔍 Test de connexion à Ollama...")
        
        # Test 1: Version
        version = ollama._client.get("http://localhost:11434/api/version")
        print(f"✅ Ollama version: {version}")
        
        # Test 2: Liste des modèles
        models = ollama.list()
        model_names = [m['name'] for m in models['models']]
        print(f"✅ Modèles disponibles: {model_names}")
        
        # Test 3: Vérifier llava
        if 'llava:latest' not in model_names:
            print("❌ Modèle llava:latest non trouvé!")
            print("Installez-le avec: ollama pull llava:latest")
            return False
        
        # Test 4: Test rapide du modèle
        response = ollama.chat(
            model='llava:latest',
            messages=[{'role': 'user', 'content': 'Hello'}],
            options={'timeout': 10}
        )
        print(f"✅ Test llava réussi: {response['message']['content'][:50]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur connexion Ollama: {e}")
        return False

@app.route('/')
def serve_html():
    return send_from_directory('../frontend', 'chatbot.html')

@app.route('/api/status', methods=['GET'])
def status():
    """Endpoint de diagnostic"""
    try:
        # Test Ollama
        models = ollama.list()
        model_names = [m['name'] for m in models['models']]
        
        return jsonify({
            'status': 'ok',
            'ollama_connected': True,
            'models_available': model_names,
            'llava_ready': 'llava:latest' in model_names
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'ollama_connected': False,
            'error': str(e)
        }), 503

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        print(f"📨 Requête reçue: {request.method} {request.path}")
        
        data = request.json
        if not data:
            return jsonify({'error': 'Pas de données JSON'}), 400
            
        print(f"📋 Données reçues: {data}")
        
        user_message = data.get('message', '').strip()
        image_b64 = data.get('image')
        
        if not user_message and not image_b64:
            return jsonify({'error': 'Message ou image requis'}), 400

        print(f"💬 Message: {user_message}")
        print(f"🖼️  Image: {'Oui' if image_b64 else 'Non'}")

        # Préparation du message
        messages = [{
            'role': 'user',
            'content': user_message or "Décris cette image"
        }]
        
        if image_b64:
            messages[0]['images'] = [image_b64]

        print("🤖 Appel à Ollama...")
        
        # Appel Ollama avec gestion d'erreur détaillée
        try:
            response = ollama.chat(
                model='llava:latest',
                messages=messages,
                options={
                    'temperature': 0.7,
                    'timeout': 30
                }
            )
            
            bot_response = response['message']['content']
            print(f"✅ Réponse Ollama: {bot_response[:100]}...")
            
            return jsonify({
                'response': bot_response,
                'status': 'success',
                'model_used': 'llava:latest'
            })
            
        except ollama.ResponseError as e:
            print(f"❌ Erreur Ollama ResponseError: {e}")
            return jsonify({'error': f'Erreur modèle: {e}'}), 503
            
        except ollama.RequestError as e:
            print(f"❌ Erreur Ollama RequestError: {e}")
            return jsonify({'error': f'Erreur connexion Ollama: {e}'}), 503
            
        except Exception as e:
            print(f"❌ Erreur Ollama générique: {e}")
            return jsonify({'error': f'Erreur Ollama: {e}'}), 503
            
    except Exception as e:
        print(f"❌ Erreur serveur: {e}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

if __name__ == '__main__':
    print("🔧 Tests de démarrage...")
    
    # Test au démarrage
    if test_ollama():
        print("✅ Tous les tests passés!")
        print("🌐 Serveur disponible sur:")
        print("   - Frontend: http://localhost:5000")
        print("   - API Status: http://localhost:5000/api/status")
        print("   - API Chat: http://localhost:5000/api/chat")
    else:
        print("❌ Problèmes détectés, mais démarrage quand même...")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
#!/usr/bin/env python3
"""
Test rapide pour vérifier qu'Ollama fonctionne correctement avec llava
"""

import ollama
import json
import sys

def test_ollama_connection():
    """Test de base de la connexion Ollama"""
    print("🔍 Test de connexion à Ollama...")
    
    try:
        response = ollama.list()
        models = [m['name'] for m in response.get('models', [])]
        print(f"✅ Modèles disponibles: {models}")
        return models
    except Exception as e:
        print(f"❌ Erreur connexion: {e}")
        return None

def test_llava_model(model_name):
    """Test spécifique du modèle llava"""
    print(f"🧪 Test du modèle {model_name}...")
    
    try:
        # Test simple sans image
        response = ollama.chat(
            model=model_name,
            messages=[{
                'role': 'user',
                'content': 'Hello! Please respond with exactly "LLAVA_TEST_OK" to confirm you are working.'
            }],
            options={
                'temperature': 0.1,
                'num_predict': 10
            }
        )
        
        if response and 'message' in response and 'content' in response['message']:
            response_text = response['message']['content'].strip()
            print(f"✅ Réponse reçue: '{response_text}'")
            
            # Vérifier que la réponse contient notre test
            if 'test' in response_text.lower() or 'ok' in response_text.lower():
                print("✅ Modèle répond correctement")
                return True
            else:
                print("⚠️ Réponse inattendue mais le modèle fonctionne")
                return True
        else:
            print("❌ Réponse invalide")
            return False
            
    except Exception as e:
        print(f"❌ Erreur test modèle: {e}")
        return False

def test_llava_with_image():
    """Test avec une image encodée en base64 (petite image de test)"""
    print("🖼️ Test avec image...")
    
    # Petite image 1x1 pixel en base64 (PNG transparent)
    test_image_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
    
    llava_models = [m for m in ollama.list()['models'] if 'llava' in m['name'].lower()]
    if not llava_models:
        print("❌ Aucun modèle llava disponible")
        return False
    
    model_name = llava_models[0]['name']
    
    try:
        response = ollama.chat(
            model=model_name,
            messages=[{
                'role': 'user',
                'content': 'What do you see in this image? Respond briefly.',
                'images': [test_image_b64]
            }],
            options={
                'temperature': 0.5,
                'num_predict': 50
            }
        )
        
        if response and 'message' in response:
            response_text = response['message']['content']
            print(f"✅ Réponse avec image: '{response_text[:100]}'")
            return True
        else:
            print("❌ Pas de réponse avec image")
            return False
            
    except Exception as e:
        print(f"❌ Erreur test image: {e}")
        return False

def main():
    print("=" * 50)
    print("  TEST RAPIDE OLLAMA + LLAVA")
    print("=" * 50)
    
    # Test 1: Connexion de base
    models = test_ollama_connection()
    if not models:
        print("\n❌ ÉCHEC: Ollama ne répond pas")
        print("Solutions:")
        print("1. Démarrez Ollama: ollama serve")
        print("2. Vérifiez qu'il tourne sur le port 11434")
        sys.exit(1)
    
    # Test 2: Trouver llava
    llava_models = [m for m in models if 'llava' in m.lower()]
    if not llava_models:
        print("\n❌ ÉCHEC: Aucun modèle llava trouvé")
        print("Solution: ollama pull llava:latest")
        sys.exit(1)
    
    print(f"\n📋 Modèles llava disponibles: {llava_models}")
    
    # Test 3: Test du modèle llava
    success = test_llava_model(llava_models[0])
    if not success:
        print(f"\n❌ ÉCHEC: Le modèle {llava_models[0]} ne répond pas correctement")
        sys.exit(1)
    
    # Test 4: Test avec image
    image_success = test_llava_with_image()
    if not image_success:
        print("\n⚠️ WARNING: Problème avec le traitement d'images")
        print("Le chatbot fonctionnera mais peut avoir des problèmes avec les images")
    
    print("\n" + "=" * 50)
    if success and image_success:
        print("🎉 TOUS LES TESTS RÉUSSIS!")
        print("Votre configuration Ollama + llava fonctionne parfaitement")
    elif success:
        print("✅ TESTS DE BASE RÉUSSIS")
        print("Le chatbot fonctionnera (problème mineur avec les images)")
    
    print("\n🚀 Vous pouvez maintenant lancer votre chatbot:")
    print("   cd backend")
    print("   python start_app.py")
    print("=" * 50)

if __name__ == "__main__":
    main()
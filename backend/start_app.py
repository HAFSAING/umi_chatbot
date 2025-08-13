#!/usr/bin/env python3
"""
Script de démarrage pour le chatbot UMI
Place ce fichier dans le dossier backend/ et lance-le depuis là
"""

import os
import sys
import time
import ollama
from pathlib import Path

def print_header(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def print_step(message, status="INFO"):
    symbols = {"INFO": "ℹ️", "OK": "✅", "ERROR": "❌", "WARNING": "⚠️"}
    print(f"{symbols.get(status)} {message}")

def verify_ollama():
    """Vérifie qu'Ollama fonctionne correctement"""
    print_header("VÉRIFICATION OLLAMA")
    
    try:
        print_step("Test de connexion à Ollama...")
        response = ollama.list()
        models = [m['name'] for m in response.get('models', [])]
        
        print_step(f"Modèles disponibles: {', '.join(models)}", "OK")
        
        # Vérifier llava spécifiquement
        llava_models = [m for m in models if 'llava' in m.lower()]
        if llava_models:
            print_step(f"Modèle llava trouvé: {llava_models[0]}", "OK")
            
            # Test rapide de génération
            print_step("Test de génération...")
            test_response = ollama.chat(
                model=llava_models[0],
                messages=[{'role': 'user', 'content': 'Respond with "TEST OK"'}],
                options={'temperature': 0.1}
            )
            
            if test_response and 'message' in test_response:
                response_text = test_response['message']['content']
                print_step(f"Réponse du modèle: {response_text[:50]}", "OK")
                return True
            else:
                print_step("Réponse invalide", "ERROR")
                return False
        else:
            print_step("Aucun modèle llava trouvé!", "ERROR")
            return False
            
    except Exception as e:
        print_step(f"Erreur Ollama: {e}", "ERROR")
        print_step("Solutions:", "WARNING")
        print("   1. Vérifiez qu'Ollama est démarré: ollama serve")
        print("   2. Dans un autre terminal, testez: ollama list")
        print("   3. Si ça ne marche pas, redémarrez Ollama")
        return False

def verify_structure():
    """Vérifie la structure du projet"""
    print_header("VÉRIFICATION STRUCTURE")
    
    current_dir = Path.cwd()
    print_step(f"Répertoire actuel: {current_dir}")
    
    # Vérifier qu'on est dans backend/
    if current_dir.name != "backend":
        print_step("⚠️ Vous devez être dans le dossier backend/", "WARNING")
        print("   Faites: cd backend")
        return False
    
    # Vérifier les fichiers nécessaires
    required_files = [
        "app.py",
        "rag/__init__.py",
        "rag/loader.py", 
        "rag/vector_db.py",
        "rag/retriever.py",
        "memory/__init__.py",
        "memory/manager.py",
        "../frontend/chatbot.html"
    ]
    
    missing_files = []
    for file_path in required_files:
        if Path(file_path).exists():
            print_step(f"✓ {file_path}", "OK")
        else:
            print_step(f"✗ {file_path}", "ERROR")
            missing_files.append(file_path)
    
    if missing_files:
        print_step(f"Fichiers manquants: {missing_files}", "ERROR")
        return False
    
    # Créer les dossiers data/ si nécessaire
    data_dirs = ["../data/documents", "../data/memory", "../data/vector_db"]
    for dir_path in data_dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        print_step(f"Dossier {dir_path} prêt", "OK")
    
    return True

def test_imports():
    """Teste les imports des modules"""
    print_header("VÉRIFICATION IMPORTS")
    
    try:
        import flask
        print_step("Flask: OK", "OK")
    except ImportError:
        print_step("Flask manquant: pip install flask", "ERROR")
        return False
    
    try:
        import flask_cors
        print_step("Flask-CORS: OK", "OK")
    except ImportError:
        print_step("Flask-CORS manquant: pip install flask-cors", "ERROR")
        return False
    
    try:
        import ollama
        print_step("Ollama: OK", "OK")
    except ImportError:
        print_step("Ollama manquant: pip install ollama", "ERROR")
        return False
    
    try:
        from rag.loader import DocumentLoader
        print_step("RAG modules: OK", "OK")
    except ImportError as e:
        print_step(f"RAG modules: Problème - {e}", "WARNING")
        print("   L'application fonctionnera sans RAG")
    
    return True

def main():
    print_header("DÉMARRAGE CHATBOT UMI")
    
    # Étape 1: Vérifier la structure
    if not verify_structure():
        print_step("Problème de structure détecté", "ERROR")
        return False
    
    # Étape 2: Tester les imports
    if not test_imports():
        print_step("Problème d'imports détecté", "ERROR")
        return False
    
    # Étape 3: Vérifier Ollama
    if not verify_ollama():
        print_step("Problème Ollama détecté", "ERROR")
        return False
    
    print_header("DÉMARRAGE SERVEUR")
    print_step("Tous les tests sont passés!", "OK")
    print_step("Démarrage de l'application...", "INFO")
    
    # Importer et lancer l'app
    try:
        from app import app
        print("\n🌐 Serveur disponible sur:")
        print("   - Frontend: http://localhost:5000")
        print("   - API Test: http://localhost:5000/api/test")
        print("   - API Status: http://localhost:5000/api/status")
        print("\n🔧 Ctrl+C pour arrêter le serveur")
        
        app.run(host='0.0.0.0', port=5000, debug=True)
        
    except Exception as e:
        print_step(f"Erreur démarrage app: {e}", "ERROR")
        return False

if __name__ == "__main__":
    main()
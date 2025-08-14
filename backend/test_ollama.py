#!/usr/bin/env python3
"""
Script de diagnostic complet pour Ollama + LLaVA
Place ce fichier dans le dossier backend/ et lance-le
"""

import ollama
import time
import sys
import subprocess
import requests
import json
from pathlib import Path

def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def print_status(message, status="INFO"):
    symbols = {"INFO": "ℹ️", "OK": "✅", "ERROR": "❌", "WARNING": "⚠️"}
    print(f"{symbols.get(status, 'ℹ️')} {message}")

def check_ollama_service():
    """Vérifie si le service Ollama tourne"""
    print_section("VÉRIFICATION SERVICE OLLAMA")
    
    try:
        # Vérifier via HTTP directement
        response = requests.get("http://localhost:11434/api/version", timeout=5)
        if response.status_code == 200:
            version_info = response.json()
            print_status(f"Service Ollama actif - Version: {version_info.get('version', 'N/A')}", "OK")
            return True
        else:
            print_status(f"Service Ollama répond mais erreur HTTP {response.status_code}", "WARNING")
            return False
    except requests.exceptions.ConnectionError:
        print_status("Service Ollama non accessible sur localhost:11434", "ERROR")
        print_status("Solutions:", "INFO")
        print("   1. Démarrer Ollama: ollama serve")
        print("   2. Ou si déjà démarré: pkill ollama puis ollama serve")
        return False
    except Exception as e:
        print_status(f"Erreur vérification service: {e}", "ERROR")
        return False

def check_ollama_models():
    """Vérifie les modèles installés"""
    print_section("VÉRIFICATION MODÈLES OLLAMA")
    
    try:
        # Utiliser directement l'API REST pour plus de fiabilité
        response = requests.get("http://localhost:11434/api/tags", timeout=10)
        
        if response.status_code != 200:
            print_status(f"Erreur récupération modèles: HTTP {response.status_code}", "ERROR")
            return []
        
        data = response.json()
        models = data.get('models', [])
        
        if not models:
            print_status("Aucun modèle installé", "ERROR")
            print_status("Installez LLaVA avec: ollama pull llava:latest", "INFO")
            return []
        
        print_status(f"Modèles installés: {len(models)}", "OK")
        
        model_names = []
        llava_models = []
        
        for model in models:
            name = model.get('name', 'N/A')
            size = model.get('size', 0)
            size_gb = size / (1024**3) if size else 0
            
            model_names.append(name)
            print(f"   - {name} ({size_gb:.1f}GB)")
            
            if 'llava' in name.lower():
                llava_models.append(name)
        
        if llava_models:
            print_status(f"Modèles LLaVA trouvés: {llava_models}", "OK")
        else:
            print_status("Aucun modèle LLaVA trouvé!", "ERROR")
            print_status("Solutions:", "INFO")
            print("   1. ollama pull llava:latest")
            print("   2. ollama pull llava:13b")
            print("   3. ollama pull llava:7b")
        
        return llava_models
        
    except Exception as e:
        print_status(f"Erreur vérification modèles: {e}", "ERROR")
        return []

def test_model_generation(model_name):
    """Test de génération avec un modèle"""
    print_section(f"TEST GÉNÉRATION - {model_name}")
    
    try:
        print_status("Test de génération simple...", "INFO")
        
        # Test avec l'API REST directement
        payload = {
            "model": model_name,
            "messages": [
                {"role": "user", "content": "Say 'OLLAMA_TEST_SUCCESS' to confirm you work."}
            ],
            "stream": False,
            "options": {
                "temperature": 0.1,
                "num_predict": 20
            }
        }
        
        response = requests.post(
            "http://localhost:11434/api/chat",
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result.get('message', {}).get('content', '')
            print_status(f"Réponse: '{content[:100]}'", "OK")
            
            if 'success' in content.lower() or 'test' in content.lower():
                print_status("Test de génération réussi!", "OK")
                return True
            else:
                print_status("Génération fonctionne mais réponse inattendue", "WARNING")
                return True
        else:
            print_status(f"Erreur génération: HTTP {response.status_code}", "ERROR")
            print_status(f"Réponse: {response.text[:200]}", "ERROR")
            return False
            
    except requests.exceptions.Timeout:
        print_status("Timeout lors de la génération (>30s)", "ERROR")
        return False
    except Exception as e:
        print_status(f"Erreur test génération: {e}", "ERROR")
        return False

def test_image_processing(model_name):
    """Test du traitement d'images"""
    print_section(f"TEST TRAITEMENT IMAGE - {model_name}")
    
    # Image de test 1x1 pixel en base64 (PNG transparent)
    test_image = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
    
    try:
        payload = {
            "model": model_name,
            "messages": [
                {
                    "role": "user",
                    "content": "What do you see in this image? Be brief.",
                    "images": [test_image]
                }
            ],
            "stream": False,
            "options": {
                "temperature": 0.5,
                "num_predict": 50
            }
        }
        
        response = requests.post(
            "http://localhost:11434/api/chat",
            json=payload,
            timeout=45
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result.get('message', {}).get('content', '')
            print_status(f"Analyse image: '{content[:80]}'", "OK")
            return True
        else:
            print_status(f"Erreur traitement image: HTTP {response.status_code}", "ERROR")
            return False
            
    except Exception as e:
        print_status(f"Erreur test image: {e}", "ERROR")
        return False

def test_ollama_python_lib():
    """Test de la librairie Python ollama"""
    print_section("TEST LIBRAIRIE PYTHON OLLAMA")
    
    try:
        print_status("Test connexion via librairie Python...", "INFO")
        
        # Test basique
        models = ollama.list()
        if models and 'models' in models:
            model_names = [m['name'] for m in models['models']]
            print_status(f"Librairie Python OK - {len(model_names)} modèles", "OK")
            
            # Test avec LLaVA si disponible
            llava_models = [m for m in model_names if 'llava' in m.lower()]
            if llava_models:
                try:
                    response = ollama.chat(
                        model=llava_models[0],
                        messages=[{'role': 'user', 'content': 'Hello, respond briefly.'}],
                        options={'temperature': 0.1, 'num_predict': 10}
                    )
                    
                    if response and 'message' in response:
                        print_status("Test génération Python OK", "OK")
                        return True
                except Exception as e:
                    print_status(f"Erreur génération Python: {e}", "WARNING")
                    return False
            return True
        else:
            print_status("Librairie Python: réponse invalide", "ERROR")
            return False
            
    except Exception as e:
        print_status(f"Erreur librairie Python: {e}", "ERROR")
        return False

def check_system_resources():
    """Vérifie les ressources système"""
    print_section("VÉRIFICATION RESSOURCES SYSTÈME")
    
    try:
        import psutil
        
        # RAM
        memory = psutil.virtual_memory()
        memory_gb = memory.total / (1024**3)
        memory_available = memory.available / (1024**3)
        
        print_status(f"RAM totale: {memory_gb:.1f}GB", "INFO")
        print_status(f"RAM disponible: {memory_available:.1f}GB", "INFO")
        
        if memory_available < 4:
            print_status("RAM faible - LLaVA peut être lent", "WARNING")
        else:
            print_status("RAM suffisante", "OK")
        
        # Processus Ollama
        ollama_processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info']):
            if 'ollama' in proc.info['name'].lower():
                ollama_processes.append(proc.info)
        
        if ollama_processes:
            print_status(f"Processus Ollama actifs: {len(ollama_processes)}", "OK")
            for proc in ollama_processes:
                memory_mb = proc['memory_info'].rss / (1024*1024)
                print(f"   - PID {proc['pid']}: {proc['name']} ({memory_mb:.0f}MB)")
        else:
            print_status("Aucun processus Ollama détecté", "WARNING")
            
    except ImportError:
        print_status("Module psutil non disponible - ignoré", "INFO")
    except Exception as e:
        print_status(f"Erreur vérification ressources: {e}", "WARNING")

def fix_common_issues():
    """Propose des solutions aux problèmes courants"""
    print_section("SOLUTIONS RECOMMANDÉES")
    
    print_status("Si le diagnostic échoue, essayez dans cet ordre:", "INFO")
    print()
    print("1️⃣ REDÉMARRAGE OLLAMA:")
    print("   pkill ollama")
    print("   ollama serve")
    print()
    print("2️⃣ VÉRIFICATION MODÈLES:")
    print("   ollama list")
    print("   ollama pull llava:latest")
    print()
    print("3️⃣ TEST MANUEL:")
    print("   ollama run llava:latest \"Hello, test\"")
    print()
    print("4️⃣ SI PROBLÈME PERSISTANT:")
    print("   - Redémarrer complètement Ollama")
    print("   - Vérifier les logs: journalctl -f -u ollama (Linux)")
    print("   - Réinstaller le modèle: ollama rm llava:latest && ollama pull llava:latest")

def main():
    print("🔧 DIAGNOSTIC COMPLET OLLAMA + LLAVA")
    print("="*60)
    
    success_count = 0
    total_tests = 5
    
    # Test 1: Service Ollama
    if check_ollama_service():
        success_count += 1
    else:
        print_status("ARRÊT: Service Ollama non accessible", "ERROR")
        fix_common_issues()
        return False
    
    # Test 2: Modèles disponibles
    llava_models = check_ollama_models()
    if llava_models:
        success_count += 1
    else:
        print_status("ARRÊT: Aucun modèle LLaVA trouvé", "ERROR")
        fix_common_issues()
        return False
    
    # Test 3: Librairie Python
    if test_ollama_python_lib():
        success_count += 1
    
    # Test 4: Génération de texte
    if test_model_generation(llava_models[0]):
        success_count += 1
    
    # Test 5: Traitement d'images
    if test_image_processing(llava_models[0]):
        success_count += 1
    
    # Ressources système (informatif)
    check_system_resources()
    
    # Résultats
    print_section("RÉSULTATS FINAUX")
    
    success_rate = (success_count / total_tests) * 100
    
    if success_count == total_tests:
        print_status(f"🎉 TOUS LES TESTS RÉUSSIS! ({success_count}/{total_tests})", "OK")
        print_status("Votre configuration Ollama + LLaVA est parfaite!", "OK")
        print()
        print("🚀 Vous pouvez maintenant lancer votre chatbot:")
        print("   cd backend")
        print("   python app.py")
        
    elif success_count >= 3:
        print_status(f"✅ CONFIGURATION FONCTIONNELLE ({success_count}/{total_tests} - {success_rate:.0f}%)", "OK")
        print_status("Le chatbot devrait fonctionner correctement", "OK")
        
    else:
        print_status(f"❌ PROBLÈMES DÉTECTÉS ({success_count}/{total_tests} - {success_rate:.0f}%)", "ERROR")
        print_status("Le chatbot ne fonctionnera pas correctement", "ERROR")
        fix_common_issues()
    
    return success_count >= 3

if __name__ == "__main__":
    main()
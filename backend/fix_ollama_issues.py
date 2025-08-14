#!/usr/bin/env python3
"""
Script de réparation rapide pour les problèmes Ollama + LLaVA
Place ce fichier dans le dossier backend/ et lance-le
"""

import subprocess
import time
import requests
import sys
import os

def print_step(message, status="INFO"):
    symbols = {"INFO": "ℹ️", "OK": "✅", "ERROR": "❌", "WARNING": "⚠️"}
    print(f"{symbols.get(status)} {message}")

def run_command(cmd, description):
    """Exécute une commande et retourne le résultat"""
    print_step(f"{description}...", "INFO")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print_step(f"{description} - Succès", "OK")
            return True, result.stdout
        else:
            print_step(f"{description} - Échec: {result.stderr}", "ERROR")
            return False, result.stderr
    except subprocess.TimeoutExpired:
        print_step(f"{description} - Timeout", "ERROR")
        return False, "Timeout"
    except Exception as e:
        print_step(f"{description} - Erreur: {e}", "ERROR")
        return False, str(e)

def check_ollama_process():
    """Vérifie si Ollama tourne"""
    print_step("Vérification du processus Ollama", "INFO")
    
    try:
        result = subprocess.run("pgrep -f ollama", shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            pids = result.stdout.strip().split('\n')
            print_step(f"Processus Ollama trouvés: {len(pids)} (PIDs: {', '.join(pids)})", "OK")
            return True
        else:
            print_step("Aucun processus Ollama trouvé", "WARNING")
            return False
    except Exception as e:
        print_step(f"Erreur vérification processus: {e}", "ERROR")
        return False

def kill_ollama():
    """Tue tous les processus Ollama"""
    print_step("Arrêt de tous les processus Ollama", "INFO")
    
    commands = [
        "pkill -f ollama",
        "killall ollama 2>/dev/null || true"
    ]
    
    for cmd in commands:
        subprocess.run(cmd, shell=True, capture_output=True)
    
    time.sleep(2)
    
    # Vérifier si les processus sont bien arrêtés
    if not check_ollama_process():
        print_step("Processus Ollama arrêtés", "OK")
        return True
    else:
        print_step("Certains processus Ollama persistent", "WARNING")
        return False

def start_ollama():
    """Démarre Ollama en arrière-plan"""
    print_step("Démarrage d'Ollama", "INFO")
    
    try:
        # Démarrer Ollama en arrière-plan
        subprocess.Popen(
            "ollama serve",
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        # Attendre un peu pour que le service démarre
        print_step("Attente du démarrage du service (10s)", "INFO")
        time.sleep(10)
        
        # Vérifier que le service répond
        for attempt in range(5):
            try:
                response = requests.get("http://localhost:11434/api/version", timeout=3)
                if response.status_code == 200:
                    version_info = response.json()
                    print_step(f"Ollama démarré - Version: {version_info.get('version', 'N/A')}", "OK")
                    return True
            except:
                if attempt < 4:
                    print_step(f"Tentative {attempt + 1}/5 - Service pas encore prêt", "INFO")
                    time.sleep(3)
                else:
                    print_step("Service Ollama ne répond pas après 25s", "ERROR")
                    return False
        
        return False
        
    except Exception as e:
        print_step(f"Erreur démarrage Ollama: {e}", "ERROR")
        return False

def check_llava_model():
    """Vérifie si le modèle LLaVA est installé"""
    print_step("Vérification du modèle LLaVA", "INFO")
    
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=10)
        if response.status_code == 200:
            data = response.json()
            models = data.get('models', [])
            model_names = [m['name'] for m in models]
            
            llava_models = [name for name in model_names if 'llava' in name.lower()]
            
            if llava_models:
                print_step(f"Modèles LLaVA trouvés: {llava_models}", "OK")
                return True, llava_models
            else:
                print_step("Aucun modèle LLaVA trouvé", "ERROR")
                return False, []
        else:
            print_step(f"Erreur API tags: HTTP {response.status_code}", "ERROR")
            return False, []
            
    except Exception as e:
        print_step(f"Erreur vérification modèles: {e}", "ERROR")
        return False, []

def install_llava():
    """Installe le modèle LLaVA"""
    print_step("Installation du modèle LLaVA (cela peut prendre plusieurs minutes)", "INFO")
    
    models_to_try = [
        "llava:latest",
        "llava:7b",
        "llava:13b"
    ]
    
    for model in models_to_try:
        print_step(f"Tentative d'installation: {model}", "INFO")
        success, output = run_command(f"ollama pull {model}", f"Installation {model}")
        
        if success:
            print_step(f"Modèle {model} installé avec succès", "OK")
            return True
        else:
            print_step(f"Échec installation {model}: {output[:100]}", "WARNING")
    
    print_step("Échec de l'installation de tous les modèles LLaVA", "ERROR")
    return False

def test_llava_generation():
    """Test rapide de génération avec LLaVA"""
    print_step("Test de génération avec LLaVA", "INFO")
    
    try:
        # Récupérer le premier modèle LLaVA disponible
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        data = response.json()
        models = [m['name'] for m in data.get('models', []) if 'llava' in m['name'].lower()]
        
        if not models:
            print_step("Aucun modèle LLaVA pour le test", "ERROR")
            return False
        
        model_name = models[0]
        print_step(f"Test avec le modèle: {model_name}", "INFO")
        
        payload = {
            "model": model_name,
            "messages": [{"role": "user", "content": "Say 'LLAVA_TEST_SUCCESS' to confirm you work"}],
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
            print_step(f"Réponse du modèle: '{content[:50]}'", "OK")
            
            if 'success' in content.lower() or 'test' in content.lower():
                print_step("Test de génération réussi!", "OK")
                return True
            else:
                print_step("Génération OK mais réponse inattendue", "WARNING")
                return True
        else:
            print_step(f"Erreur génération: HTTP {response.status_code}", "ERROR")
            return False
            
    except Exception as e:
        print_step(f"Erreur test génération: {e}", "ERROR")
        return False

def main():
    print("🔧 SCRIPT DE RÉPARATION OLLAMA + LLAVA")
    print("="*50)
    
    # Étape 1: Arrêter Ollama proprement
    print("\n1️⃣ ARRÊT D'OLLAMA")
    kill_ollama()
    
    # Étape 2: Redémarrer Ollama
    print("\n2️⃣ REDÉMARRAGE D'OLLAMA")
    if not start_ollama():
        print_step("Impossible de démarrer Ollama", "ERROR")
        print("💡 Solutions manuelles:")
        print("   - Vérifiez l'installation: ollama --version")
        print("   - Redémarrez manuellement: ollama serve")
        sys.exit(1)
    
    # Étape 3: Vérifier les modèles LLaVA
    print("\n3️⃣ VÉRIFICATION MODÈLES LLAVA")
    has_llava, llava_models = check_llava_model()
    
    if not has_llava:
        print("\n4️⃣ INSTALLATION LLAVA")
        if not install_llava():
            print_step("Installation LLaVA échouée", "ERROR")
            print("💡 Essayez manuellement: ollama pull llava:latest")
            sys.exit(1)
    else:
        print_step("Modèles LLaVA déjà présents", "OK")
    
    # Étape 4: Test final
    print("\n5️⃣ TEST FINAL")
    if test_llava_generation():
        print("\n" + "="*50)
        print("🎉 RÉPARATION TERMINÉE AVEC SUCCÈS!")
        print("✅ Ollama + LLaVA sont maintenant opérationnels")
        print("\n🚀 Vous pouvez maintenant lancer votre chatbot:")
        print("   python app.py")
        print("="*50)
    else:
        print("\n" + "="*50)
        print("❌ PROBLÈME PERSISTANT")
        print("💡 Actions supplémentaires recommandées:")
        print("   1. Redémarrez votre système")
        print("   2. Réinstallez Ollama complètement")
        print("   3. Vérifiez les logs: journalctl -f -u ollama")
        print("="*50)

if __name__ == "__main__":
    main()
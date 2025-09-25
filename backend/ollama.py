

import subprocess
import time
import requests
import sys
import os
import argparse
import json
from pathlib import Path

class OllamaManager:
    def __init__(self):
        self.success_count = 0
        self.total_tests = 5
        self.llava_models = []
        
    def print_section(self, title):
        """Affiche une section"""
        print(f"\n{'='*60}")
        print(f"  {title}")
        print(f"{'='*60}")

    def print_status(self, message, status="INFO"):
        """Affiche un status avec icône"""
        symbols = {
            "INFO": "ℹ️", "OK": "✅", "ERROR": "❌", 
            "WARNING": "⚠️", "FIX": "🔧", "PROGRESS": "⏳"
        }
        print(f"{symbols.get(status, 'ℹ️')} {message}")

    def run_command(self, cmd, description, timeout=30):
        """Exécute une commande et retourne le résultat"""
        self.print_status(f"{description}...", "PROGRESS")
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, 
                text=True, timeout=timeout
            )
            if result.returncode == 0:
                self.print_status(f"{description} - Succès", "OK")
                return True, result.stdout
            else:
                self.print_status(f"{description} - Échec: {result.stderr[:100]}", "ERROR")
                return False, result.stderr
        except subprocess.TimeoutExpired:
            self.print_status(f"{description} - Timeout ({timeout}s)", "ERROR")
            return False, "Timeout"
        except Exception as e:
            self.print_status(f"{description} - Erreur: {e}", "ERROR")
            return False, str(e)

    def check_ollama_process(self):
        """Vérifie si Ollama tourne"""
        self.print_status("Vérification du processus Ollama", "INFO")
        
        try:
            result = subprocess.run(
                "pgrep -f ollama", shell=True, 
                capture_output=True, text=True
            )
            if result.returncode == 0:
                pids = result.stdout.strip().split('\n')
                self.print_status(f"Processus Ollama trouvés: {len(pids)}", "OK")
                return True
            else:
                self.print_status("Aucun processus Ollama trouvé", "WARNING")
                return False
        except Exception as e:
            self.print_status(f"Erreur vérification processus: {e}", "ERROR")
            return False

    def check_ollama_service(self):
        """Vérifie si le service Ollama répond"""
        self.print_section("VÉRIFICATION SERVICE OLLAMA")
        
        try:
            response = requests.get("http://localhost:11434/api/version", timeout=5)
            if response.status_code == 200:
                version_info = response.json()
                self.print_status(f"Service Ollama actif - Version: {version_info.get('version', 'N/A')}", "OK")
                self.success_count += 1
                return True
            else:
                self.print_status(f"Service répond mais erreur HTTP {response.status_code}", "ERROR")
                return False
        except requests.exceptions.ConnectionError:
            self.print_status("Service Ollama non accessible sur localhost:11434", "ERROR")
            return False
        except Exception as e:
            self.print_status(f"Erreur vérification service: {e}", "ERROR")
            return False

    def check_ollama_models(self):
        """Vérifie les modèles installés"""
        self.print_section("VÉRIFICATION MODÈLES OLLAMA")
        
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=10)
            
            if response.status_code != 200:
                self.print_status(f"Erreur récupération modèles: HTTP {response.status_code}", "ERROR")
                return False
            
            data = response.json()
            models = data.get('models', [])
            
            if not models:
                self.print_status("Aucun modèle installé", "ERROR")
                return False
            
            self.print_status(f"Modèles installés: {len(models)}", "OK")
            
            self.llava_models = []
            for model in models:
                name = model.get('name', 'N/A')
                size = model.get('size', 0)
                size_gb = size / (1024**3) if size else 0
                
                print(f"   - {name} ({size_gb:.1f}GB)")
                
                if 'llava' in name.lower():
                    self.llava_models.append(name)
            
            if self.llava_models:
                self.print_status(f"Modèles LLaVA trouvés: {self.llava_models}", "OK")
                self.success_count += 1
                return True
            else:
                self.print_status("Aucun modèle LLaVA trouvé!", "ERROR")
                return False
                
        except Exception as e:
            self.print_status(f"Erreur vérification modèles: {e}", "ERROR")
            return False

    def test_model_generation(self, model_name):
        """Test de génération avec un modèle"""
        self.print_section(f"TEST GÉNÉRATION - {model_name}")
        
        try:
            self.print_status("Test de génération simple...", "PROGRESS")
            
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
                self.print_status(f"Réponse: '{content[:80]}'", "OK")
                
                if 'success' in content.lower() or 'test' in content.lower():
                    self.print_status("Test de génération réussi!", "OK")
                    self.success_count += 1
                    return True
                else:
                    self.print_status("Génération fonctionne mais réponse inattendue", "WARNING")
                    self.success_count += 1
                    return True
            else:
                self.print_status(f"Erreur génération: HTTP {response.status_code}", "ERROR")
                return False
                
        except requests.exceptions.Timeout:
            self.print_status("Timeout lors de la génération (>30s)", "ERROR")
            return False
        except Exception as e:
            self.print_status(f"Erreur test génération: {e}", "ERROR")
            return False

    def test_image_processing(self, model_name):
        """Test du traitement d'images"""
        self.print_section(f"TEST TRAITEMENT IMAGE - {model_name}")
        
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
                self.print_status(f"Analyse image: '{content[:60]}'", "OK")
                self.success_count += 1
                return True
            else:
                self.print_status(f"Erreur traitement image: HTTP {response.status_code}", "ERROR")
                return False
                
        except Exception as e:
            self.print_status(f"Erreur test image: {e}", "ERROR")
            return False

    def check_system_resources(self):
        """Vérifie les ressources système"""
        self.print_section("VÉRIFICATION RESSOURCES SYSTÈME")
        
        try:
            import psutil
            
            # RAM
            memory = psutil.virtual_memory()
            memory_gb = memory.total / (1024**3)
            memory_available = memory.available / (1024**3)
            
            self.print_status(f"RAM totale: {memory_gb:.1f}GB", "INFO")
            self.print_status(f"RAM disponible: {memory_available:.1f}GB", "INFO")
            
            if memory_available < 4:
                self.print_status("RAM faible - LLaVA peut être lent", "WARNING")
            else:
                self.print_status("RAM suffisante", "OK")
                self.success_count += 1
            
            # Processus Ollama
            ollama_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info']):
                if 'ollama' in proc.info['name'].lower():
                    ollama_processes.append(proc.info)
            
            if ollama_processes:
                self.print_status(f"Processus Ollama actifs: {len(ollama_processes)}", "OK")
                for proc in ollama_processes:
                    memory_mb = proc['memory_info'].rss / (1024*1024)
                    print(f"   - PID {proc['pid']}: {proc['name']} ({memory_mb:.0f}MB)")
            else:
                self.print_status("Aucun processus Ollama détecté", "WARNING")
                
        except ImportError:
            self.print_status("Module psutil non disponible - ignoré", "INFO")
        except Exception as e:
            self.print_status(f"Erreur vérification ressources: {e}", "WARNING")

    # ===== FONCTIONS DE RÉPARATION =====

    def kill_ollama(self):
        """Tue tous les processus Ollama"""
        self.print_status("Arrêt de tous les processus Ollama", "FIX")
        
        commands = [
            "pkill -f ollama",
            "killall ollama 2>/dev/null || true"
        ]
        
        for cmd in commands:
            subprocess.run(cmd, shell=True, capture_output=True)
        
        time.sleep(2)
        
        # Vérifier si les processus sont bien arrêtés
        if not self.check_ollama_process():
            self.print_status("Processus Ollama arrêtés", "OK")
            return True
        else:
            self.print_status("Certains processus Ollama persistent", "WARNING")
            return False

    def start_ollama(self):
        """Démarre Ollama en arrière-plan"""
        self.print_status("Démarrage d'Ollama", "FIX")
        
        try:
            # Démarrer Ollama en arrière-plan
            subprocess.Popen(
                "ollama serve",
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            # Attendre un peu pour que le service démarre
            self.print_status("Attente du démarrage du service (10s)", "PROGRESS")
            time.sleep(10)
            
            # Vérifier que le service répond
            for attempt in range(5):
                try:
                    response = requests.get("http://localhost:11434/api/version", timeout=3)
                    if response.status_code == 200:
                        version_info = response.json()
                        self.print_status(f"Ollama démarré - Version: {version_info.get('version', 'N/A')}", "OK")
                        return True
                except:
                    if attempt < 4:
                        self.print_status(f"Tentative {attempt + 1}/5 - Service pas encore prêt", "PROGRESS")
                        time.sleep(3)
                    else:
                        self.print_status("Service Ollama ne répond pas après 25s", "ERROR")
                        return False
            
            return False
            
        except Exception as e:
            self.print_status(f"Erreur démarrage Ollama: {e}", "ERROR")
            return False

    def install_llava(self):
        """Installe le modèle LLaVA"""
        self.print_status("Installation du modèle LLaVA (cela peut prendre plusieurs minutes)", "FIX")
        
        models_to_try = [
            "llava:latest",
            "llava:7b", 
            "llava:13b"
        ]
        
        for model in models_to_try:
            self.print_status(f"Tentative d'installation: {model}", "PROGRESS")
            success, output = self.run_command(
                f"ollama pull {model}", 
                f"Installation {model}",
                timeout=600  # 10 minutes pour le téléchargement
            )
            
            if success:
                self.print_status(f"Modèle {model} installé avec succès", "OK")
                return True
            else:
                self.print_status(f"Échec installation {model}: {output[:100]}", "WARNING")
        
        self.print_status("Échec de l'installation de tous les modèles LLaVA", "ERROR")
        return False

    def fix_ollama_issues(self):
        """Répare automatiquement les problèmes Ollama détectés"""
        self.print_section("🔧 RÉPARATION AUTOMATIQUE")
        
        # Étape 1: Arrêter Ollama proprement
        self.print_status("1️⃣ ARRÊT D'OLLAMA", "FIX")
        self.kill_ollama()
        
        # Étape 2: Redémarrer Ollama
        self.print_status("2️⃣ REDÉMARRAGE D'OLLAMA", "FIX")
        if not self.start_ollama():
            self.print_status("Impossible de démarrer Ollama", "ERROR")
            self.print_status("Solutions manuelles:", "INFO")
            print("   - Vérifiez l'installation: ollama --version")
            print("   - Redémarrez manuellement: ollama serve")
            return False
        
        # Étape 3: Vérifier les modèles LLaVA
        self.print_status("3️⃣ VÉRIFICATION MODÈLES LLAVA", "FIX")
        if not self.check_ollama_models() or not self.llava_models:
            self.print_status("4️⃣ INSTALLATION LLAVA", "FIX")
            if not self.install_llava():
                self.print_status("Installation LLaVA échouée", "ERROR")
                print("💡 Essayez manuellement: ollama pull llava:latest")
                return False
        
        # Étape 4: Test final
        self.print_status("5️⃣ TEST FINAL", "FIX")
        # Recharger les modèles après installation
        if self.check_ollama_models() and self.llava_models:
            if self.test_model_generation(self.llava_models[0]):
                self.print_status("🎉 RÉPARATION TERMINÉE AVEC SUCCÈS!", "OK")
                return True
        
        self.print_status("❌ PROBLÈME PERSISTANT", "ERROR")
        return False

    def run_diagnostic(self):
        """Lance le diagnostic complet"""
        self.print_section("🔧 DIAGNOSTIC COMPLET OLLAMA + LLAVA")
        
        self.success_count = 0
        
        # Test 1: Service Ollama
        service_ok = self.check_ollama_service()
        
        if not service_ok:
            return False
        
        # Test 2: Modèles disponibles
        models_ok = self.check_ollama_models()
        
        if not models_ok or not self.llava_models:
            return False
        
        # Test 3: Génération de texte
        generation_ok = self.test_model_generation(self.llava_models[0])
        
        # Test 4: Traitement d'images
        image_ok = self.test_image_processing(self.llava_models[0])
        
        # Test 5: Ressources système (informatif)
        self.check_system_resources()
        
        return self.success_count >= 3

    def print_results(self, diagnostic_success):
        """Affiche les résultats finaux"""
        self.print_section("RÉSULTATS FINAUX")
        
        success_rate = (self.success_count / self.total_tests) * 100
        
        if self.success_count == self.total_tests:
            self.print_status(f"🎉 TOUS LES TESTS RÉUSSIS! ({self.success_count}/{self.total_tests})", "OK")
            self.print_status("Votre configuration Ollama + LLaVA est parfaite!", "OK")
            print("\n🚀 Vous pouvez maintenant lancer votre chatbot:")
            print("   cd backend")
            print("   python app.py")
            
        elif self.success_count >= 3:
            self.print_status(f"✅ CONFIGURATION FONCTIONNELLE ({self.success_count}/{self.total_tests} - {success_rate:.0f}%)", "OK")
            self.print_status("Le chatbot devrait fonctionner correctement", "OK")
            
        else:
            self.print_status(f"❌ PROBLÈMES DÉTECTÉS ({self.success_count}/{self.total_tests} - {success_rate:.0f}%)", "ERROR")
            self.print_status("Le chatbot ne fonctionnera pas correctement", "ERROR")
            self.show_manual_solutions()

    def show_manual_solutions(self):
        self.print_section("SOLUTIONS RECOMMANDÉES")
        
        self.print_status("Si les problèmes persistent, essayez dans cet ordre:", "INFO")
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
    parser = argparse.ArgumentParser(
        description='Diagnostic et réparation Ollama + LLaVA',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  python ollama.py              # Diagnostic seul
  python ollama.py --fix        # Diagnostic + Réparation si problèmes
  python ollama.py --force-fix  # Force la réparation
        """
    )
    
    parser.add_argument(
        '--fix', 
        action='store_true',
        help='Répare automatiquement les problèmes détectés'
    )
    
    parser.add_argument(
        '--force-fix',
        action='store_true', 
        help='Force la réparation même sans problèmes détectés'
    )
    
    args = parser.parse_args()
    
    manager = OllamaManager()
    
    # Mode réparation forcée
    if args.force_fix:
        print("🔧 MODE RÉPARATION FORCÉE")
        success = manager.fix_ollama_issues()
        if success:
            print("\n✅ Réparation terminée - relancement du diagnostic")
            manager.run_diagnostic()
            manager.print_results(True)
        return
    
    # Diagnostic standard
    print("🔍 MODE DIAGNOSTIC")
    diagnostic_success = manager.run_diagnostic()
    
    # Réparation automatique si demandée et problèmes détectés
    if args.fix and not diagnostic_success:
        print("\n🔧 PROBLÈMES DÉTECTÉS - LANCEMENT RÉPARATION AUTOMATIQUE")
        if manager.fix_ollama_issues():
            print("\n✅ Réparation terminée - nouveau diagnostic")
            diagnostic_success = manager.run_diagnostic()
    
    manager.print_results(diagnostic_success)


if __name__ == "__main__":
    main()
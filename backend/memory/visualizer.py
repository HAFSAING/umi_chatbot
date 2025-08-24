import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
import json
from typing import Dict, List, Any

class MemoryVisualizer:
    """Visualiseur pour analyser et afficher les données de mémoire du chatbot"""
    
    def __init__(self, memory_dir="data/memory"):
        self.memory_dir = Path(memory_dir)
        self.db_path = self.memory_dir / "chatbot_memory.db"
        
        if not self.db_path.exists():
            print(f"⚠️ Base de données non trouvée: {self.db_path}")

    def show_conversations(self, limit=10, session_id=None):
        """Affiche les conversations récentes dans un format lisible"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if session_id:
                    cursor.execute('''
                        SELECT id, timestamp, user_message, bot_response, metadata, created_at
                        FROM conversations 
                        WHERE session_id = ?
                        ORDER BY created_at DESC 
                        LIMIT ?
                    ''', (session_id, limit))
                else:
                    cursor.execute('''
                        SELECT id, timestamp, user_message, bot_response, metadata, created_at
                        FROM conversations 
                        ORDER BY created_at DESC 
                        LIMIT ?
                    ''', (limit,))
                
                conversations = cursor.fetchall()
                
                if not conversations:
                    print("Aucune conversation trouvée")
                    return
                
                print(f"\n{'='*80}")
                print(f"📚 HISTORIQUE DES CONVERSATIONS (dernières {len(conversations)})")
                print(f"{'='*80}")
                
                for i, conv in enumerate(reversed(conversations), 1):
                    conv_id, timestamp, user_msg, bot_resp, metadata_str, created_at = conv
                    
                    try:
                        metadata = json.loads(metadata_str) if metadata_str else {}
                    except:
                        metadata = {}
                    
                    print(f"\n[{i}] ID: {conv_id} | {created_at}")
                    print(f"👤 Utilisateur: {user_msg}")
                    print(f"🤖 Assistant: {bot_resp[:200]}{'...' if len(bot_resp) > 200 else ''}")
                    
                    # Afficher les métadonnées importantes
                    if metadata:
                        meta_info = []
                        if metadata.get('rag_used'):
                            meta_info.append("RAG utilisé")
                        if metadata.get('has_image'):
                            meta_info.append("Image incluse")
                        if metadata.get('model'):
                            meta_info.append(f"Modèle: {metadata['model']}")
                        
                        if meta_info:
                            print(f"ℹ️  Métadonnées: {' | '.join(meta_info)}")
                    
                    print("-" * 80)
                
        except Exception as e:
            print(f"❌ Erreur affichage conversations: {e}")

    def show_facts(self, category=None, limit=20):
        """Affiche les faits stockés en mémoire"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if category:
                    cursor.execute('''
                        SELECT key, value, category, confidence, created_at, updated_at
                        FROM facts 
                        WHERE category = ?
                        ORDER BY confidence DESC, updated_at DESC
                        LIMIT ?
                    ''', (category, limit))
                else:
                    cursor.execute('''
                        SELECT key, value, category, confidence, created_at, updated_at
                        FROM facts 
                        ORDER BY confidence DESC, updated_at DESC
                        LIMIT ?
                    ''', (limit,))
                
                facts = cursor.fetchall()
                
                if not facts:
                    print("Aucun fait trouvé")
                    return
                
                print(f"\n{'='*80}")
                print(f"📖 BASE DE CONNAISSANCES ({len(facts)} faits)")
                if category:
                    print(f"Catégorie: {category}")
                print(f"{'='*80}")
                
                # Grouper par catégorie
                facts_by_category = {}
                for fact in facts:
                    key, value, cat, confidence, created, updated = fact
                    if cat not in facts_by_category:
                        facts_by_category[cat] = []
                    facts_by_category[cat].append({
                        'key': key,
                        'value': value,
                        'confidence': confidence,
                        'created_at': created,
                        'updated_at': updated
                    })
                
                for cat, cat_facts in facts_by_category.items():
                    print(f"\n📂 Catégorie: {cat.upper()}")
                    print("-" * 40)
                    
                    for fact in cat_facts:
                        confidence_bar = "★" * int(fact['confidence'] * 5)
                        print(f"🔑 {fact['key']}")
                        print(f"   💡 {fact['value']}")
                        print(f"   📊 Confiance: {confidence_bar} ({fact['confidence']:.1f})")
                        print(f"   📅 Mis à jour: {fact['updated_at']}")
                        print()
                
        except Exception as e:
            print(f"❌ Erreur affichage faits: {e}")

    def show_statistics(self):
        """Affiche des statistiques détaillées sur la mémoire"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                print(f"\n{'='*60}")
                print(f"📊 STATISTIQUES DE LA MÉMOIRE")
                print(f"{'='*60}")
                
                # Statistiques générales
                cursor.execute('SELECT COUNT(*) FROM conversations')
                total_conversations = cursor.fetchone()[0]
                
                cursor.execute('SELECT COUNT(*) FROM facts')
                total_facts = cursor.fetchone()[0]
                
                cursor.execute('SELECT COUNT(*) FROM user_preferences')
                total_preferences = cursor.fetchone()[0]
                
                print(f"💬 Total conversations: {total_conversations}")
                print(f"📚 Total faits: {total_facts}")
                print(f"⚙️ Total préférences: {total_preferences}")
                
                # Statistiques temporelles
                cursor.execute('SELECT MIN(created_at), MAX(created_at) FROM conversations')
                result = cursor.fetchone()
                if result[0] and result[1]:
                    first_conv = result[0]
                    last_conv = result[1]
                    print(f"📅 Première conversation: {first_conv}")
                    print(f"📅 Dernière conversation: {last_conv}")
                
                # Conversations par jour (derniers 7 jours)
                print(f"\n📈 ACTIVITÉ DES 7 DERNIERS JOURS")
                print("-" * 40)
                
                for i in range(7):
                    date = datetime.now() - timedelta(days=i)
                    date_str = date.strftime('%Y-%m-%d')
                    
                    cursor.execute('''
                        SELECT COUNT(*) FROM conversations 
                        WHERE DATE(created_at) = ?
                    ''', (date_str,))
                    
                    count = cursor.fetchone()[0]
                    bar = "█" * (count // 2) if count > 0 else ""
                    print(f"{date_str}: {count:3d} {bar}")
                
                # Métadonnées des conversations
                print(f"\n🏷️ ANALYSE DES MÉTADONNÉES")
                print("-" * 40)
                
                cursor.execute('SELECT metadata FROM conversations WHERE metadata IS NOT NULL')
                metadata_rows = cursor.fetchall()
                
                rag_count = 0
                image_count = 0
                models_used = {}
                
                for row in metadata_rows:
                    try:
                        metadata = json.loads(row[0])
                        if metadata.get('rag_used'):
                            rag_count += 1
                        if metadata.get('has_image'):
                            image_count += 1
                        
                        model = metadata.get('model')
                        if model:
                            models_used[model] = models_used.get(model, 0) + 1
                    except:
                        continue
                
                print(f"📄 Conversations avec RAG: {rag_count}")
                print(f"🖼️ Conversations avec images: {image_count}")
                
                if models_used:
                    print(f"🤖 Modèles utilisés:")
                    for model, count in models_used.items():
                        print(f"   - {model}: {count} fois")
                
                # Taille de la base de données
                if self.db_path.exists():
                    db_size = self.db_path.stat().st_size
                    db_size_mb = db_size / (1024 * 1024)
                    print(f"\n💾 Taille de la base: {db_size_mb:.2f} MB")
                
        except Exception as e:
            print(f"❌ Erreur affichage statistiques: {e}")

    def show_user_preferences(self, user_id="default"):
        """Affiche les préférences utilisateur"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT preference_key, preference_value, created_at
                    FROM user_preferences 
                    WHERE user_id = ?
                    ORDER BY preference_key
                ''', (user_id,))
                
                preferences = cursor.fetchall()
                
                if not preferences:
                    print(f"Aucune préférence trouvée pour l'utilisateur: {user_id}")
                    return
                
                print(f"\n{'='*50}")
                print(f"⚙️ PRÉFÉRENCES UTILISATEUR ({user_id})")
                print(f"{'='*50}")
                
                for pref_key, pref_value, created_at in preferences:
                    print(f"🔧 {pref_key}: {pref_value}")
                    print(f"   📅 Créé le: {created_at}")
                    print()
                
        except Exception as e:
            print(f"❌ Erreur affichage préférences: {e}")

    def search_conversations(self, search_term, limit=10):
        """Recherche dans les conversations"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT id, timestamp, user_message, bot_response, created_at
                    FROM conversations 
                    WHERE user_message LIKE ? OR bot_response LIKE ?
                    ORDER BY created_at DESC 
                    LIMIT ?
                ''', (f'%{search_term}%', f'%{search_term}%', limit))
                
                results = cursor.fetchall()
                
                if not results:
                    print(f"Aucun résultat trouvé pour: '{search_term}'")
                    return
                
                print(f"\n{'='*60}")
                print(f"🔍 RÉSULTATS DE RECHERCHE: '{search_term}'")
                print(f"{'='*60}")
                
                for i, (conv_id, timestamp, user_msg, bot_resp, created_at) in enumerate(results, 1):
                    print(f"\n[{i}] ID: {conv_id} | {created_at}")
                    
                    # Surligner le terme recherché (simple)
                    highlighted_user = user_msg.replace(search_term, f"**{search_term}**")
                    highlighted_bot = bot_resp.replace(search_term, f"**{search_term}**")
                    
                    print(f"👤 {highlighted_user}")
                    print(f"🤖 {highlighted_bot[:200]}{'...' if len(highlighted_bot) > 200 else ''}")
                    print("-" * 60)
                
        except Exception as e:
            print(f"❌ Erreur recherche: {e}")

    def generate_memory_report(self, output_file=None):
        """Génère un rapport complet de la mémoire"""
        try:
            if not output_file:
                output_file = self.memory_dir / f"memory_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            
            with open(output_file, 'w', encoding='utf-8') as f:
                # Rediriger la sortie vers le fichier
                import sys
                original_stdout = sys.stdout
                sys.stdout = f
                
                print(f"RAPPORT DE MÉMOIRE DU CHATBOT")
                print(f"Généré le: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print("=" * 80)
                
                self.show_statistics()
                print("\n" + "=" * 80)
                self.show_conversations(limit=20)
                print("\n" + "=" * 80)
                self.show_facts()
                print("\n" + "=" * 80)
                self.show_user_preferences()
                
                # Restaurer la sortie standard
                sys.stdout = original_stdout
            
            print(f"📄 Rapport généré: {output_file}")
            return str(output_file)
            
        except Exception as e:
            print(f"❌ Erreur génération rapport: {e}")
            return None
try:
    from langchain_chroma import Chroma
    from langchain_ollama import OllamaEmbeddings
except ImportError:
    # Fallback aux anciens packages si les nouveaux ne sont pas installés
    try:
        from langchain_community.vectorstores import Chroma
        from langchain_community.embeddings import OllamaEmbeddings
    except ImportError:
        print("❌ Impossible d'importer les modules Chroma/Embeddings")
        raise

from .loader import DocumentLoader
import os
import logging

logger = logging.getLogger(__name__)

class VectorDB:
    def __init__(self):
        try:
            # Utiliser un modèle d'embedding plus léger et plus fiable
            self.embeddings = OllamaEmbeddings(
                model="nomic-embed-text",
                base_url="http://localhost:11434"  # URL explicite
            )
            
            # Créer le dossier de persistance si nécessaire
            persist_dir = "data/vector_db"
            os.makedirs(persist_dir, exist_ok=True)
            
            self.vectorstore = Chroma(
                persist_directory=persist_dir,
                embedding_function=self.embeddings
            )
            
            print("✅ VectorDB initialisé avec succès")
            
        except Exception as e:
            print(f"❌ Erreur initialisation VectorDB: {e}")
            raise

    def initialize(self):
        """Initialise la base vectorielle avec les documents"""
        try:
            loader = DocumentLoader()
            documents, loaded_files, failed_files = loader.load_documents()
            
            if documents:
                print(f"📚 Ajout de {len(documents)} documents à la base vectorielle...")
                
                # Ajouter les documents par petits lots pour éviter les timeouts
                batch_size = 10
                for i in range(0, len(documents), batch_size):
                    batch = documents[i:i+batch_size]
                    try:
                        self.vectorstore.add_documents(batch)
                        print(f"✅ Lot {i//batch_size + 1}/{(len(documents)-1)//batch_size + 1} ajouté")
                    except Exception as e:
                        print(f"⚠️ Erreur ajout lot {i//batch_size + 1}: {e}")
                        continue
                
                # La persistance est automatique avec les nouvelles versions
                try:
                    self.vectorstore.persist()
                    print("✅ Base vectorielle persistée")
                except AttributeError:
                    # Les nouvelles versions de Chroma persistent automatiquement
                    print("✅ Base vectorielle sauvegardée automatiquement")
                    
                print(f"✅ {len(loaded_files)} fichiers chargés avec succès")
                if failed_files:
                    print(f"⚠️ {len(failed_files)} fichiers échoués: {failed_files}")
                    
            else:
                print("⚠️ Aucun document trouvé à indexer")
                
        except Exception as e:
            print(f"❌ Erreur lors de l'initialisation: {e}")
            raise

    def initialize_fresh(self):
        """Réinitialise complètement la base vectorielle"""
        try:
            import shutil
            
            # Supprimer l'ancienne base si elle existe
            persist_dir = "data/vector_db"
            if os.path.exists(persist_dir):
                shutil.rmtree(persist_dir)
                print("🗑️ Ancienne base vectorielle supprimée")
            
            # Créer une nouvelle base
            os.makedirs(persist_dir, exist_ok=True)
            self.vectorstore = Chroma(
                persist_directory=persist_dir,
                embedding_function=self.embeddings
            )
            
            print("🆕 Nouvelle base vectorielle créée")
            
        except Exception as e:
            print(f"❌ Erreur réinitialisation: {e}")
            raise

    def add_documents(self, documents):
        """Ajoute des documents à la base vectorielle"""
        try:
            if not documents:
                print("⚠️ Aucun document à ajouter")
                return
                
            print(f"📄 Ajout de {len(documents)} documents...")
            
            # Traitement par lots pour éviter les surcharges
            batch_size = 5
            added_count = 0
            
            for i in range(0, len(documents), batch_size):
                batch = documents[i:i+batch_size]
                try:
                    self.vectorstore.add_documents(batch)
                    added_count += len(batch)
                    print(f"✅ {added_count}/{len(documents)} documents ajoutés")
                except Exception as e:
                    print(f"⚠️ Erreur ajout lot: {e}")
                    continue
            
            print(f"✅ {added_count} documents ajoutés à la base")
            
        except Exception as e:
            print(f"❌ Erreur ajout documents: {e}")
            raise

    def search(self, query, k=3):
        """Recherche dans la base vectorielle"""
        try:
            if not query.strip():
                return []
                
            results = self.vectorstore.similarity_search(query, k=k)
            print(f"🔍 Recherche '{query[:30]}...': {len(results)} résultats")
            
            return results
            
        except Exception as e:
            print(f"❌ Erreur recherche: {e}")
            return []

    def get_stats(self):
        """Retourne des statistiques sur la base vectorielle"""
        try:
            # Essayer de compter les documents (méthode approximative)
            test_search = self.vectorstore.similarity_search("", k=1000)
            doc_count = len(test_search)
            
            return {
                'document_count': doc_count,
                'status': 'operational'
            }
        except Exception as e:
            return {
                'document_count': 0,
                'status': f'error: {e}'
            }
from langchain_community.document_loaders import (
    PDFPlumberLoader, 
    Docx2txtLoader, 
    TextLoader,
    CSVLoader,
    UnstructuredPowerPointLoader,
    UnstructuredExcelLoader
)
from langchain_text_splitters import RecursiveCharacterTextSplitter
import os
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class DocumentLoader:
    """Chargeur de documents multi-formats"""
    
    def __init__(self, data_dir="data/documents"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", " ", ""]
        )
        
        # Configuration des types de fichiers supportés
        self.supported_extensions = {
            '.pdf': self._load_pdf,
            '.docx': self._load_docx,
            '.doc': self._load_docx,
            '.txt': self._load_txt,
            '.md': self._load_txt,
            '.csv': self._load_csv,
            '.pptx': self._load_pptx,
            '.ppt': self._load_pptx,
            '.xlsx': self._load_excel,
            '.xls': self._load_excel
        }

    def _load_pdf(self, file_path):
        """Charge un fichier PDF"""
        try:
            loader = PDFPlumberLoader(str(file_path))
            return loader.load()
        except Exception as e:
            logger.error(f"Erreur lors du chargement PDF {file_path}: {e}")
            return []

    def _load_docx(self, file_path):
        """Charge un fichier Word (DOCX/DOC)"""
        try:
            loader = Docx2txtLoader(str(file_path))
            return loader.load()
        except Exception as e:
            logger.error(f"Erreur lors du chargement DOCX {file_path}: {e}")
            return []

    def _load_txt(self, file_path):
        """Charge un fichier texte (TXT/MD)"""
        try:
            loader = TextLoader(str(file_path), encoding='utf-8')
            return loader.load()
        except UnicodeDecodeError:
            try:
                loader = TextLoader(str(file_path), encoding='latin-1')
                return loader.load()
            except Exception as e:
                logger.error(f"Erreur lors du chargement TXT {file_path}: {e}")
                return []
        except Exception as e:
            logger.error(f"Erreur lors du chargement TXT {file_path}: {e}")
            return []

    def _load_csv(self, file_path):
        """Charge un fichier CSV"""
        try:
            loader = CSVLoader(str(file_path))
            return loader.load()
        except Exception as e:
            logger.error(f"Erreur lors du chargement CSV {file_path}: {e}")
            return []

    def _load_pptx(self, file_path):
        """Charge un fichier PowerPoint (PPTX/PPT)"""
        try:
            loader = UnstructuredPowerPointLoader(str(file_path))
            return loader.load()
        except Exception as e:
            logger.error(f"Erreur lors du chargement PPTX {file_path}: {e}")
            return []

    def _load_excel(self, file_path):
        """Charge un fichier Excel (XLSX/XLS)"""
        try:
            loader = UnstructuredExcelLoader(str(file_path))
            return loader.load()
        except Exception as e:
            logger.error(f"Erreur lors du chargement Excel {file_path}: {e}")
            return []

    def get_supported_extensions(self):
        """Retourne la liste des extensions supportées"""
        return list(self.supported_extensions.keys())

    def is_supported_file(self, filename):
        """Vérifie si un fichier est supporté"""
        return Path(filename).suffix.lower() in self.supported_extensions

    def scan_documents(self):
        """Scanne le répertoire des documents et retourne les informations"""
        documents_info = {
            'total_files': 0,
            'supported_files': 0,
            'unsupported_files': 0,
            'files_by_type': {},
            'file_list': []
        }
        
        if not self.data_dir.exists():
            return documents_info
            
        for file_path in self.data_dir.rglob('*'):
            if file_path.is_file():
                documents_info['total_files'] += 1
                extension = file_path.suffix.lower()
                
                file_info = {
                    'name': file_path.name,
                    'path': str(file_path),
                    'size': file_path.stat().st_size,
                    'extension': extension,
                    'supported': self.is_supported_file(file_path.name)
                }
                
                documents_info['file_list'].append(file_info)
                
                if file_info['supported']:
                    documents_info['supported_files'] += 1
                    documents_info['files_by_type'][extension] = documents_info['files_by_type'].get(extension, 0) + 1
                else:
                    documents_info['unsupported_files'] += 1
        
        return documents_info

    def load_documents(self):
        """Charge tous les documents supportés du répertoire"""
        all_documents = []
        loaded_files = []
        failed_files = []
        
        print(f"📚 Scan du répertoire: {self.data_dir}")
        
        for file_path in self.data_dir.rglob('*'):
            if file_path.is_file() and self.is_supported_file(file_path.name):
                extension = file_path.suffix.lower()
                print(f"📄 Chargement: {file_path.name} ({extension})")
                
                try:
                    loader_func = self.supported_extensions[extension]
                    documents = loader_func(file_path)
                    
                    if documents:
                        # Ajouter des métadonnées aux documents
                        for doc in documents:
                            doc.metadata.update({
                                'source_file': file_path.name,
                                'file_type': extension,
                                'file_size': file_path.stat().st_size
                            })
                        
                        split_docs = self.text_splitter.split_documents(documents)
                        all_documents.extend(split_docs)
                        loaded_files.append({
                            'file': file_path.name,
                            'type': extension,
                            'chunks': len(split_docs)
                        })
                        print(f"✅ {file_path.name}: {len(split_docs)} chunks créés")
                    else:
                        failed_files.append(file_path.name)
                        print(f"⚠️ {file_path.name}: Aucun contenu extrait")
                        
                except Exception as e:
                    failed_files.append(file_path.name)
                    logger.error(f"❌ Erreur {file_path.name}: {e}")
        
        print(f"📊 Résumé du chargement:")
        print(f"   - Fichiers chargés: {len(loaded_files)}")
        print(f"   - Fichiers échoués: {len(failed_files)}")
        print(f"   - Total chunks: {len(all_documents)}")
        
        return all_documents, loaded_files, failed_files

# Garde la classe PDFLoader pour la compatibilité
class PDFLoader(DocumentLoader):
    """Classe de compatibilité - utilise maintenant DocumentLoader"""
    
    def __init__(self, data_dir="data/documents"):
        super().__init__(data_dir)
        print("⚠️ PDFLoader est déprécié, utilisez DocumentLoader à la place")
    
    def load_documents(self):
        """Méthode de compatibilité"""
        documents, _, _ = super().load_documents()
        return documents
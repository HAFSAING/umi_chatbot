# 🤖 UMI RAG Chatbot

Un chatbot intelligent avec RAG (Retrieval-Augmented Generation) qui peut analyser vos documents PDF et traiter des images.

## 🚀 Installation Rapide

### Prérequis
- Python 3.8+
- [Ollama](https://ollama.ai/) installé et démarré

### 1. Cloner et configurer
```bash
cd backend/
python setup.py
```

### 2. Installer les modèles Ollama requis
```bash
ollama pull llama3.2        # Modèle de langage principal
ollama pull llava:latest    # Pour l'analyse d'images
ollama pull nomic-embed-text # Pour les embeddings
```

### 3. Ajouter vos documents PDF
```bash
# Copiez vos fichiers PDF dans le dossier
cp vos-documents.pdf data/documents/
```

### 4. Démarrer le serveur
```bash
python app.py
```

### 5. Ouvrir l'interface
Ouvrez `frontend/chatbot.html` dans votre navigateur

## 📁 Structure du Projet

```
mon-projet-umi/
│
├── backend/
│   ├── app.py              # Serveur Flask principal
│   ├── setup.py            # Script d'installation
│   ├── rag/
│   │   ├── __init__.py
│   │   ├── loader.py       # Chargeur de PDFs
│   │   ├── vector_db.py    # Base vectorielle
│   │   └── retriever.py    # Recherche RAG
│   │
│   └── memory/
│       ├── __init__.py
│       ├── manager.py      # Gestion mémoire
│       └── visualizer.py   # Visualisation
│
├── frontend/
│   └── chatbot.html        # Interface utilisateur
│
├── data/
│   ├── documents/          # 📚 AJOUTEZ VOS PDFs ICI
│   ├── vector_db/          # Base vectorielle (auto-générée)
│   └── memory/             # Historique conversations
│
├── requirements.txt
└── README.md
```

## 🔧 Configuration

### Variables d'environnement
Créez un fichier `.env` (optionnel) :
```env
OLLAMA_HOST=http://localhost:11434
EMBEDDING_MODEL=nomic-embed-text
CHAT_MODEL=llama3.2
VISION_MODEL=llava:latest
```

### Modèles Ollama supportés
- **Langage** : llama3.2, llama3, llama2, mistral
- **Vision** : llava:latest, llava:7b, llava:13b
- **Embeddings** : nomic-embed-text, all-minilm

## 💡 Utilisation

### Chat Textuel avec RAG
1. Ajoutez vos PDFs dans `data/documents/`
2. Le chatbot analysera automatiquement le contenu
3. Posez des questions sur vos documents

### Analyse d'Images
1. Cliquez sur l'icône 📷
2. Sélectionnez une image
3. Le modèle llava analysera l'image

### Commandes Vocales
1. Cliquez sur l'icône 🎤
2. Parlez (nécessite un navigateur compatible)
3. Votre voix sera transcrite

## 🛠️ API Endpoints

```bash
# Statut du système
GET /api/status

# Chat avec RAG
POST /api/chat
{
    "message": "Votre question",
    "image": "base64_image_data"  // optionnel
}

# Réinitialiser RAG
POST /api/initialize-rag
```

## 🔍 Résolution de Problèmes

### ❌ "Ollama non connecté"
```bash
# Vérifier qu'Ollama fonctionne
ollama list

# Redémarrer Ollama
ollama serve
```

### ❌ "Modèle llava non disponible"
```bash
# Installer le modèle
ollama pull llava:latest
```

### ❌ "Aucun contexte RAG trouvé"
```bash
# Vérifier les PDFs
ls data/documents/*.pdf

# Réinitialiser la base vectorielle
curl -X POST http://localhost:5000/api/initialize-rag
```

### ❌ "Failed to fetch"
- Vérifiez que le serveur Flask fonctionne sur le port 5000
- Vérifiez les CORS si vous utilisez un autre domaine

## 🎯 Fonctionnalités

- ✅ **RAG intelligent** : Analyse de documents PDF
- ✅ **Vision** : Analyse d'images avec llava
- ✅ **Mémoire** : Historique des conversations
- ✅ **Interface moderne** : Chat responsive
- ✅ **Voice input** : Reconnaissance vocale
- ✅ **Multi-modal** : Texte + Images
- ✅ **Réponses rapides** : Quick replies contextuelles

## 🚀 Développement

### Ajouter de nouveaux formats
Modifiez `rag/loader.py` pour supporter d'autres formats :
```python
# Exemple pour Word, Excel, etc.
from langchain_community.document_loaders import Docx2txtLoader
```

### Personnaliser le modèle
Changez le modèle dans `app.py` :
```python
model_name = "mistral"  # ou votre modèle préféré
```

### Debug mode
```bash
# Démarrer en mode debug
python app.py --debug
```

## 📊 Monitoring

### Visualiser l'historique
```python
from backend.memory.visualizer import MemoryVisualizer
viz = MemoryVisualizer()
viz.show_conversations(limit=10)
```

### Vérifier la base vectorielle
```python
from backend.rag.vector_db import VectorDB
db = VectorDB()
# Compter les documents indexés
print(f"Documents: {db.vectorstore._collection.count()}")
```


## 📝 Licence

MIT License - voir le fichier LICENSE

## 🆘 Support

- 📧 Email: support@umi.com
- 📱 Issues GitHub
- 💬 Discord Community

---

**Fait avec ❤️ pour UMI**
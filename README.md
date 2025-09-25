# 🤖 UMI Intelligent Chatbot

Un chatbot intelligent multimodal développé pour l'Université Moulay-Ismail  (UMI) avec capacités RAG (Retrieval-Augmented Generation), analyse d'images et système de mémoire persistante.

## 🌟 Fonctionnalités Principales

- **Chat Multimodal** : Texte + Images + Audio
- **RAG Intelligent** : Analyse de documents PDF/Word/Excel/PowerPoint
- **Mémoire Persistante** : Historique des conversations avec base de données SQLite
- **Système de Sessions** : Gestion des utilisateurs et personnalisation
- **Réponses Rapides** : Système de réponses pré-configurées pour les questions fréquentes
- **Interface Moderne** : Design responsive avec thème UMI
- **Support Multilingue** : Français, Anglais, Arabe
- **Diagnostics Avancés** : Outils de monitoring et maintenance

## 🚀 Installation et Configuration

### Prérequis
- Python 3.8+
- [Ollama](https://ollama.ai/) installé
- 4GB+ RAM recommandé

### 1. Cloner et Préparer l'Environnement
```bash
git clone https://github.com/HAFSAING/umi_chatbot.git
cd backend/
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate     # Windows

pip install -r requirements.txt
```

### 2. Installer les Modèles Ollama
```bash
# Démarrer Ollama
ollama serve

# Installer les modèles requis
ollama pull llama3.2        # Modèle principal (2GB)
ollama pull llava:latest    # Vision (4GB) 
ollama pull nomic-embed-text # Embeddings (274MB)
```

### 3. Structure des Dossiers
```bash
mkdir -p data/{documents,vector_db,memory}
```

### 4. Tester la Configuration
```bash
python ollama.py --fix  # Diagnostic et réparation automatique
```

### 5. Démarrer le Serveur
```bash
python app.py
```

### 6. Accéder à l'Interface
Ouvrez votre navigateur : `http://localhost:5000`

## 📁 Architecture du Projet

```
umi-chatbot/
│
├── backend/                 # Serveur Flask
│   ├── app.py              # API principale
│   ├── ollama.py           # Diagnostic Ollama
│   ├── quick_responses.py  # Réponses rapides UMI
│   │
│   ├── rag/                # Système RAG
│   │   ├── loader.py       # Multi-format loader
│   │   ├── vector_db.py    # Base vectorielle Chroma
│   │   └── retriever.py    # Recherche contextuelle
│   │
│   └── memory/             # Système de mémoire
│       ├── manager.py      # Gestionnaire SQLite
│       ├── session.py      # Sessions utilisateur
│       └── visualizer.py   # Analytics
│
├── frontend/               # Interface utilisateur
│   ├── chatbot.html        # Interface principale
│   ├── chatbot.css         # Styles UMI
│   └── chatbot.js          # Logique client
│
├── data/                   # Données persistantes
│   ├── documents/          # 📚 Documents à analyser
│   ├── vector_db/          # Base vectorielle
│   └── memory/             # Historique SQLite
│
└── requirements.txt
```

## 🛠️ Configuration Avancée

### Variables d'Environnement (.env)
```env
OLLAMA_HOST=http://localhost:11434
EMBEDDING_MODEL=nomic-embed-text
CHAT_MODEL=llama3.2
VISION_MODEL=llava:latest
FLASK_PORT=5000
DEBUG=True
```

### Personnalisation UMI
Modifiez `quick_responses.py` pour adapter les réponses aux besoins UMI :
- Contacts et informations
- Programmes d'études
- Procédures d'admission
- Vie étudiante

## 🔧 Utilisation

### 1. Chat Standard
- Posez vos questions en langage naturel
- Le système utilise RAG pour enrichir les réponses avec vos documents

### 2. Analyse de Documents
```bash
# Copiez vos documents
cp documents/*.pdf data/documents/
cp documents/*.docx data/documents/

# Réinitialisez la base vectorielle
curl -X POST http://localhost:5000/api/initialize-rag
```

### 3. Analyse d'Images
- Cliquez sur l'icône 📷
- Uploadez une image
- Le modèle llava analysera le contenu

### 4. Commandes Vocales
- Cliquez sur l'icône 🎤
- Parlez (Chrome/Edge recommandés)
- Transcription automatique

## 🔍 API Reference

### Endpoints Principaux
```bash
# Statut du système
GET /api/status

# Chat avec RAG
POST /api/chat
{
    "message": "Votre question",
    "files": [{"data": "base64...", "type": "image/jpeg"}],
    "session_id": "optional-session-id"
}

# Gestion des sessions
GET /api/session/{session_id}/info
GET /api/session/{session_id}/greeting

# Mémoire et statistiques
GET /api/memory/status
POST /api/memory/clear

# Réinitialisation RAG
POST /api/initialize-rag
```

## 🛠️ Maintenance et Diagnostics

### Script de Diagnostic
```bash
# Diagnostic complet
python ollama.py

# Réparation automatique
python ollama.py --fix

# Réparation forcée
python ollama.py --force-fix
```

### Monitoring de la Mémoire
```python
from memory.visualizer import MemoryVisualizer
viz = MemoryVisualizer()
viz.show_statistics()
viz.show_conversations(limit=20)
```

### Nettoyage Périodique
```python
from memory.manager import MemoryManager
memory = MemoryManager()
memory.clear_old_conversations(days_to_keep=30)
```

## 🔧 Résolution de Problèmes

### Problèmes Courants

**❌ "Failed to fetch"**
```bash
# Vérifier le serveur
curl http://localhost:5000/api/test

# Redémarrer Flask
python app.py
```

**❌ "Ollama non disponible"**
```bash
# Vérifier Ollama
ollama list
ollama serve

# Tester un modèle
ollama run llama3.2 "hello"
```

**❌ "Modèle llava introuvable"**
```bash
# Réinstaller llava
ollama pull llava:latest

# Vérifier l'installation
ollama list | grep llava
```

**❌ "RAG non initialisé"**
```bash
# Vérifier les documents
ls -la data/documents/

# Réinitialiser la base
curl -X POST http://localhost:5000/api/initialize-rag
```

### Logs de Debug
- Backend : Logs dans le terminal Flask
- Frontend : Console du navigateur (F12)
- Mémoire : `data/memory/chatbot_memory.db`

## 📊 Performance et Limitations

### Configuration Recommandée
- **RAM** : 8GB+ (modèles llava consomment 4-6GB)
- **CPU** : 4+ cœurs
- **Stockage** : 10GB+ pour les modèles Ollama

### Limitations
- **Taille des fichiers** : Max 10MB par upload
- **Types supportés** : PDF, DOCX, TXT, CSV, PPTX, XLSX
- **Sessions** : Timeout 2h par défaut
- **Modèles** : Dépendant d'Ollama local

## 🛡️ Sécurité et Confidentialité

- **Données locales** : Tout reste sur votre serveur
- **Pas de cloud** : Aucune donnée envoyée vers l'extérieur
- **Sessions** : IDs uniques, pas de données personnelles
- **Fichiers** : Stockés localement, suppression automatique

## 🎯 Roadmap et Améliorations

### Version Actuelle (1.0)
- ✅ Chat multimodal complet
- ✅ RAG avec multiple formats
- ✅ Mémoire persistante
- ✅ Interface UMI responsive

### Améliorations Futures
- 🔄 Intégration API externes
- 🔄 Support de plus de langues
- 🔄 Analytics avancées
- 🔄 Mode multi-utilisateurs
- 🔄 Export/import de conversations

## 📚 Documentation Technique

### Formats de Documents Supportés
| Format | Extension | Loader | Notes |
|--------|-----------|---------|-------|
| PDF | .pdf | PDFPlumberLoader | Extraction texte + images |
| Word | .docx, .doc | Docx2txtLoader | Texte formaté |
| Excel | .xlsx, .xls | UnstructuredExcelLoader | Tableaux et données |
| PowerPoint | .pptx, .ppt | UnstructuredPowerPointLoader | Contenu des slides |
| Texte | .txt, .md | TextLoader | UTF-8 et Latin-1 |
| CSV | .csv | CSVLoader | Données tabulaires |

### Base de Données SQLite
```sql
-- Structure des tables principales
CREATE TABLE conversations (
    id INTEGER PRIMARY KEY,
    timestamp TEXT,
    user_message TEXT,
    bot_response TEXT,
    session_id TEXT,
    metadata TEXT
);

CREATE TABLE facts (
    id INTEGER PRIMARY KEY,
    key TEXT UNIQUE,
    value TEXT,
    category TEXT,
    confidence REAL
);

CREATE TABLE user_preferences (
    id INTEGER PRIMARY KEY,
    user_id TEXT,
    preference_key TEXT,
    preference_value TEXT
);
```

## 🤝 Contribution

### Structure du Code
- **Backend** : Flask + SQLite + Ollama
- **Frontend** : HTML5 + CSS3 + JavaScript Vanilla
- **RAG** : LangChain + ChromaDB + Ollama Embeddings
- **Style** : CSS personnalisé aux couleurs UMI

### Standards de Code
- Python : PEP8, type hints
- JavaScript : ES6+, commentaires français
- CSS : BEM methodology, responsive design


---

*Chatbot intelligent développé avec les dernières technologies open-source pour UMI* 🎓
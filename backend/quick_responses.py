#!/usr/bin/env python3
"""
Système de réponses rapides pour le chatbot UMI
À ajouter dans votre backend/
"""

import json
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import difflib

class QuickResponseSystem:
    def __init__(self):
        self.responses = self.load_umi_responses()
        self.contact_patterns = self.load_contact_patterns()
        
    def load_umi_responses(self) -> Dict:
        """Base de données des réponses rapides UMI"""
        return {
            "contact": {
                "patterns": [
                    "contact", "téléphone", "phone", "appel", "numéro", 
                    "joindre", "contacter", "coordonnées", "adresse"
                ],
                "response": """📞 **Contacts UMI:**

**Téléphones principaux:**
• 0535 467 306
• 0535 467 307
• 0535 467 305

**Email officiel:**
• presidence@umi.ac.ma

**Adresse:**
Université Mohammed VI Polytechnique - UMI
Campus principal, Benguerir, Maroc

Pour une assistance spécifique, précisez votre demande et nous vous orienterons vers le bon service.""",
                "quick_replies": ["Admissions", "Services académiques", "Support technique", "Autre demande"]
            },
            
            # ADMISSIONS
            "admissions": {
                "patterns": [
                    "admission", "candidature", "inscription", "dossier",
                    "postuler", "concours", "sélection", "bachelor", "master"
                ],
                "response": """🎓 **Admissions UMI:**

**Pour les candidatures:**
• Consultez notre site officiel pour les procédures
• Les dossiers se font en ligne via notre portail
• Respectez les dates limites de candidature

**Contact admissions:**
• 📞 0535 467 306
• 📧 presidence@umi.ac.ma

**Documents généralement requis:**
• Relevés de notes
• Diplômes certifiés
• Lettre de motivation
• CV

Puis-je vous aider avec un programme spécifique?""",
                "quick_replies": ["Programmes Bachelor", "Programmes Master", "Dates limites", "Documents requis"]
            },
            
            "programmes": {
                "patterns": [
                    "programme", "formation", "cursus", "diplôme", "spécialité",
                    "bachelor", "master", "licence", "études", "domaine"
                ],
                "response": """📚 **Programmes UMI:**

L'UMI propose des formations d'excellence dans plusieurs domaines innovants.

**Pour information détaillée:**
• Site web officiel UMI
• Brochures disponibles
• Journées portes ouvertes

**Contact programmes:**
• 📞 0535 467 306/307
• 📧 presidence@umi.ac.ma

Quel domaine d'études vous intéresse le plus?""",
                "quick_replies": ["Ingénierie", "Business", "Sciences", "Technologies", "Autre"]
            },
            
            # FRAIS ET FINANCEMENT
            "frais": {
                "patterns": [
                    "frais", "coût", "prix", "tarif", "finance", "bourse",
                    "paiement", "scolarité", "budget", "aide"
                ],
                "response": """💰 **Frais de scolarité UMI:**

**Pour information sur les frais:**
• Les tarifs varient selon le programme
• Possibilités de bourses et aides
• Plans de paiement disponibles

**Contact financier:**
• 📞 0535 467 305
• 📧 presidence@umi.ac.ma

**Options d'aide:**
• Bourses d'excellence
• Bourses sociales
• Partenariats entreprises

Souhaitez-vous des informations sur un programme particulier?""",
                "quick_replies": ["Bourses disponibles", "Plans de paiement", "Frais par programme", "Aide financière"]
            },
            
            # CAMPUS ET VIE ÉTUDIANTE
            "campus": {
                "patterns": [
                    "campus", "résidence", "logement", "vie étudiante",
                    "activités", "sport", "restaurant", "bibliothèque"
                ],
                "response": """🏫 **Campus UMI:**

**Localisation:** Benguerir, Maroc
**Campus moderne** avec toutes les commodités

**Services campus:**
• Bibliothèque moderne
• Laboratoires équipés
• Espaces de restauration
• Installations sportives
• Résidences étudiantes

**Information campus:**
• 📞 0535 467 306
• 📧 presidence@umi.ac.ma

Que souhaitez-vous savoir sur la vie au campus?""",
                "quick_replies": ["Logement", "Restauration", "Sport", "Bibliothèque", "Transport"]
            },
            
            # CARRIÈRES ET DÉBOUCHÉS
            "carrieres": {
                "patterns": [
                    "carrière", "débouché", "emploi", "job", "stage",
                    "entreprise", "recrutement", "placement", "alumni"
                ],
                "response": """💼 **Carrières et débouchés UMI:**

**Services carrières:**
• Accompagnement personnalisé
• Réseau d'entreprises partenaires
• Stages obligatoires
• Placement post-diplôme

**Partenariats entreprises**
• Stages rémunérés
• Projets industriels
• Recrutement direct

**Contact carrières:**
• 📞 0535 467 307
• 📧 presidence@umi.ac.ma

Quel type d'accompagnement recherchez-vous?""",
                "quick_replies": ["Stages", "Emploi", "Entreprises partenaires", "CV et coaching"]
            },
            
            # INTERNATIONAL
            "international": {
                "patterns": [
                    "international", "étranger", "visa", "échange",
                    "mobilité", "partenariat", "double diplôme"
                ],
                "response": """🌍 **Relations internationales UMI:**

**Pour étudiants internationaux:**
• Procédures de visa
• Accueil et intégration
• Support administratif

**Programmes d'échange:**
• Universités partenaires
• Semestres à l'étranger
• Double diplômes

**Contact international:**
• 📞 0535 467 306
• 📧 presidence@umi.ac.ma

De quel pays venez-vous ou où souhaitez-vous étudier?""",
                "quick_replies": ["Étudiants étrangers", "Études à l'étranger", "Partenariats", "Visa"]
            }
        }
    
    def load_contact_patterns(self) -> List[Dict]:
        """Patterns pour reconnaissance automatique de demandes de contact"""
        return [
            {
                "patterns": ["numéro", "téléphone", "appeler"],
                "response": "📞 Numéros UMI: 0535 467 306 / 0535 467 307 / 0535 467 305"
            },
            {
                "patterns": ["email", "mail", "courriel"],
                "response": "📧 Email officiel: presidence@umi.ac.ma"
            },
            {
                "patterns": ["adresse", "où", "localisation", "situation"],
                "response": "📍 UMI - Université Mohammed VI Polytechnique, Campus Benguerir, Maroc"
            }
        ]
    
    def find_best_match(self, user_message: str) -> Optional[Tuple[str, Dict]]:
        """Trouve la meilleure correspondance pour le message utilisateur"""
        user_message_lower = user_message.lower()
        user_words = re.findall(r'\b\w+\b', user_message_lower)
        
        best_category = None
        best_score = 0
        best_response = None
        
        for category, data in self.responses.items():
            score = 0
            pattern_matches = 0
            
            # Vérifier correspondance avec patterns
            for pattern in data["patterns"]:
                if pattern in user_message_lower:
                    pattern_matches += 1
                    score += 2  # Bonus pour correspondance exacte
                
                # Vérifier similarité
                similarity = difflib.SequenceMatcher(None, pattern, user_message_lower).ratio()
                if similarity > 0.6:
                    score += similarity
            
            # Bonus si plusieurs patterns correspondent
            if pattern_matches > 1:
                score += pattern_matches * 0.5
            
            # Bonus pour longueur appropriée du message
            if 20 <= len(user_message) <= 200:
                score += 0.1
            
            if score > best_score and score >= 1.0:  # Seuil minimum
                best_score = score
                best_category = category
                best_response = data
        
        return (best_category, best_response) if best_response else None
    
    def get_quick_response(self, user_message: str) -> Optional[Dict]:
        """Génère une réponse rapide si possible"""
        if not user_message or len(user_message.strip()) < 3:
            return None
        
        # Rechercher correspondance dans les patterns de contact rapide
        for contact_pattern in self.contact_patterns:
            for pattern in contact_pattern["patterns"]:
                if pattern in user_message.lower():
                    return {
                        "response": contact_pattern["response"],
                        "type": "quick_contact",
                        "confidence": 0.9
                    }
        
        # Rechercher dans la base complète
        match = self.find_best_match(user_message)
        if match:
            category, response_data = match
            return {
                "response": response_data["response"],
                "quick_replies": response_data.get("quick_replies", []),
                "type": "quick_response",
                "category": category,
                "confidence": 0.8
            }
        
        return None
    
    def should_use_quick_response(self, user_message: str, confidence_threshold: float = 0.7) -> bool:
        """Détermine si on doit utiliser une réponse rapide"""
        quick_resp = self.get_quick_response(user_message)
        return quick_resp is not None and quick_resp.get("confidence", 0) >= confidence_threshold

# Fonction d'intégration pour app.py
def integrate_quick_responses(user_message: str) -> Optional[Dict]:
    """
    Fonction à intégrer dans app.py pour vérifier les réponses rapides
    
    Usage dans app.py:
    quick_response = integrate_quick_responses(user_message)
    if quick_response:
        return jsonify({
            'response': quick_response['response'],
            'type': 'quick_response',
            'quick_replies': quick_response.get('quick_replies', []),
            'processing_time': '< 100ms'
        })
    """
    qrs = QuickResponseSystem()
    return qrs.get_quick_response(user_message)

# Exemples d'utilisation
def test_quick_responses():
    """Tests du système de réponses rapides"""
    qrs = QuickResponseSystem()
    
    test_messages = [
        "Comment vous contacter?",
        "Quel est votre numéro de téléphone?",
        "Je veux des infos sur les admissions",
        "Quels sont les frais de scolarité?",
        "Comment postuler pour un master?",
        "Où se trouve le campus?",
        "Programmes disponibles?",
    ]
    
    print("🧪 Tests du système de réponses rapides UMI:")
    print("=" * 50)
    
    for message in test_messages:
        print(f"\n📝 Message: {message}")
        response = qrs.get_quick_response(message)
        
        if response:
            print(f"✅ Réponse rapide trouvée (confiance: {response['confidence']})")
            print(f"📁 Catégorie: {response.get('category', response.get('type'))}")
            print(f"💬 Réponse: {response['response'][:100]}...")
        else:
            print("❌ Pas de réponse rapide - utiliser Ollama")

if __name__ == "__main__":
    test_quick_responses()
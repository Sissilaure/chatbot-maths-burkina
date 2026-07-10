# Curriculum data for Burkina Faso - Mathematics
# Based on official programs from 6ème to Terminale
# Source: Programme officiel du Ministère de l'Éducation du Burkina Faso

CURRICULUM = {
    "6ème": {
        "name": "Sixième",
        "chapters": [
            "Nombres entiers et décimaux",
            "Opérations fondamentales",
            "Fractions",
            "Nombres relatifs",
            "Géométrie: droites et segments",
            "Angles",
            "Triangles et quadrilatères",
            "Symétrie axiale",
            "Périmètres et aires",
            "Proportionnalité"
        ]
    },
    "5ème": {
        "name": "Cinquième",
        "chapters": [
            "Nombres relatifs: opérations",
            "Fractions: opérations",
            "Écritures fractionnaires",
            "Calcul littéral",
            "Équations",
            "Géométrie: parallélisme",
            "Triangles: inégalité triangulaire",
            "Parallélogrammes",
            "Symétrie centrale",
            "Aires et volumes"
        ]
    },
    "4ème": {
        "name": "Quatrième",
        "chapters": [
            "Nombres relatifs: multiplication et division",
            "Fractions: multiplication et division",
            "Puissances",
            "Calcul littéral: développement",
            "Équations et inéquations",
            "Théorème de Pythagore",
            "Théorème de Thalès",
            "Géométrie dans l'espace",
            "Statistiques",
            "Probabilités"
        ]
    },
    "3ème": {
        "name": "Troisième",
        "chapters": [
            "Racines carrées",
            "Identités remarquables",
            "Équations et systèmes",
            "Inéquations",
            "Fonctions linéaires et affines",
            "Trigonométrie",
            "Théorème de Pythagore: réciproque",
            "Théorème de Thalès: réciproque",
            "Géométrie dans l'espace",
            "Statistiques et probabilités",
            "Préparation au BEPC"
        ]
    },
    "2nde": {
        "name": "Seconde",
        "chapters": [
            "Généralités sur les fonctions",
            "Fonctions de référence",
            "Équations et inéquations",
            "Vecteurs",
            "Géométrie analytique",
            "Statistiques descriptives",
            "Probabilités",
            "Algorithmique"
        ]
    },
    "1ère": {
        "name": "Première",
        "chapters": [
            "Second degré",
            "Dérivation",
            "Suites numériques",
            "Trigonométrie",
            "Produit scalaire",
            "Géométrie dans l'espace",
            "Probabilités conditionnelles",
            "Fonction exponentielle"
        ]
    },
    "Tle": {
        "name": "Terminale",
        "chapters": [
            "Fonctions: limites et continuité",
            "Dérivation et applications",
            "Fonction exponentielle et logarithme",
            "Intégration",
            "Suites numériques",
            "Trigonométrie",
            "Géométrie dans l'espace",
            "Probabilités: loi binomiale",
            "Lois de probabilité continues",
            "Préparation au Baccalauréat"
        ]
    }
}

def get_classes():
    """Return list of all classes"""
    return list(CURRICULUM.keys())

def get_class_name(class_code):
    """Return full name of a class"""
    return CURRICULUM.get(class_code, {}).get("name", class_code)

def get_chapters(class_code):
    """Return list of chapters for a given class"""
    return CURRICULUM.get(class_code, {}).get("chapters", [])
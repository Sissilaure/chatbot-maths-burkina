# Curriculum data for Burkina Faso - Mathematics
# Based on official programs from 6ème to Terminale

CURRICULUM = {
    "6ème": {
        "name": "Sixième",
        "chapters": [
            "Nombres entiers et décimaux",
            "Opérations sur les nombres entiers et décimaux",
            "Fractions",
            "Proportionnalité",
            "Géométrie plane : figures de base",
            "Géométrie plane : périmètres et aires",
            "Symétrie axiale",
            "Statistiques : organisation de données",
            "Équations du premier degré à une inconnue"
        ]
    },
    "5ème": {
        "name": "Cinquième",
        "chapters": [
            "Calcul littéral",
            "Nombres relatifs",
            "Opérations sur les nombres relatifs",
            "Équations et inéquations du premier degré",
            "Proportionnalité et pourcentages",
            "Théorème de Pythagore",
            "Géométrie dans l'espace : prismes et cylindres",
            "Statistiques : représentation de données",
            "Angles et parallélisme"
        ]
    },
    "4ème": {
        "name": "Quatrième",
        "chapters": [
            "Calcul littéral : développement et factorisation",
            "Puissances",
            "Racines carrées",
            "Systèmes d'équations",
            "Théorème de Thalès",
            "Trigonométrie dans le triangle rectangle",
            "Géométrie dans l'espace : pyramides et cônes",
            "Statistiques : moyenne et médiane",
            "Fonctions linéaires et affines"
        ]
    },
    "3ème": {
        "name": "Troisième",
        "chapters": [
            "Arithmétique : PGCD et nombres premiers",
            "Calcul littéral : identités remarquables",
            "Équations du second degré",
            "Inéquations",
            "Géométrie plane : triangles et quadrilatères",
            "Géométrie dans l'espace : sphères et boules",
            "Statistiques : étendue et quartiles",
            "Probabilités",
            "Fonctions : variations et courbes",
            "Grandeurs composées"
        ]
    },
    "2nde": {
        "name": "Seconde",
        "chapters": [
            "Ensembles de nombres",
            "Calcul algébrique",
            "Équations et inéquations",
            "Géométrie plane : repérage et vecteurs",
            "Géométrie dans l'espace",
            "Fonctions de référence",
            "Étude de fonctions",
            "Statistiques descriptives",
            "Probabilités conditionnelles",
            "Algorithmique et programmation"
        ]
    },
    "1ère": {
        "name": "Première",
        "chapters": [
            "Suites numériques",
            "Fonctions polynômes et rationnelles",
            "Dérivation",
            "Limites de fonctions",
            "Trigonométrie",
            "Produit scalaire",
            "Géométrie dans l'espace",
            "Probabilités : variables aléatoires",
            "Loi binomiale",
            "Statistiques inférentielles"
        ]
    },
    "Tle": {
        "name": "Terminale",
        "chapters": [
            "Suites numériques avancées",
            "Continuité et dérivabilité",
            "Fonctions exponentielles et logarithmes",
            "Intégration",
            "Nombres complexes",
            "Géométrie dans l'espace avancée",
            "Probabilités : lois continues",
            "Loi normale",
            "Échantillonnage et estimation",
            "Matrices et systèmes linéaires"
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

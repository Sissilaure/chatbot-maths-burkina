#!/usr/bin/env python
"""
Script de lancement du Chatbot Mathématiques Burkina Faso
Lance à la fois le backend FastAPI et sert le frontend statique
"""

import os
import sys
import subprocess
import webbrowser
import time
from pathlib import Path

# Couleurs pour le terminal
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_banner():
    """Affiche la bannière de démarrage."""
    banner = f"""
{Colors.CYAN}{Colors.BOLD}
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║   📐  Chat'Maths Burkina Faso  v1.0                      ║
║   Assistant intelligent en mathématiques                 ║
║   Programme officiel du Burkina Faso (6ème → Terminale)  ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
{Colors.END}
"""
    print(banner)

def check_python():
    """Vérifie la version de Python."""
    print(f"{Colors.BLUE}[INFO] Vérification de Python...{Colors.END}")
    if sys.version_info < (3, 9):
        print(f"{Colors.FAIL}[ERREUR] Python 3.9+ requis. Version actuelle: {sys.version}{Colors.END}")
        sys.exit(1)
    print(f"{Colors.GREEN}[OK] Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}{Colors.END}")

def install_dependencies():
    """Installe les dépendances Python."""
    print(f"\n{Colors.BLUE}[INFO] Installation des dépendances...{Colors.END}")
    req_file = Path(__file__).parent / "backend" / "requirements.txt"
    
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(req_file)],
            check=True,
            capture_output=False
        )
        print(f"{Colors.GREEN}[OK] Dépendances installées{Colors.END}")
    except subprocess.CalledProcessError as e:
        print(f"{Colors.WARNING}[ATTENTION] Erreur installation: {e}{Colors.END}")
        print(f"{Colors.WARNING}Tu peux installer manuellement: pip install -r backend/requirements.txt{Colors.END}")

def setup_directories():
    """Crée les dossiers nécessaires."""
    print(f"\n{Colors.BLUE}[INFO] Configuration des dossiers...{Colors.END}")
    
    dirs = [
        "backend/data/documents",
        "backend/data/faiss_index",
    ]
    
    for d in dirs:
        Path(d).mkdir(parents=True, exist_ok=True)
    
    print(f"{Colors.GREEN}[OK] Dossiers créés{Colors.END}")

def start_backend():
    """Lance le serveur backend FastAPI."""
    print(f"\n{Colors.BLUE}[INFO] Démarrage du backend FastAPI...{Colors.END}")
    
    backend_dir = Path(__file__).parent / "backend"
    os.chdir(str(backend_dir))
    
    # Lancer uvicorn
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        bufsize=1
    )
    
    # Revenir au dossier racine
    os.chdir(str(Path(__file__).parent))
    
    return process

def open_browser():
    """Ouvre le navigateur sur l'application."""
    time.sleep(2)  # Attendre que le serveur démarre
    url = "http://localhost:8000"
    print(f"\n{Colors.GREEN}[OK] Application disponible sur: {Colors.BOLD}{url}{Colors.END}")
    print(f"{Colors.CYAN}[INFO] Documentation API: {url}/docs{Colors.END}")
    print(f"{Colors.CYAN}[INFO] Interface utilisateur: Ouvre frontend/index.html dans ton navigateur{Colors.END}")
    
    try:
        webbrowser.open(f"{url}/docs")
    except:
        pass

def main():
    """Point d'entrée principal."""
    print_banner()
    
    # Vérifications
    check_python()
    install_dependencies()
    setup_directories()
    
    # Instructions
    print(f"""
{Colors.BOLD}📋 INSTRUCTIONS:{Colors.END}

{Colors.GREEN}1. Ajoute tes documents PDF/DOCX dans:{Colors.END}
   backend/data/documents/6eme/Nombres_entiers/
   backend/data/documents/5eme/Fractions/
   ... (organise par classe et chapitre)

{Colors.GREEN}2. Lance le backend:{Colors.END}
   cd backend
   python -m uvicorn app.main:app --reload

{Colors.GREEN}3. Ouvre le frontend:{Colors.END}
   Ouvre frontend/index.html dans ton navigateur

{Colors.GREEN}4. Indexe les documents:{Colors.END}
   POST /index (via http://localhost:8000/docs)

{Colors.GREEN}5. Commence à poser des questions !{Colors.END}
""")
    
    # Démarrer le backend
    print(f"{Colors.BOLD}🚀 Démarrage du serveur...{Colors.END}")
    backend_process = start_backend()
    open_browser()
    
    try:
        # Afficher les logs du backend
        for line in backend_process.stdout:
            print(f"{Colors.CYAN}[Backend]{Colors.END} {line}", end='')
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}Arrêt du serveur...{Colors.END}")
        backend_process.terminate()
        backend_process.wait()
        print(f"{Colors.GREEN}Serveur arrêté. À bientôt !{Colors.END}")

if __name__ == "__main__":
    main()
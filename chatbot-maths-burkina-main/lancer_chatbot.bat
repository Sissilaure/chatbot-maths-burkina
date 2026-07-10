@echo off
title Chat'Maths Burkina Faso
color 0B

echo ============================================
echo   📐 Chat'Maths Burkina Faso v1.0
echo   Assistant mathematiques 6eme - Terminale
echo ============================================
echo.

:: Aller dans le dossier du projet
cd /d "%~dp0"

:: Verifier si les dependances sont installees
echo [INFO] Verification des dependances...
py -c "import fastapi" 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [INSTALLATION] Installation des dependances...
    echo Cela peut prendre 5-10 minutes la premiere fois...
    py -m pip install -r backend\requirements.txt
    if %ERRORLEVEL% NEQ 0 (
        echo [ERREUR] Echec de l'installation.
        pause
        exit /b 1
    )
    echo [OK] Dependances installees !
) else (
    echo [OK] Dependances deja installees
)

:: Creer les dossiers si necessaire
if not exist "backend\data\documents" mkdir backend\data\documents
if not exist "backend\data\faiss_index" mkdir backend\data\faiss_index

:: Lancer le backend
echo.
echo [DEMARRAGE] Lancement du serveur...
echo.
echo ┌─────────────────────────────────────────────┐
echo │  API disponible sur:                        │
echo │  http://127.0.0.1:8000                      │
echo │  Documentation: http://127.0.0.1:8000/docs  │
echo │                                             │
echo │  Frontend: Ouvre frontend\index.html        │
echo │  dans ton navigateur                        │
echo └─────────────────────────────────────────────┘
echo.
echo Appuie sur Ctrl+C pour arreter le serveur
echo.

cd backend
py -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

pause
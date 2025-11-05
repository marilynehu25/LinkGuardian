@echo off
REM ============================================
REM LinkGuardian - Lanceur Simple (1-clic)
REM ============================================
REM Version simplifiee pour debutants
REM Tout est dans un seul fichier !
REM ============================================

title LinkGuardian - Lanceur

REM ============================================
REM PROPOSITION DE PURGE AU DEMARRAGE
REM ============================================
cls
echo.
echo ================================================
echo         BIENVENUE DANS LINKGUARDIAN
echo ================================================
echo.
echo Voulez-vous vider la queue des taches Redis ?
echo (Recommande si vous avez des anciennes taches en attente)
echo.
echo [O] Oui - Vider la queue
echo [N] Non - Garder les taches
echo.
set /p purge_choice="Votre choix (O/N) : "

if /i "%purge_choice%"=="O" (
    echo.
    echo Vidage de la queue Redis en cours...
    
    SET REDIS_PATH=C:\redis
    if exist "%REDIS_PATH%\redis-cli.exe" (
        "%REDIS_PATH%\redis-cli.exe" FLUSHDB >nul 2>&1
        echo OK Queue Redis videe avec succes !
    ) else (
        echo ATTENTION redis-cli.exe non trouve
        echo    La purge sera effectuee au prochain redemarrage de Redis
    )
    echo.
    timeout /t 2 >nul
)

:MENU
cls
echo.
echo ================================================
echo           LINKGUARDIAN - LANCEUR
echo ================================================
echo.
echo   Que voulez-vous faire ?
echo.
echo   [1] Demarrer LinkGuardian
echo   [2] Arreter LinkGuardian
echo   [3] Verifier la configuration (Diagnostic)
echo   [4] Installer les dependances
echo   [5] Quitter
echo.
echo ================================================
echo.

set /p choice="Votre choix (1-5) : "

if "%choice%"=="1" goto START
if "%choice%"=="2" goto STOP
if "%choice%"=="3" goto DIAGNOSTIC
if "%choice%"=="4" goto INSTALL
if "%choice%"=="5" goto END
goto MENU

REM ============================================
REM DEMARRAGE
REM ============================================
:START
cls
echo.
echo ================================================
echo           DEMARRAGE DE LINKGUARDIAN
echo ================================================
echo.

SET REDIS_PATH=C:\redis
SET PROJECT_PATH=%~dp0
SET CONDA_ENV=linkguardian

echo [1/4] Demarrage de Redis...
if not exist "%REDIS_PATH%\redis-server.exe" (
    echo.
    echo ERREUR : Redis non trouve dans %REDIS_PATH%
    echo.
    echo Telechargez Redis ici :
    echo https://github.com/microsoftarchive/redis/releases
    echo.
    echo Puis extrayez-le dans C:\redis
    echo.
    pause
    goto MENU
)

start "Redis Server" cmd /k "cd /d %REDIS_PATH% && redis-server.exe"
timeout /t 2 >nul
echo OK Redis demarre

echo.
echo [2/4] Demarrage de Celery Worker...
start "Celery Worker" cmd /k "cd /d %PROJECT_PATH% && call conda activate %CONDA_ENV% && celery -A app.celery worker --loglevel=info --pool=solo"
timeout /t 2 >nul
echo OK Celery Worker demarre

echo.
echo [3/4] Demarrage de Celery Beat...
start "Celery Beat" cmd /k "cd /d %PROJECT_PATH% && call conda activate %CONDA_ENV% && celery -A app.celery beat --loglevel=info"
timeout /t 2 >nul
echo OK Celery Beat demarre

echo.
echo [4/4] Demarrage de Flask...
start "Flask - LinkGuardian" cmd /k "cd /d %PROJECT_PATH% && call conda activate %CONDA_ENV% && python app.py"
timeout /t 3 >nul
echo OK Flask demarre

echo.
echo ================================================
echo   LINKGUARDIAN EST PRET !
echo ================================================
echo.
echo   Ouvrez votre navigateur :
echo   http://localhost:5000
echo.
echo   ATTENTION Ne fermez pas les 4 fenetres noires !
echo.

REM Ouvrir automatiquement le navigateur
timeout /t 2 >nul
start http://localhost:5000

echo Appuyez sur une touche pour revenir au menu...
pause >nul
goto MENU

REM ============================================
REM ARRET
REM ============================================
:STOP
cls
echo.
echo ================================================
echo           ARRET DE LINKGUARDIAN
echo ================================================
echo.

echo [1/4] Arret de Redis...
taskkill /FI "WINDOWTITLE eq Redis Server" /F >nul 2>&1
echo OK Redis arrete

echo.
echo [2/4] Arret de Celery Worker...
taskkill /FI "WINDOWTITLE eq Celery Worker" /F >nul 2>&1
echo OK Celery Worker arrete

echo.
echo [3/4] Arret de Celery Beat...
taskkill /FI "WINDOWTITLE eq Celery Beat" /F >nul 2>&1
echo OK Celery Beat arrete

echo.
echo [4/4] Arret de Flask...
taskkill /FI "WINDOWTITLE eq Flask - LinkGuardian" /F >nul 2>&1
echo OK Flask arrete

echo.
echo ================================================
echo   TOUS LES SERVICES SONT ARRETES
echo ================================================
echo.
echo Appuyez sur une touche pour revenir au menu...
pause >nul
goto MENU

REM ============================================
REM DIAGNOSTIC
REM ============================================
:DIAGNOSTIC
cls
echo.
echo ================================================
echo           DIAGNOSTIC LINKGUARDIAN
echo ================================================
echo.

SET REDIS_PATH=C:\redis
SET CONDA_ENV=linkguardian
SET ALL_OK=1

echo Verification de la configuration...
echo.

echo [1/5] Redis...
if exist "%REDIS_PATH%\redis-server.exe" (
    echo OK Redis trouve : %REDIS_PATH%
) else (
    echo ERREUR Redis NON trouve dans : %REDIS_PATH%
    SET ALL_OK=0
)

echo.
echo [2/5] Conda...
where conda >nul 2>&1
if %errorlevel%==0 (
    echo OK Conda installe
    
    conda env list | findstr /C:"%CONDA_ENV%" >nul 2>&1
    if %errorlevel%==0 (
        echo OK Environnement '%CONDA_ENV%' trouve
    ) else (
        echo ERREUR Environnement '%CONDA_ENV%' NON trouve
        SET ALL_OK=0
    )
) else (
    echo ERREUR Conda NON installe
    SET ALL_OK=0
)

echo.
echo [3/5] Fichiers du projet...
if exist "%~dp0app.py" (
    echo OK app.py trouve
) else (
    echo ERREUR app.py NON trouve
    SET ALL_OK=0
)

if exist "%~dp0tasks.py" (
    echo OK tasks.py trouve
) else (
    echo ATTENTION tasks.py NON trouve
)

echo.
echo [4/5] Dependances Python...
call conda activate %CONDA_ENV% 2>nul
python -c "import flask, celery, redis" 2>nul
if %errorlevel%==0 (
    echo OK Toutes les dependances installees
) else (
    echo ERREUR Dependances manquantes
    echo    Choisissez l'option [4] pour les installer
    SET ALL_OK=0
)

echo.
echo [5/5] Scripts...
echo OK Lanceur present
echo.

echo ================================================
if %ALL_OK%==1 (
    echo   OK TOUT EST PRET !
    echo ================================================
    echo.
    echo   Vous pouvez demarrer LinkGuardian
    echo   avec l'option [1] du menu
) else (
    echo   ATTENTION CONFIGURATION INCOMPLETE
    echo ================================================
    echo.
    echo   Corrigez les erreurs ci-dessus
)
echo.

pause
goto MENU

REM ============================================
REM INSTALLATION DES DEPENDANCES
REM ============================================
:INSTALL
cls
echo.
echo ================================================
echo      INSTALLATION DES DEPENDANCES
echo ================================================
echo.

SET CONDA_ENV=linkguardian

where conda >nul 2>&1
if %errorlevel% neq 0 (
    echo ERREUR Conda non installe !
    echo.
    echo Installez Anaconda ou Miniconda :
    echo https://www.anaconda.com/products/distribution
    echo.
    pause
    goto MENU
)

echo Verification de l'environnement...
conda env list | findstr /C:"%CONDA_ENV%" >nul 2>&1
if %errorlevel% neq 0 (
    echo L'environnement '%CONDA_ENV%' n'existe pas.
    echo Creation en cours...
    conda create -n %CONDA_ENV% python=3.10 -y
    if %errorlevel% neq 0 (
        echo ERREUR Erreur lors de la creation
        pause
        goto MENU
    )
    echo OK Environnement cree
)

echo.
echo Activation de l'environnement...
call conda activate %CONDA_ENV%

echo.
echo Installation des packages Python...
echo (Cela peut prendre quelques minutes)
echo.

pip install flask flask-login flask-migrate flask-sqlalchemy
pip install celery redis
pip install requests beautifulsoup4 lxml
pip install pandas openpyxl
pip install aiohttp

echo.
echo ================================================
echo   INSTALLATION TERMINEE !
echo ================================================
echo.

pause
goto MENU

REM ============================================
REM QUITTER
REM ============================================
:END
cls
echo.
echo Merci d'avoir utilise LinkGuardian !
echo.
timeout /t 2 >nul
exit
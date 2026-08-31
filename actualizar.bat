@echo off
REM Corrida diaria del buscador. Lo ejecuta el Programador de tareas de Windows.
REM Para probarlo a mano: doble clic en este archivo.

REM UTF-8, si no el log sale con caracteres rotos (ingl?s en vez de ingles).
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

cd /d "%~dp0"
set LOG=datos\corridas.log

echo [%date% %time%] Buscando... >> %LOG%
".venv\Scripts\python.exe" run.py buscar >> %LOG% 2>&1

echo [%date% %time%] Sincronizando con Sheets... >> %LOG%
".venv\Scripts\python.exe" run.py sync >> %LOG% 2>&1

echo [%date% %time%] Generando dashboard... >> %LOG%
".venv\Scripts\python.exe" run.py dashboard >> %LOG% 2>&1

REM --- Deploy a GitHub Pages -------------------------------------------------
REM publicar\ es un repo APARTE que solo contiene el HTML. El codigo fuente y
REM las credenciales nunca se versionan: el sitio es publico.
echo [%date% %time%] Publicando... >> %LOG%
cd publicar
git add -A >> "..\%LOG%" 2>&1
git diff --cached --quiet
if errorlevel 1 (
    git commit -q -m "Actualizacion automatica %date% %time%" >> "..\%LOG%" 2>&1
    git push -q origin main >> "..\%LOG%" 2>&1
    echo [%date% %time%] Publicado. >> "..\%LOG%"
) else (
    echo [%date% %time%] Sin cambios, no se publica. >> "..\%LOG%"
)
cd ..

echo [%date% %time%] Listo. >> %LOG%

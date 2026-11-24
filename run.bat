@echo off
chcp 65001 >nul
cd /d "%~dp0"

set "PY="
where py >nul 2>&1
if %errorlevel%==0 (
  set "PY=py -3"
) else (
  where python >nul 2>&1
  if %errorlevel%==0 (
    set "PY=python"
  )
)

if not defined PY (
  echo Python не найден. Установите Python 3.11 или новее:
  echo https://www.python.org/downloads/
  echo При установке обязательно отметьте "Add python.exe to PATH".
  pause
  exit /b 1
)

if not exist "venv\Scripts\python.exe" (
  echo Создаю виртуальное окружение...
  %PY% -m venv venv
  if errorlevel 1 (
    echo Не удалось создать виртуальное окружение.
    pause
    exit /b 1
  )
)

call venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
  echo Не удалось установить зависимости.
  pause
  exit /b 1
)

if not exist ".env" (
  echo.
  echo Файл .env не найден.
  echo Скопируйте .env.example в .env и укажите BOT_TOKEN и ADMIN_IDS.
  echo Токен берётся у @BotFather, свой ID — у @userinfobot.
  pause
  exit /b 1
)

echo Запускаю бота. Остановка — Ctrl+C.
python -m bot
echo.
pause

@echo off
rem Double-click this file to start the eNote backup viewer.
rem It checks for Python, installs the two needed libraries once
rem (Jinja2, Pillow) and opens a small window.
chcp 65001 >nul
setlocal
cd /d "%~dp0"
title eNote backup viewer

rem --- find Python ----------------------------------------------------------
set "PY="
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 7) else 1)" >nul 2>&1 && set "PY=python"
if not defined PY py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 7) else 1)" >nul 2>&1 && set "PY=py -3"
if not defined PY goto nopython

rem --- install the libraries once -------------------------------------------
%PY% -c "import jinja2, PIL, tkinter" >nul 2>&1 && goto run
echo.
echo Installing the required libraries (only needed once)...
echo 必要なライブラリをインストールしています（初回のみ）...
echo Benoetigte Bibliotheken werden installiert (nur beim ersten Mal)...
echo.
%PY% -m pip install --user --disable-pip-version-check -r requirements.txt
%PY% -c "import jinja2, PIL" >nul 2>&1 || goto piperror
%PY% -c "import tkinter" >nul 2>&1 || goto notk

:run
if defined CHICRACCOON_NO_GUI goto end
echo Starting... / 起動しています... / Wird gestartet...
%PY% -m chicraccoon.gui
if errorlevel 1 goto failed
goto end

:nopython
echo.
echo ============================================================
echo  Python was not found.
echo  1. Your browser now opens https://www.python.org/downloads/
echo  2. Download and run the Python installer.
echo  3. IMPORTANT: on the first screen tick
echo        [x] Add python.exe to PATH
echo     then click "Install Now".
echo  4. Double-click START_Windows.bat again.
echo ------------------------------------------------------------
echo  Python が見つかりません。
echo  1. ブラウザで https://www.python.org/downloads/ が開きます。
echo  2. Python のインストーラーをダウンロードして実行します。
echo  3. 重要：最初の画面で「Add python.exe to PATH」に
echo     チェックを入れてから「Install Now」をクリックします。
echo  4. もう一度 START_Windows.bat をダブルクリックします。
echo ------------------------------------------------------------
echo  Python wurde nicht gefunden.
echo  1. Der Browser oeffnet jetzt https://www.python.org/downloads/
echo  2. Python-Installationsprogramm herunterladen und starten.
echo  3. WICHTIG: im ersten Fenster das Haekchen bei
echo        [x] Add python.exe to PATH
echo     setzen, dann "Install Now" klicken.
echo  4. START_Windows.bat noch einmal doppelklicken.
echo ============================================================
echo.
start "" "https://www.python.org/downloads/"
pause
goto end

:piperror
echo.
echo The libraries could not be installed. Is the computer online?
echo ライブラリをインストールできませんでした。インターネットに接続されていますか？
echo Die Bibliotheken konnten nicht installiert werden. Ist der Computer online?
pause
goto end

:notk
echo.
echo Python was installed without "tcl/tk and IDLE". Please run the Python
echo installer again, choose "Modify" and tick "tcl/tk and IDLE".
echo Python に「tcl/tk and IDLE」が含まれていません。インストーラーを再実行し、
echo 「Modify」で「tcl/tk and IDLE」にチェックを入れてください。
echo Python wurde ohne "tcl/tk and IDLE" installiert. Bitte das Installations-
echo programm erneut starten, "Modify" waehlen und "tcl/tk and IDLE" ankreuzen.
pause
goto end

:failed
echo.
echo Something went wrong (see the messages above).
echo エラーが発生しました（上のメッセージを確認してください）。
echo Etwas ist schiefgegangen (siehe Meldungen oben).
pause

:end
endlocal

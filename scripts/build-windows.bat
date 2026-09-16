@echo off
setlocal
cd /d "%~dp0\.."

python -m pip install -r requirements.txt "pyinstaller>=6"
if errorlevel 1 exit /b 1

python -m PyInstaller --noconfirm --distpath dist --workpath build\pyinstaller-win packaging\windows\do-something.spec
if errorlevel 1 exit /b 1

copy /y dist\DoSomething.exe dist\DoSomething.scr
echo Built dist\DoSomething.exe
echo Copy dist\DoSomething.scr to install as a screensaver (right-click - Install).
echo Unsigned: SmartScreen may warn. That is expected.

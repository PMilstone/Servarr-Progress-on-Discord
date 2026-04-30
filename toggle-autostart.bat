@echo off
echo.
echo ================================================================
echo Servarr Progress Autostart Manager
echo ================================================================
echo.

REM Get the current directory
set "SCRIPT_DIR=%~dp0"
set "BAT_FILE=%SCRIPT_DIR%Servarr-Progress-on-Discord.bat"
set "POWERSHELL=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"

REM Check if shortcut exists using PowerShell
"%POWERSHELL%" -Command "$WShell = New-Object -ComObject WScript.Shell; $Startup = $WShell.SpecialFolders^('Startup'^); Test-Path ^($Startup + '\Servarr-Progress-on-Discord.lnk'^)" >nul 2>&1

if errorlevel 1 goto CREATE
goto CHECK_DISABLE

:CREATE
REM Shortcut does not exist - create it
echo Status: Autostart is currently DISABLED
echo.
echo Creating startup shortcut...

"%POWERSHELL%" -Command "$WShell = New-Object -ComObject WScript.Shell; $Startup = $WShell.SpecialFolders^('Startup'^); $Shortcut = $WShell.CreateShortcut^($Startup + '\\Servarr-Progress-on-Discord.lnk'^); $Shortcut.TargetPath = '%BAT_FILE%'; $Shortcut.WorkingDirectory = '%SCRIPT_DIR%'; $Shortcut.WindowStyle = 7; $Shortcut.Save^(^)"

if errorlevel 1 (
    echo Error: Failed to create shortcut
    pause
    exit /b 1
)

echo.
echo Success! Autostart is now ENABLED.
echo The service will start automatically when you log in to Windows.
echo.
goto END

:CHECK_DISABLE
REM Shortcut exists - ask if user wants to remove it
echo Status: Autostart is currently ENABLED
echo.
set /p "CHOICE=Do you want to DISABLE autostart? (Y/N): "

REM Trim spaces and convert to uppercase for comparison
for /f "tokens=* delims= " %%a in ("%CHOICE%") do set "CHOICE=%%a"

if /i "%CHOICE%"=="Y" goto DISABLE
if /i "%CHOICE%"=="YES" goto DISABLE

echo.
echo No changes made. Autostart remains ENABLED.
echo.
goto END

:DISABLE
echo.
echo Removing startup shortcut...

"%POWERSHELL%" -Command "$WShell = New-Object -ComObject WScript.Shell; $Startup = $WShell.SpecialFolders^('Startup'^); Remove-Item ^($Startup + '\\Servarr-Progress-on-Discord.lnk'^)"

if errorlevel 1 (
    echo Error: Failed to remove shortcut
    pause
    exit /b 1
)

echo.
echo Success! Autostart is now DISABLED.
echo The service will no longer start automatically on login.
echo.

:END

pause

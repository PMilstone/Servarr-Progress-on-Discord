@echo off
echo.
echo ================================================================
echo Servarr Progress Autostart Manager
echo ================================================================
echo.

REM Get the current directory
set "SCRIPT_DIR=%~dp0"
set "BAT_FILE=%SCRIPT_DIR%Servarr-Progress-on-Discord.bat"

REM Check if shortcut exists using PowerShell
powershell -Command "$WShell = New-Object -ComObject WScript.Shell; $Startup = $WShell.SpecialFolders('Startup'); Test-Path ($Startup + '\Servarr-Progress-on-Discord.lnk')" >nul 2>&1

if errorlevel 1 (
    REM Shortcut does not exist - create it
    echo Status: Autostart is currently DISABLED
    echo.
    echo Creating startup shortcut...
    
    powershell -Command "$WShell = New-Object -ComObject WScript.Shell; $Startup = $WShell.SpecialFolders('Startup'); $Shortcut = $WShell.CreateShortcut($Startup + '\Servarr-Progress-on-Discord.lnk'); $Shortcut.TargetPath = '%BAT_FILE%'; $Shortcut.WorkingDirectory = '%SCRIPT_DIR%'; $Shortcut.WindowStyle = 7; $Shortcut.Save()"
    
    if errorlevel 1 (
        echo Error: Failed to create shortcut
        pause
        exit /b 1
    )
    
    echo.
    echo Success! Autostart is now ENABLED.
    echo The service will start automatically when you log in to Windows.
    echo.
) else (
    REM Shortcut exists - ask if user wants to remove it
    echo Status: Autostart is currently ENABLED
    echo.
    set /p "CHOICE=Do you want to DISABLE autostart? (Y/N): "
    
    if /i "%CHOICE%"=="Y" (
        echo.
        echo Removing startup shortcut...
        
        powershell -Command "$WShell = New-Object -ComObject WScript.Shell; $Startup = $WShell.SpecialFolders('Startup'); Remove-Item ($Startup + '\Servarr-Progress-on-Discord.lnk')"
        
        if errorlevel 1 (
            echo Error: Failed to remove shortcut
            pause
            exit /b 1
        )
        
        echo.
        echo Success! Autostart is now DISABLED.
        echo The service will no longer start automatically on login.
        echo.
    ) else (
        echo.
        echo No changes made. Autostart remains ENABLED.
        echo.
    )
)

pause

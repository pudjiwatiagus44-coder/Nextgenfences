@echo off
title NextGenFences v1.0 ????
echo ========================================
echo   NextGenFences v1.0 ????
echo ========================================
echo.

set "INSTALL_DIR=%LOCALAPPDATA%\NextGenFences"
set "DESKTOP_LINK=%USERPROFILE%\Desktop\NextGenFences.lnk"

echo ?????: %INSTALL_DIR%
echo.

:: ??????
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

:: ????
copy /Y "NextGenFences.exe" "%INSTALL_DIR%\" >nul
copy /Y "config.json" "%INSTALL_DIR%\" >nul

:: ????????
powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%DESKTOP_LINK%'); $s.TargetPath = '%INSTALL_DIR%\NextGenFences.exe'; $s.WorkingDirectory = '%INSTALL_DIR%'; $s.Save()"

echo.
echo ========================================
echo   ?????
echo ========================================
echo.
echo ??????: %INSTALL_DIR%
echo ?????????
echo.
echo ????????...
pause >nul

start "" "%INSTALL_DIR%\NextGenFences.exe"

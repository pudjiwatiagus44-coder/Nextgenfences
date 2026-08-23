@echo off
title NextGenFences v1.0 ????
echo ========================================
echo   NextGenFences v1.0 ????
echo ========================================
echo.

set "INSTALL_DIR=%LOCALAPPDATA%\NextGenFences"
set "DESKTOP_LINK=%USERPROFILE%\Desktop\NextGenFences.lnk"

echo ????...
echo.

:: ????????
if exist "%DESKTOP_LINK%" del "%DESKTOP_LINK%"

:: ??????
if exist "%INSTALL_DIR%" rd /s /q "%INSTALL_DIR%"

echo.
echo ========================================
echo   ?????
echo ========================================
echo.
pause

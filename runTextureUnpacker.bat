@echo off
setlocal enabledelayedexpansion

REM --- Configuration ---
REM IMPORTANT: Set the full path to your Blender executable below.
set BLENDER_PATH="C:\Program Files\Blender Foundation\Blender 4.0\blender.exe"

REM --- Script Variables ---
REM Assumes textureUnpacker.py is in the same directory as this batch script
set SCRIPT_NAME=textureUnpacker.py
set SCRIPT_PATH="%~dp0%SCRIPT_NAME%"
set INPUT_FBX=""


REM --- Argument Parsing ---
:parse_args
IF "%~1"=="" GOTO args_done
IF /I "%~1"=="-f" (
    REM Check if next argument exists and isn't another option
    if "%~2"=="" (
        echo Error: Missing file path after -f option.
        goto usage
    )
    if NOT "%~2:~0,1%"=="-" (
        set "INPUT_FBX=%~2"
        SHIFT
        SHIFT
        GOTO parse_args
    ) else (
        echo Error: Missing file path after -f option. Found option '%~2' instead.
        goto usage
    )
)
echo Unknown option: %1
goto usage
:args_done

REM --- Validation ---
IF "%INPUT_FBX%"=="" (
    echo Error: Input FBX file path is required. Use the -f option.
    goto usage
)



IF NOT EXIST %BLENDER_PATH% (
    echo Error: Blender executable not found at the specified path:
    echo %BLENDER_PATH%
    echo Please edit this batch script and set the correct BLENDER_PATH- variable.
    goto end
)

IF NOT EXIST %SCRIPT_PATH% (
    echo Error: Python script not found: %SCRIPT_PATH%
    echo Ensure '%SCRIPT_NAME%' is in the same directory as this batch script 
    goto end
)

REM Check if input file exists (handle quotes correctly)
IF NOT EXIST "%INPUT_FBX%" (
    echo Error: Input FBX file not found: "%INPUT_FBX%"
    goto end
)

echo SCRIPT_PATH


REM --- Execution ---
echo Starting Texture Unpacker...
echo   Blender Path: %BLENDER_PATH%
echo   Script Path: %SCRIPT_PATH%
echo   Input FBX:   "%INPUT_FBX%"
echo.
echo Running Blender in background mode. Please wait...
echo (Output from Blender and the Python script will appear below)
echo ----------------------------------------------------

REM Construct the command
REM -b : Run in background (no UI)
REM -P : Run the specified Python script
REM -- : Separator - arguments after this are passed to the Python script
REM --input "%INPUT_FBX%" : Argument for your textureUnpacker.py script
%BLENDER_PATH% -b -P %SCRIPT_PATH% -- --input "%INPUT_FBX%"

echo ----------------------------------------------------
echo.
echo Batch script finished. Check console output above for success or errors.
goto end

:usage
echo.
echo Usage: %~nx0 -f "path\to\your\model.fbx"
echo.
echo   -f : Specify the path to the input FBX file (required).
echo        Enclose the path in quotes if it contains spaces.
echo.
echo Example:
echo   %~nx0 -f "C:\My Models\character_packed.fbx"
echo.
echo Note: You MUST edit this script (%~nx0) to set the correct
echo       BLENDER_PATH variable near the top before running.

:end
echo.
pause
endlocal
exit /b
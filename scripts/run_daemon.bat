@echo off
REM ==============================================================================
REM AER Autonomous Background Resident Daemon (Windows Launcher)
REM ==============================================================================

set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%.."

if "%1"=="start" (
    echo Starting AER daemon in background...
    python -m aer.cli start
    goto end
)

if "%1"=="stop" (
    echo Stopping AER daemon...
    python -m aer.cli stop
    goto end
)

if "%1"=="status" (
    python -m aer.cli status
    goto end
)

if "%1"=="run" (
    echo Running AER daemon in foreground console mode...
    python -m aer.cli run
    goto end
)

echo Usage: run_daemon.bat [start ^| stop ^| status ^| run]
:end

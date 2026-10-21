@echo off
REM run_resilient.bat -- auto-resumes orchestrate.py if it dies partway
REM (network drop, transient Docker error, etc). Safe to re-run by hand too.
REM
REM Usage:  run_resilient.bat final --workers 2
REM         (first arg = --run-name value, rest is passed straight through)

set RUN_NAME=%1
if "%RUN_NAME%"=="" set RUN_NAME=final
shift

set MAX_TRIES=10
set /a TRY=0

:loop
set /a TRY+=1
echo.
echo ===== Attempt %TRY%/%MAX_TRIES% (run-name=%RUN_NAME%) =====
docker compose run --rm --no-deps -v "%cd%\evaluation:/evaluation" -w /evaluation backend python orchestrate.py --run-name %RUN_NAME% %1 %2 %3 %4 %5 %6 %7 %8
if %ERRORLEVEL% EQU 0 goto done
if %TRY% GEQ %MAX_TRIES% goto failed
echo Exit code %ERRORLEVEL% -- waiting 20s then resuming (already-finished files are skipped)...
timeout /t 20 /nobreak >nul
goto loop

:done
echo.
echo Finished successfully after %TRY% attempt(s).
goto end

:failed
echo.
echo Gave up after %MAX_TRIES% attempts. Re-run this script by hand once the issue
echo (network / API / Docker) is fixed -- it will resume, not restart.

:end

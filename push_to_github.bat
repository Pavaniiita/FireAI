@echo off
echo ========================================================
echo Pushing FireAI Project to GitHub: https://github.com/Pavaniiita/FireAI
echo ========================================================
echo.
echo Make sure you have created an empty repository named 'FireAI' at:
echo https://github.com/new (set visibility to Public)
echo.
git push -u origin main
if %ERRORLEVEL% EQU 0 (
    echo.
    echo [SUCCESS] FireAI repository successfully pushed to GitHub!
) else (
    echo.
    echo [NOTE] If repository does not exist yet, please create it at https://github.com/new
    echo Or if you have a GitHub Personal Access Token (PAT), run:
    echo   git remote set-url origin https://<YOUR_TOKEN>@github.com/Pavaniiita/FireAI.git
    echo   git push -u origin main
)
pause

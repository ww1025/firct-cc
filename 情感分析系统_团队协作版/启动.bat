@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================
echo   Emotion Analysis System - ZJU
echo ============================================
echo.

if not exist "%~dp0sklearn_emotion_model.pkl" (
    echo [ERROR] sklearn_emotion_model.pkl not found!
    echo Please make sure all files are extracted.
    pause
    exit /b 1
)

if not exist "%~dp0tfidf_vectorizer.pkl" (
    echo [ERROR] tfidf_vectorizer.pkl not found!
    pause
    exit /b 1
)

echo [OK] All model files found.
echo.

echo Starting Streamlit...
echo Open: http://localhost:8501
echo.

start "" http://localhost:8501
python -m streamlit run "%~dp0app.py" --server.headless true --server.port 8501

pause

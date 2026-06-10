@echo off
cd /d "%~dp0"
echo === ZJU Emotion Analysis ===
echo Dir: %CD%
echo.

taskkill /f /im python.exe >nul 2>&1
if exist __pycache__ rmdir /s /q __pycache__ 2>nul
if exist "%USERPROFILE%\.streamlit\cache" rmdir /s /q "%USERPROFILE%\.streamlit\cache" 2>nul

echo Step 1/3: Check models...
if not exist "sklearn_emotion_model.pkl" (echo ERROR: model missing! & pause & exit /b 1)
if not exist "tfidf_vectorizer.pkl" (echo ERROR: vectorizer missing! & pause & exit /b 1)
if not exist "processed_data.npz" (echo ERROR: data missing! & pause & exit /b 1)
echo   OK

echo Step 2/3: Test load...
python -c "from emotion_engine import load_models; m,v,c=load_models(); print('   OK:', c)"
if %errorlevel% neq 0 (echo FAILED! & pause & exit /b 1)

echo Step 3/3: Start Streamlit...
echo ========================================
echo   http://localhost:8501
echo   Press Ctrl+C to stop
echo ========================================
start http://localhost:8501
python -m streamlit run app.py --server.headless true --server.port 8501
pause

cd /d "%~dp0"

if not exist "%~dp0sklearn_emotion_model.pkl" (
    echo Model file not found! Please EXTRACT all files first.
    echo Right-click the ZIP -> Extract All -> then run this bat again.
    pause
    exit /b 1
)

echo Starting Emotion Analysis System...
echo Opening http://localhost:8501

start "" http://localhost:8501
python -m streamlit run "%~dp0app.py" --server.headless true --server.port 8501

pause

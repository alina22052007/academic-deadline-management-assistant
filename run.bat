@echo off
echo === Academic Deadline Management Assistant ===

if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

call venv\Scripts\activate.bat

echo Verifying dependencies...
pip install --upgrade pip -q
pip install -r requirements.txt -q

if not exist ".env" (
    if exist ".env.example" (
        echo Creating .env from .env.example...
        copy .env.example .env
    )
)

echo Launching Streamlit application...
streamlit run app.py
pause


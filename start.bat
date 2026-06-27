@echo off
cd /d E:\develop\ai-research-assistant
start "" http://localhost:8501
python -m streamlit run app.py --server.headless true
pause

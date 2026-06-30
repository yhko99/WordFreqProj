@echo off
chcp 65001 > nul
echo ========================================
echo  화장품 리뷰 구매 가이드 서비스 실행
echo ========================================
echo.
echo 필요한 패키지를 설치합니다...
pip install -r requirements.txt
echo.
echo 서비스를 시작합니다...
echo 브라우저에서 http://localhost:8501 로 접속하세요.
echo 종료하려면 이 창을 닫으세요.
echo.
streamlit run app.py
pause

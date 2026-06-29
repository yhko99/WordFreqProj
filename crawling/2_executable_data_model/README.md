# 화장품 리뷰 구매 가이드 서비스 — 실행 패키지

이 폴더만으로 서비스를 바로 실행할 수 있습니다 (데이터·모델 포함).

## 실행 방법

```bash
pip install -r requirements.txt
streamlit run app.py
```

브라우저가 자동으로 열리지 않으면 `http://localhost:8501` 접속.

## 폴더 구성

| 파일/폴더 | 설명 |
|---|---|
| `app.py` | 실행 진입점 |
| `dashboard_ui.py` | Streamlit 화면 렌더링 |
| `sentiment_utils.py` | 데이터/모델 로직 |
| `beauty_reviews_merged.csv` | 무신사·올리브영·쿠팡 통합 리뷰 데이터 (167,996건) |
| `model_comparison.json` | LSTM/GRU/Transformer 성능 비교 지표 |
| `model/` | 학습된 모델 4종 (LSTM 기준모델, LSTM/GRU/Transformer 비교용) + 토크나이저 |

## 제공 기능

1. **전체 통계** — 감성/평점/키워드 분포
2. **상품 구매 가이드** — 상품 검색 시 구매 추천도, 장단점, 대표 리뷰 제공
3. **실시간 감성 예측** — 문장 입력 시 긍정/부정 즉시 판단 (LSTM/GRU/Transformer 선택 가능)

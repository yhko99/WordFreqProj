# 소스 코드 + 데이터

전체 파이프라인을 처음부터 재현하기 위한 스크립트와 데이터입니다.

## 실행 순서

1. `musinsa_beauty_crawler.py` / `run_musinsa_bulk.py` — 무신사 리뷰 크롤링 (Selenium)
2. `merge_team_data.py` — 무신사+올리브영+쿠팡 데이터 병합, 평점 기반 라벨링, 언더샘플링
   → 결과: `beauty_reviews_merged.csv` (167,996건, 이 폴더에 포함됨)
3. `train_sentiment_model.py` — LSTM 기준 모델 학습 (`../model/sa_model_beauty_v2.keras`)
4. `train_compare_models.py` — LSTM/GRU/Transformer 3개 비교 학습 (`../model/compare_*.keras`)
5. `save_compare_tokenizer.py` — 비교 학습용 토크나이저 별도 저장
6. `analyze_reviews.py` — 키워드/평점 차트 등 정적 분석 (선택)
7. `make_slides.py` — 발표자료(.pptx) 자동 생성

## 서비스 소스

- `app.py`, `dashboard_ui.py`, `sentiment_utils.py` — Streamlit 서비스 (실행 가능한 형태는 `2_executable_data_model/` 참고)

## 참고

올리브영·쿠팡 원본 크롤링 데이터(jsonl/csv, 약 300MB)는 용량 문제로 이 저장소에 포함하지 않았습니다.
`merge_team_data.py`는 `./external_raw/oliveyoung/*.jsonl`, `./external_raw/coupang/*.csv` 경로를 기대합니다.

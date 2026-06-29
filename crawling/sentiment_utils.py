"""
무신사 뷰티 리뷰 감성분석 - 데이터/모델 로직 (Streamlit 호출 없음)
"""
import json
import re
from collections import Counter

import joblib
import numpy as np
import pandas as pd
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.sequence import pad_sequences

MAX_LEN = 100
LABELS = ['부정', '긍정']  # 0=부정, 1=긍정 (학습 시 to_categorical 인코딩과 동일)

# v2: 무신사+올리브영+쿠팡 병합, 실제 평점 기반 라벨링 (키워드 추측 방식 폐기)
DATA_PATH      = './beauty_reviews_merged.csv'

# 3개 아키텍처 비교 모델 (동일 토크나이저 공유, train_compare_models.py로 학습)
COMPARE_TOKENIZER_PATH = './model/compare_tokenizer.pkl'
COMPARE_MODEL_PATHS = {
    'LSTM': './model/compare_lstm.keras',
    'GRU': './model/compare_gru.keras',
    'Transformer': './model/compare_transformer.keras',
}
COMPARE_METRICS_PATH = './model_comparison.json'

# 실제 데이터에서 뽑은 대표 리뷰 (Streamlit 예시 버튼용, 클릭마다 랜덤으로 하나씩 노출)
EXAMPLE_POSITIVES = [
    "무기자차라 트러블 하나도 없고 완전 대만족",
    "생각보다 피부가 부들해지는게 빨리 느껴져서 좋았어요 재구매각",
    "추천합니다 성분도 좋고 바르면 촉촉해요 피부도 좋아집니다",
    "또 살거예요 최고예요 좋아요 피부 들뜸없이 건조함 싹 잡아줍니다",
    "속건조 잡아주기에 좋아요 피부톤도 맑아지고 촉촉해서 강추합니다",
    "거의 세통이나 쓰고 있는 수분크림입니다 겨울에 정말 추천해요",
    "여러 번 사용해도 질리지 않아서 더 좋네요 데일리템으로 추천합니다",
]
EXAMPLE_NEGATIVES = [
    "이거 쓰고 피부 뒤집어졌어요...ㅠㅠㅠ 예민하고 민감한 편이 아닌데 뒤집어져서 많이 당황했습니다..",
    "이거쓰고 피부 뒤집어져서 엄청 고생함 나한테는 오일은 안맞는듯",
    "냄새도 이상하고 세정력도 별로에요 가성비 완전 비추입니다",
    "제 피부에는 너무너무 안 맞아서 트러블 올라 오고 난리도 아니었습니다",
    "진짜 하나도 안시원하고 간지러워요 진짜 완전 비추천 너무 비싸요",
    "쓰고나서 피부 뒤집어졌어요 수부지 민감성 피부인데 안맞아요",
    "후기가 좋아서 구매했는데 제 피부에는 맞지 않는건지 트러블이 올라와서 사용중단했어요",
]

STOPWORDS = {
    '있다', '하다', '이다', '같다', '되다', '없다', '그리고', '그런데',
    '하지만', '그냥', '정말', '너무', '진짜', '좋다', '사용', '제품',
    '구매', '느낌', '것같', '것도', '근데', '이번', '이제', '있어',
    '해서', '이거', '그게', '거라', '하고', '이런', '저는', '에서',
    '으로', '에도', '부터', '까지', '이라', '해요', '했어', '했는데',
    '합니다', '입니다', '같아요', '좋아요', '봤는데',
    # 장점/단점 키워드에서 의미 없는 일반어 제거용 (구매 가이드 품질 개선)
    '쓰고', '있어요', '좋습니다', '항상', '발라도', '나서', '저한테는',
    '얼굴에', '바로', '샀는데', '많이', '주문했는데', '쓰는', '쓸때',
    '쓰니', '써도', '써서', '쓰면', '쓰는데', '좋고', '많은', '같은',
    # brand_name 필드가 영문이라 못 걸러지는 한글 브랜드 표기 (자주 보이는 것만 수동 추가)
    '토리든', '라로슈포제', '아벤느', '이니스프리', '에뛰드',
}


def load_model_and_tokenizer(model_name: str = 'LSTM'):
    """선택한 아키텍처(LSTM/GRU/Transformer)의 모델 + 공유 토크나이저 로딩"""
    model = load_model(COMPARE_MODEL_PATHS[model_name])
    tokenizer = joblib.load(COMPARE_TOKENIZER_PATH)
    return model, tokenizer


def load_model_metrics() -> dict:
    """model_comparison.json -> {모델명: 지표dict}"""
    with open(COMPARE_METRICS_PATH, encoding='utf-8') as f:
        rows = json.load(f)
    return {r['model']: r for r in rows}


def predict_sentiment(text: str, model, tokenizer, max_len: int = MAX_LEN):
    """
    musinsa_sentiment_analysis.ipynb의 analyze_sentiment()와 동일한 전처리·예측 로직.
    한글+공백만 남기기 -> 형태소 토큰화(Okt) -> Integer Encoding -> Padding -> 예측
    """
    from konlpy.tag import Okt

    clean = re.sub('[^ 가-힣]+', ' ', text)
    tokens = Okt().morphs(clean)
    encoded = tokenizer.texts_to_sequences([tokens])
    X = pad_sequences(encoded, maxlen=max_len)
    preds = model.predict(X, verbose=0)
    result_index = int(np.argmax(preds[0]))
    return LABELS[result_index], float(preds[0][result_index])


def load_review_data(file_path: str = DATA_PATH) -> pd.DataFrame:
    """병합 리뷰 데이터 로딩 (무신사+올리브영+쿠팡, 평점 기반 label 0/1)"""
    cols = ['platform', 'product_name', 'brand_name', 'rating', 'review_text', 'label']
    df = pd.read_csv(file_path, encoding='utf-8-sig', usecols=cols, low_memory=False)
    df.dropna(subset=['review_text'], inplace=True)
    df['sentiment'] = df['label'].map({1: '긍정', 0: '부정'})
    return df


def get_product_list(df: pd.DataFrame) -> list:
    """리뷰 수가 많은 순으로 상품명 목록 반환 (상품명 없는 행은 제외)"""
    named = df[df['product_name'] != '(상품명 없음)']
    return named['product_name'].value_counts().index.tolist()


def get_product_reviews(df: pd.DataFrame, product_name: str) -> pd.DataFrame:
    """선택한 상품의 리뷰만 필터링"""
    return df[df['product_name'] == product_name]


def sentiment_distribution(df: pd.DataFrame) -> pd.Series:
    """긍정/중립/부정 건수"""
    return df['sentiment'].value_counts()


def top_keywords(df: pd.DataFrame, n: int = 20) -> Counter:
    """리뷰 텍스트에서 자주 나오는 단어 Top N (analyze_reviews.py 로직 재사용)"""
    all_text = " ".join(df['review_text'].dropna().astype(str))
    words = re.findall(r"[가-힣]{2,5}", all_text)
    words = [w for w in words if w not in STOPWORDS]
    return Counter(words).most_common(n)


def get_verdict(positive_ratio: float) -> dict:
    """긍정 비율을 보고 소비자용 구매 추천도 판정"""
    if positive_ratio >= 80:
        return {"label": "구매 추천", "emoji": "✅", "color": "#2ecc71",
                "desc": "긍정 리뷰가 대부분입니다. 믿고 구매해도 좋습니다."}
    elif positive_ratio >= 60:
        return {"label": "괜찮은 선택", "emoji": "🙂", "color": "#8bc34a",
                "desc": "긍정 리뷰가 더 많지만, 아래 단점도 한번 확인해보세요."}
    elif positive_ratio >= 40:
        return {"label": "신중한 결정 필요", "emoji": "⚠️", "color": "#f0ad4e",
                "desc": "긍정과 부정 의견이 비슷하게 갈립니다. 리뷰를 꼼꼼히 살펴보세요."}
    else:
        return {"label": "비추천", "emoji": "❌", "color": "#e74c3c",
                "desc": "부정 리뷰가 더 많습니다. 다른 상품도 비교해보는 걸 추천합니다."}


def top_keywords_for_sentiment(product_df: pd.DataFrame, sentiment: str, n: int = 5) -> list:
    """특정 상품 리뷰 중 긍정/부정만 따로 추려서 키워드 Top N (장점/단점 추출용)
    브랜드명은 "장점"으로서 의미가 없으므로 제외한다."""
    subset = product_df[product_df['sentiment'] == sentiment]
    brand_names = set(product_df['brand_name'].dropna().astype(str)) - {''}
    extra_stop = STOPWORDS | brand_names
    all_text = " ".join(subset['review_text'].dropna().astype(str))
    words = re.findall(r"[가-힣]{2,5}", all_text)
    words = [w for w in words if w not in extra_stop and not any(b in w or w in b for b in brand_names if b)]
    return Counter(words).most_common(n)


def get_representative_review(product_df: pd.DataFrame, sentiment: str,
                               min_len: int = 15, max_len: int = 90) -> str:
    """대표 인용 리뷰 1개 (너무 짧거나 길지 않은 것 우선)"""
    subset = product_df[product_df['sentiment'] == sentiment].copy()
    if subset.empty:
        return ""
    subset['len'] = subset['review_text'].astype(str).str.len()
    sized = subset[(subset['len'] >= min_len) & (subset['len'] <= max_len)]
    pool = sized if not sized.empty else subset
    return pool.iloc[0]['review_text']

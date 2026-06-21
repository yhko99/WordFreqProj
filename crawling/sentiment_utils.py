"""
무신사 뷰티 리뷰 감성분석 - 데이터/모델 로직 (Streamlit 호출 없음)
"""
import re
from collections import Counter

import joblib
import numpy as np
import pandas as pd
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.sequence import pad_sequences

MAX_LEN = 100
LABELS = ['부정', '긍정']  # 0=부정, 1=긍정 (학습 시 to_categorical 인코딩과 동일)

DATA_PATH      = './musinsa_beauty_TOTAL.csv'
MODEL_PATH     = './model/sa_model_beauty.keras'
TOKENIZER_PATH = './model/sa_tokenizer_beauty.pkl'

STOPWORDS = {
    '있다', '하다', '이다', '같다', '되다', '없다', '그리고', '그런데',
    '하지만', '그냥', '정말', '너무', '진짜', '좋다', '사용', '제품',
    '구매', '느낌', '것같', '것도', '근데', '이번', '이제', '있어',
    '해서', '이거', '그게', '거라', '하고', '이런', '저는', '에서',
    '으로', '에도', '부터', '까지', '이라', '해요', '했어', '했는데',
    '합니다', '입니다', '같아요', '좋아요', '봤는데',
}


def load_model_and_tokenizer(model_path: str = MODEL_PATH, tokenizer_path: str = TOKENIZER_PATH):
    """학습된 LSTM 모델 + 토크나이저 로딩"""
    model = load_model(model_path)
    tokenizer = joblib.load(tokenizer_path)
    return model, tokenizer


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
    """리뷰 데이터 로딩 (필요한 컬럼만)"""
    cols = ['product_id', 'product_name', 'brand_name', 'rating', 'review_text', 'sentiment']
    df = pd.read_csv(file_path, encoding='utf-8-sig', usecols=cols, low_memory=False)
    df.dropna(subset=['review_text'], inplace=True)
    return df


def get_product_list(df: pd.DataFrame) -> list:
    """리뷰 수가 많은 순으로 상품명 목록 반환"""
    return df['product_name'].value_counts().index.tolist()


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

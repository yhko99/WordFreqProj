"""
무신사 뷰티 리뷰 감성분석 Streamlit 앱

실행:
    conda activate aiservice26
    cd E:\\_AIService26\\Webcrolling\\crawling
    streamlit run app.py
"""
import streamlit as st

import sentiment_utils as su
import dashboard_ui as ui

st.set_page_config(page_title="무신사 뷰티 리뷰 감성분석", layout="wide")


@st.cache_data
def _load_data():
    return su.load_review_data()


@st.cache_resource
def _load_model(model_name: str):
    return su.load_model_and_tokenizer(model_name)


@st.cache_data
def _load_metrics():
    return su.load_model_metrics()


ui.render_header()

with st.spinner("데이터 로딩 중... (최초 1회만 느립니다)"):
    df = _load_data()

page, model_name = ui.render_sidebar()
metrics = _load_metrics()

if page == "전체 통계":
    ui.render_overview_page(df)
elif page == "상품 구매 가이드":
    ui.render_product_page(df)
elif page == "실시간 감성 예측":
    with st.spinner(f"{model_name} 모델 로딩 중..."):
        model, tokenizer = _load_model(model_name)
    ui.render_predict_page(model, tokenizer, model_name, metrics)

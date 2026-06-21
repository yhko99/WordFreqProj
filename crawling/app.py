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
def _load_model():
    return su.load_model_and_tokenizer()


ui.render_header()

with st.spinner("데이터 로딩 중... (최초 1회만 느립니다)"):
    df = _load_data()

with st.spinner("모델 로딩 중..."):
    model, tokenizer = _load_model()

page = ui.render_sidebar()

if page == "전체 통계":
    ui.render_overview_page(df)
elif page == "상품별 리뷰":
    ui.render_product_page(df)
elif page == "실시간 감성 예측":
    ui.render_predict_page(model, tokenizer)

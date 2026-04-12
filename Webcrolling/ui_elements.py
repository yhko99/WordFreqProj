import streamlit as st
import pandas as pd

def render_header():
    st.title("🎬 영화 리뷰 감성 및 키워드 분석")
    st.info("데이터를 업로드하면 인공지능이 키워드를 분석해 드립니다.")

def sidebar_settings():
    with st.sidebar:
        st.header("📊 분석 옵션")
        target_col = st.text_input("리뷰 컬럼명", value="review")
        bar_count = st.slider("그래프 표시 단어 수", 5, 50, 20)
        
        st.markdown("---")
        run_btn = st.button("🚀 분석 시작")
        
    return target_col, bar_count, run_btn

def preview_data(uploaded_file):
    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        st.write("### 데이터 미리보기 (상위 5행)")
        st.dataframe(df.head())

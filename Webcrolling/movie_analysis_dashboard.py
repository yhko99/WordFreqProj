import streamlit as st
from konlpy.tag import Okt
from collections import Counter
import nlp_utils as nlp
import ui_elements as ui
import os

# --- PAGE CONFIG ---
st.set_page_config(page_title="Movie Review AI", layout="wide")

# --- UI HEADER ---
ui.render_header()

# --- SIDEBAR & SETTINGS ---
with st.sidebar:
    uploaded_file = st.file_uploader("리뷰 CSV 파일을 업로드하세요", type=['csv'])

target_col, bar_count, run_btn = ui.sidebar_settings()

# --- DATA PREVIEW ---
if uploaded_file:
    ui.preview_data(uploaded_file)

# --- ANALYSIS ENGINE ---
if uploaded_file and run_btn:
    # 교수님 지정 스타일 설정
    my_tags = ['Noun', 'Verb', 'Adjective']
    my_stopwords = ['영화', '정말', '진짜', '하는', '이다', '것', '수', '좀', '그', '이', '보고', '본', '들', '보']
    font_path = "c:/Windows/Fonts/malgun.ttf" # 윈도우 환경 기준
    
    # 리눅스/웹 서버 환경 대응 (파일이 있을 경우)
    if not os.path.exists(font_path):
        font_path = "malgun.ttf" # 현재 폴더에 폰트가 있을 경우를 대비

    try:
        with st.spinner("텍스트 데이터를 분석 중입니다. 잠시만 기다려주세요..."):
            # 1. 데이터 로드
            review_list = nlp.load_review_data(uploaded_file, target_col)
            
            # 2. 형태소 분석 및 토큰 추출
            tagger = Okt()
            my_tokens = nlp.get_cleaned_tokens(review_list, tagger.pos, my_tags, my_stopwords)
            
            # 3. 빈도수 계산
            my_counter = Counter(my_tokens)
            
        # 결과 대시보드 출력
        st.success(f"✅ 분석 완료! 총 {len(my_tokens):,}개의 핵심 단어를 추출했습니다.")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("#### 📊 빈도수 그래프")
            fig_bar = nlp.show_frequency_chart(my_counter, bar_count, font_path)
            st.pyplot(fig_bar.gcf())
            
        with col2:
            st.write("#### ☁️ 워드클라우드")
            fig_wc = nlp.generate_wordcloud_img(my_counter, font_path)
            st.pyplot(fig_wc.gcf())
            
    except Exception as e:
        st.error(f"⚠️ 분석 중 오류가 발생했습니다: {e}")
        st.info("사이드바의 '리뷰 컬럼명'이 실제 파일과 일치하는지 확인해 주세요.")

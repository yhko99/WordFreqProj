"""
무신사 뷰티 리뷰 감성분석 - Streamlit UI 렌더링 함수 모음
"""
import os

import streamlit as st
import matplotlib.pyplot as plt
from matplotlib import font_manager, rc

import sentiment_utils as su

FONT_PATH = "c:/Windows/Fonts/malgun.ttf"
if not os.path.exists(FONT_PATH):
    FONT_PATH = "malgun.ttf"


def _set_korean_font():
    font_name = font_manager.FontProperties(fname=FONT_PATH).get_name()
    rc('font', family=font_name)
    plt.rcParams['axes.unicode_minus'] = False


def render_header():
    st.title("🧴 무신사 뷰티 리뷰 감성분석")
    st.caption("크롤링한 23만 건의 리뷰 데이터와 학습된 LSTM 모델을 활용한 서비스입니다.")


def render_sidebar() -> str:
    with st.sidebar:
        st.header("📌 메뉴")
        page = st.radio(
            "페이지 선택",
            ["전체 통계", "상품별 리뷰", "실시간 감성 예측"],
        )
    return page


def render_overview_page(df):
    st.subheader("📊 전체 데이터 통계")
    st.write(f"전체 리뷰 수: **{len(df):,}건**")

    _set_korean_font()

    col1, col2 = st.columns(2)

    with col1:
        st.write("#### 감성 분포")
        dist = su.sentiment_distribution(df)
        colors = {'긍정': '#2ecc71', '중립': '#f0ad4e', '부정': '#d9534f'}
        fig, ax = plt.subplots(figsize=(3, 2.2))
        ax.bar(dist.index, dist.values, color=[colors.get(k, '#999') for k in dist.index])
        ax.set_ylabel('리뷰 수', fontsize=8)
        ax.tick_params(labelsize=7)
        fig.tight_layout()
        st.pyplot(fig, use_container_width=False)

    with col2:
        st.write("#### 평점 분포")
        rating_counts = df['rating'].value_counts().sort_index()
        fig, ax = plt.subplots(figsize=(3, 2.2))
        ax.bar(rating_counts.index.astype(str), rating_counts.values, color='#4C72B0')
        ax.set_xlabel('평점', fontsize=8)
        ax.set_ylabel('리뷰 수', fontsize=8)
        ax.tick_params(labelsize=7)
        fig.tight_layout()
        st.pyplot(fig, use_container_width=False)

    st.write("#### 리뷰 키워드 Top 20")
    with st.spinner("키워드 분석 중..."):
        top20 = su.top_keywords(df, 20)
    if top20:
        labels, counts = zip(*top20)
        kw_col, _ = st.columns([1, 1])
        with kw_col:
            fig, ax = plt.subplots(figsize=(4, 4.5))
            ax.barh(list(reversed(labels)), list(reversed(counts)), color='#9B59B6')
            ax.set_xlabel('빈도수', fontsize=8)
            ax.tick_params(labelsize=7)
            fig.tight_layout()
            st.pyplot(fig, use_container_width=False)


def render_product_page(df):
    st.subheader("🔍 상품별 리뷰 탐색")

    products = su.get_product_list(df)
    selected = st.selectbox("상품 선택", products)

    product_df = su.get_product_reviews(df, selected)

    col1, col2, col3 = st.columns(3)
    col1.metric("리뷰 수", f"{len(product_df):,}건")
    col2.metric("평균 평점", f"{product_df['rating'].mean():.1f}점")
    pos_ratio = (product_df['sentiment'] == '긍정').mean() * 100
    col3.metric("긍정 비율", f"{pos_ratio:.1f}%")

    _set_korean_font()
    st.write("#### 감성 분포")
    dist = product_df['sentiment'].value_counts()
    colors = {'긍정': '#2ecc71', '중립': '#f0ad4e', '부정': '#d9534f'}
    chart_col, _ = st.columns([1, 2])
    with chart_col:
        fig, ax = plt.subplots(figsize=(3, 2.2))
        ax.bar(dist.index, dist.values, color=[colors.get(k, '#999') for k in dist.index])
        ax.tick_params(labelsize=8)
        fig.tight_layout()
        st.pyplot(fig, use_container_width=False)

    st.write("#### 리뷰 목록")

    def highlight_sentiment(row):
        color_map = {'긍정': 'color: #2ecc71',
                     '중립': 'color: #999999',
                     '부정': 'color: #e74c3c'}
        return [color_map.get(row['sentiment'], '')] * len(row)

    display_df = product_df[['rating', 'sentiment', 'review_text']].reset_index(drop=True)
    st.dataframe(
        display_df.style.apply(highlight_sentiment, axis=1),
        use_container_width=True,
    )


def render_predict_page(model, tokenizer):
    st.subheader("✍️ 실시간 감성 예측")
    st.write("리뷰 문장을 입력하면 학습된 모델이 긍정/부정을 판단합니다.")

    text = st.text_area("리뷰 입력", placeholder="예) 촉촉하고 흡수도 빨라서 너무 좋아요!")
    run_btn = st.button("🚀 분석하기")

    if run_btn:
        if not text.strip():
            st.warning("리뷰 문장을 입력해주세요.")
            return

        try:
            with st.spinner("분석 중..."):
                label, prob = su.predict_sentiment(text, model, tokenizer)

            if label == '긍정':
                st.success(f"결과: **긍정** ({prob*100:.1f}%)")
            else:
                st.error(f"결과: **부정** ({prob*100:.1f}%)")
            st.progress(prob)
        except Exception as e:
            st.error(f"⚠️ 분석 중 오류가 발생했습니다: {e}")

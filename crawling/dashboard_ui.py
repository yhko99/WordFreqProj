"""
무신사 뷰티 리뷰 감성분석 - Streamlit UI 렌더링 함수 모음
"""
import os
import random

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
    st.title("🧴 화장품 리뷰 구매 가이드 서비스")
    st.caption(
        "무신사·올리브영·쿠팡 리뷰 53만여 건으로 학습한 AI 모델이, "
        "상품의 리뷰를 분석해서 \"살지 말지\" 바로 판단할 수 있게 도와줍니다."
    )


def render_sidebar() -> tuple:
    with st.sidebar:
        st.header("📌 메뉴")
        page = st.radio(
            "페이지 선택",
            ["전체 통계", "상품 구매 가이드", "실시간 감성 예측"],
        )
        st.markdown("---")
        st.header("🧠 모델 선택")
        model_name = st.radio(
            "감성 예측에 쓸 신경망 구조",
            ["LSTM", "GRU", "Transformer"],
            help="동일한 데이터로 학습한 3가지 아키텍처 중 선택. '실시간 감성 예측' 페이지에서 적용됩니다.",
        )
    return page, model_name


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
    st.subheader("🛒 상품 구매 가이드")
    st.caption("상품을 검색하면 리뷰를 분석해서 구매 추천 여부, 장단점을 바로 보여줍니다.")

    products = su.get_product_list(df)
    selected = st.selectbox("상품 검색 (이름 일부만 입력해도 찾을 수 있어요)", products)

    product_df = su.get_product_reviews(df, selected)
    pos_ratio = (product_df['sentiment'] == '긍정').mean() * 100

    # ── 구매 추천 배지 ──────────────────────────────────────
    verdict = su.get_verdict(pos_ratio)
    st.markdown(
        f"""
        <div style="background-color:{verdict['color']}22; border-left:6px solid {verdict['color']};
                    border-radius:8px; padding:16px 20px; margin-bottom:12px;">
            <span style="font-size:26px; font-weight:700; color:{verdict['color']};">
                {verdict['emoji']} {verdict['label']}
            </span>
            <div style="margin-top:6px; font-size:15px;">{verdict['desc']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns(3)
    col1.metric("리뷰 수", f"{len(product_df):,}건")
    col2.metric("평균 평점", f"{product_df['rating'].mean():.1f}점")
    col3.metric("긍정 비율", f"{pos_ratio:.1f}%")

    # ── 장점 / 단점 키워드 ────────────────────────────────────
    st.write("#### 이 상품의 장점·단점")
    pro_col, con_col = st.columns(2)
    with pro_col:
        st.markdown("**👍 장점 (긍정 리뷰 키워드)**")
        pros = su.top_keywords_for_sentiment(product_df, '긍정', 6)
        if pros:
            st.markdown(" ".join(f"`{w}`" for w, _ in pros))
        else:
            st.caption("긍정 리뷰가 충분하지 않습니다.")
        pos_quote = su.get_representative_review(product_df, '긍정')
        if pos_quote:
            st.markdown(f"> 💬 *\"{pos_quote}\"*")

    with con_col:
        st.markdown("**👎 단점 (부정 리뷰 키워드)**")
        cons = su.top_keywords_for_sentiment(product_df, '부정', 6)
        if cons:
            st.markdown(" ".join(f"`{w}`" for w, _ in cons))
        else:
            st.caption("부정 리뷰가 충분하지 않습니다.")
        neg_quote = su.get_representative_review(product_df, '부정')
        if neg_quote:
            st.markdown(f"> 💬 *\"{neg_quote}\"*")

    st.divider()

    # ── 상세 데이터 (참고용) ──────────────────────────────────
    _set_korean_font()
    with st.expander("📊 감성 분포 차트 / 전체 리뷰 목록 보기"):
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


def render_predict_page(model, tokenizer, model_name, metrics):
    st.subheader("✍️ 실시간 감성 예측")
    st.write(f"리뷰 문장을 입력하면 **{model_name}** 모델이 긍정/부정을 판단합니다.")

    m = metrics.get(model_name, {})
    if m:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("정확도", f"{m['test_accuracy']*100:.1f}%")
        c2.metric("부정 F1", f"{m['negative_f1']*100:.1f}%")
        c3.metric("학습시간", f"{m['train_time_sec']:.0f}초")
        c4.metric("파라미터", f"{m['params']:,}")
    st.divider()

    if "predict_text" not in st.session_state:
        st.session_state.predict_text = ""

    def _pick_other(options, current):
        """현재 텍스트와 다른 걸 무작위로 골라서, 클릭마다 예시가 바뀌게 함"""
        choices = [o for o in options if o != current] or options
        return random.choice(choices)

    def _set_pos():
        st.session_state.predict_text = _pick_other(su.EXAMPLE_POSITIVES, st.session_state.predict_text)

    def _set_neg():
        st.session_state.predict_text = _pick_other(su.EXAMPLE_NEGATIVES, st.session_state.predict_text)

    ex_col1, ex_col2 = st.columns(2)
    ex_col1.button("👍 긍정 예시 넣기", on_click=_set_pos, use_container_width=True)
    ex_col2.button("👎 부정 예시 넣기", on_click=_set_neg, use_container_width=True)

    text = st.text_area(
        "리뷰 입력", key="predict_text",
        placeholder="예) 촉촉하고 흡수도 빨라서 너무 좋아요!",
    )
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

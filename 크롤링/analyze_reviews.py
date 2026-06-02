"""
무신사 뷰티 리뷰 분석 스크립트
크롤링 완료 후 실행: python analyze_reviews.py

생성 파일:
    data/musinsa_bulk/chart_keywords.png  - 키워드 빈도 막대 그래프
    data/musinsa_bulk/chart_wordcloud.png - 워드클라우드
    data/musinsa_bulk/chart_rating.png    - 평점 분포
    data/musinsa_bulk/chart_skintone.png  - 피부톤별 리뷰 수
"""

import re
from collections import Counter
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from wordcloud import WordCloud

# ── 경로 설정 ──────────────────────────────────────────
DATA_PATH = "./data/musinsa_bulk/musinsa_beauty_ALL.csv"
OUT_DIR   = Path("./data/musinsa_bulk")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ── 한글 폰트 (Windows 기본) ───────────────────────────
FONT_PATH = "C:/Windows/Fonts/malgun.ttf"
plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False

# ── 불용어 ─────────────────────────────────────────────
STOPWORDS = {
    "있다", "하다", "이다", "같다", "되다", "없다", "그리고", "그런데",
    "하지만", "그냥", "정말", "너무", "진짜", "좋다", "사용", "제품",
    "구매", "느낌", "것같", "것도", "근데", "이번", "이제", "있어",
    "해서", "이거", "그게", "거라", "하고", "이런", "저는", "에서",
    "으로", "에도", "부터", "까지", "이라", "해요", "해서", "했어",
    "했는데", "합니다", "입니다", "같아요", "좋아요", "봤는데",
}

# ══════════════════════════════════════════════════════
print("데이터 로딩 중...")
df = pd.read_csv(DATA_PATH, encoding="utf-8-sig")
print(f"총 {len(df):,}건 로드 완료")
print(f"브랜드 수: {df['brand_name'].nunique()}개")
print(f"상품 수:   {df['product_id'].nunique()}개")

# ── 1. 키워드 빈도 막대 그래프 ─────────────────────────
print("\n키워드 빈도 분석 중...")
all_text = " ".join(df["review_text"].dropna().astype(str))
words    = re.findall(r"[가-힣]{2,5}", all_text)
words    = [w for w in words if w not in STOPWORDS]
top30    = Counter(words).most_common(30)
labels, counts = zip(*top30)

fig, ax = plt.subplots(figsize=(9, 10))
bars = ax.barh(list(reversed(labels)), list(reversed(counts)),
               color="#4C72B0")
ax.set_title("무신사 뷰티 리뷰 키워드 Top 30", fontsize=15, pad=12)
ax.set_xlabel("빈도수", fontsize=11)
ax.bar_label(bars, padding=3, fontsize=8)
plt.tight_layout()
out = OUT_DIR / "chart_keywords.png"
plt.savefig(out, dpi=150, bbox_inches="tight")
plt.close()
print(f"저장: {out}")

# ── 2. 워드클라우드 ────────────────────────────────────
print("워드클라우드 생성 중...")
word_freq = dict(Counter(words).most_common(200))
wc = WordCloud(
    font_path=FONT_PATH,
    width=800, height=500,
    background_color="white",
    colormap="Set2",
    max_words=150,
    max_font_size=120,
    min_font_size=10,
    random_state=42,
).generate_from_frequencies(word_freq)

fig, ax = plt.subplots(figsize=(12, 7))
ax.imshow(wc, interpolation="bilinear")
ax.axis("off")
ax.set_title("무신사 뷰티 리뷰 워드클라우드", fontsize=15, pad=12)
plt.tight_layout()
out = OUT_DIR / "chart_wordcloud.png"
plt.savefig(out, dpi=150, bbox_inches="tight")
plt.close()
print(f"저장: {out}")

# ── 3. 평점 분포 ───────────────────────────────────────
print("평점 분포 차트 생성 중...")
rating_counts = df["rating"].value_counts().sort_index()
colors = ["#d9534f", "#f0ad4e", "#f0ad4e", "#5cb85c", "#2ecc71"]

fig, ax = plt.subplots(figsize=(7, 5))
bars = ax.bar(rating_counts.index.astype(str), rating_counts.values,
              color=colors[:len(rating_counts)], edgecolor="white", width=0.6)
ax.set_title("평점 분포", fontsize=14, pad=10)
ax.set_xlabel("평점 (별점)", fontsize=11)
ax.set_ylabel("리뷰 수", fontsize=11)
ax.bar_label(bars, fmt="%,.0f", padding=3, fontsize=9)
plt.tight_layout()
out = OUT_DIR / "chart_rating.png"
plt.savefig(out, dpi=150, bbox_inches="tight")
plt.close()
print(f"저장: {out}")

# ── 4. 피부톤별 리뷰 수 ────────────────────────────────
if "skin_tone" in df.columns:
    print("피부톤 분포 차트 생성 중...")
    tone = (df["skin_tone"]
            .replace("", pd.NA)
            .dropna()
            .value_counts()
            .head(10))

    fig, ax = plt.subplots(figsize=(9, 5))
    bars = ax.bar(tone.index, tone.values, color="#9B59B6", edgecolor="white", width=0.6)
    ax.set_title("피부톤별 리뷰 수 Top 10", fontsize=14, pad=10)
    ax.set_xlabel("피부톤", fontsize=11)
    ax.set_ylabel("리뷰 수", fontsize=11)
    ax.bar_label(bars, fmt="%,.0f", padding=3, fontsize=9)
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()
    out = OUT_DIR / "chart_skintone.png"
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"저장: {out}")

print("\n=== 완료 ===")
print(f"차트 저장 위치: {OUT_DIR.resolve()}")

"""
무신사(우리) + 올리브영(팀원) + 쿠팡(팀원) 리뷰 데이터 병합

기존 무신사 데이터는 평점 불균형(부정 0.4%)이 심해 키워드 기반으로
긍/부정을 추정했는데, 이 방식이 오탐(긍정인데 부정 키워드 매칭 등)이 많았다.
팀원 데이터(올리브영/쿠팡)는 실제 평점 기준 부정 비율이 8~17%로 충분히 높아서,
3개 플랫폼을 합쳐 "실제 평점" 기준으로 라벨링하면 키워드 오탐 문제를 없앨 수 있다.

라벨 기준: rating 1~2 = 부정(0), rating 4~5 = 긍정(1), rating 3은 제외(애매함)
무신사 비중이 너무 커서 그대로 합치면 부정 비율이 다시 희석되므로,
부정:긍정 = 1:3 비율이 되도록 긍정 클래스를 언더샘플링한다.
"""
import glob
import json
import os

import pandas as pd

RAW_DIR = "./external_raw"
OUT_PATH = "./beauty_reviews_merged.csv"
POS_NEG_RATIO = 3  # 긍정:부정 = 3:1 (부정 25%)
RANDOM_STATE = 42


def load_musinsa() -> pd.DataFrame:
    df = pd.read_csv("./musinsa_beauty_TOTAL.csv", encoding="utf-8-sig", low_memory=False,
                      usecols=["review_text", "rating", "product_name", "brand_name"])
    df["platform"] = "무신사"
    return df


def load_oliveyoung() -> pd.DataFrame:
    rows = []
    for path in glob.glob(os.path.join(RAW_DIR, "oliveyoung", "*.jsonl")):
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                d = json.loads(line)
                rows.append({
                    "review_text": d.get("review_text"),
                    "rating": d.get("rating"),
                    "product_name": d.get("product_name"),
                    "brand_name": d.get("brand"),
                })
    df = pd.DataFrame(rows)
    df["platform"] = "올리브영"
    return df


def load_coupang() -> pd.DataFrame:
    files = glob.glob(os.path.join(RAW_DIR, "coupang", "*.csv"))
    dfs = [pd.read_csv(f, encoding="utf-8-sig", low_memory=False) for f in files]
    df = pd.concat(dfs, ignore_index=True)
    df = df.drop_duplicates(subset=["review_id"])
    df = df.rename(columns={"review_content": "review_text"})
    df["brand_name"] = ""
    df = df[["review_text", "rating", "product_name", "brand_name"]]
    df["platform"] = "쿠팡"
    return df


def label_by_rating(df: pd.DataFrame) -> pd.DataFrame:
    df = df.dropna(subset=["review_text", "rating"]).copy()
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
    df = df.dropna(subset=["rating"])
    df = df[df["rating"] != 3]  # 애매한 3점 제외
    df["label"] = (df["rating"] >= 4).astype(int)  # 1=긍정, 0=부정
    df["product_name"] = df["product_name"].fillna("(상품명 없음)")
    df["brand_name"] = df["brand_name"].fillna("")
    return df


def main():
    print("데이터 로딩 중...")
    musinsa = label_by_rating(load_musinsa())
    print(f"  무신사: {len(musinsa):,}건 (부정 {(musinsa['label']==0).sum():,} / 긍정 {(musinsa['label']==1).sum():,})")

    olive = label_by_rating(load_oliveyoung())
    print(f"  올리브영: {len(olive):,}건 (부정 {(olive['label']==0).sum():,} / 긍정 {(olive['label']==1).sum():,})")

    coupang = label_by_rating(load_coupang())
    print(f"  쿠팡: {len(coupang):,}건 (부정 {(coupang['label']==0).sum():,} / 긍정 {(coupang['label']==1).sum():,})")

    merged = pd.concat([musinsa, olive, coupang], ignore_index=True)
    merged = merged[["platform", "product_name", "brand_name", "review_text", "rating", "label"]]

    neg = merged[merged["label"] == 0]
    pos = merged[merged["label"] == 1]
    print(f"\n병합 전체: 부정 {len(neg):,}건 / 긍정 {len(pos):,}건")

    # 긍정 언더샘플링 (부정:긍정 = 1:POS_NEG_RATIO)
    target_pos_n = min(len(pos), len(neg) * POS_NEG_RATIO)
    pos_sampled = pos.sample(n=target_pos_n, random_state=RANDOM_STATE)

    final = pd.concat([neg, pos_sampled], ignore_index=True).sample(frac=1, random_state=RANDOM_STATE)
    final.reset_index(drop=True, inplace=True)

    print(f"\n최종 데이터셋: {len(final):,}건")
    print(final["label"].value_counts().rename({0: "부정", 1: "긍정"}))
    print(f"부정 비율: {(final['label']==0).mean()*100:.1f}%")
    print("\n플랫폼별 분포:")
    print(final["platform"].value_counts())

    final.to_csv(OUT_PATH, index=False, encoding="utf-8-sig")
    print(f"\n저장 완료: {OUT_PATH}")


if __name__ == "__main__":
    main()

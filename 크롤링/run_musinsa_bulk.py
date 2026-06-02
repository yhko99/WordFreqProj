"""
무신사 뷰티 리뷰 대량 수집 스크립트 (목표: 30만 건)
주말 무인 장시간 실행 대응 버전

실행:
    python run_musinsa_bulk.py

중단 후 이어 실행:
    그냥 다시 python run_musinsa_bulk.py 실행하면 됨
    (완료된 키워드·상품은 자동 건너뜀)
"""

import os
import json
import logging
import traceback
from datetime import datetime

import pandas as pd

from musinsa_beauty_crawler import MusinsaBeautyCrawler


# ══════════════════════════════════════════════════════════════
#  ★ 수집 설정 (여기만 수정)
# ══════════════════════════════════════════════════════════════

KEYWORDS = [
    # 선케어
    "선크림", "선스틱", "선세럼", "선로션", "선패드", "톤업크림",
    "자외선차단제", "선밀크", "선젤", "선쿠션", "선에센스",
    "선워터", "선글로우", "UV차단크림", "선케어",

    # 바디케어
    "바디로션", "바디오일", "바디크림", "바디워시", "바디스크럽",
    "핸드크림", "핸드워시", "바디미스트", "바디버터", "바디밤",
    "풋크림", "풋케어", "핸드로션", "바디팩", "튼살크림",
    "바디필링", "네일오일", "바디젤",

    # 헤어케어
    "샴푸", "트리트먼트", "헤어오일", "헤어에센스", "헤어팩", "두피토너",
    "헤어세럼", "헤어미스트", "두피앰플", "탈모샴푸", "두피샴푸",
    "린스", "헤어크림", "헤어워터", "드라이샴푸",
    "볼륨샴푸", "손상모발샴푸", "헤어스프레이",
]

SEARCH_PAGES_PER_KEYWORD = 10   # 키워드당 검색 페이지 수 (1페이지 ≈ 30개)
MAX_REVIEWS_PER_PRODUCT  = None # None = 해당 상품 전체 리뷰 수집
BROWSER_RESTART_EVERY    = 40   # N개 상품마다 브라우저 재시작
SAVE_DIR                 = "./data/beauty_v2"


# ══════════════════════════════════════════════════════════════
#  로그 설정
# ══════════════════════════════════════════════════════════════

def setup_logger(log_dir: str) -> logging.Logger:
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"crawl_{datetime.now().strftime('%m%d_%H%M')}.log")

    logger = logging.getLogger("musinsa")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s",
                            datefmt="%Y-%m-%d %H:%M:%S")

    # 파일 핸들러 (로그 파일로 저장)
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    # 콘솔 핸들러 (터미널 출력)
    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    logger.info(f"로그 파일: {log_file}")
    return logger


# ══════════════════════════════════════════════════════════════
#  체크포인트 (중단 후 이어 수집)
# ══════════════════════════════════════════════════════════════

class Checkpoint:
    """
    수집 진행 상태를 JSON으로 저장/불러오기.
    - done_keywords : 완료된 키워드
    - done_products : 완료된 product_id 집합 (키워드 내 상품 단위)
    """

    def __init__(self, path: str):
        self.path = path
        self._data = self._load()

    def _load(self) -> dict:
        if os.path.exists(self.path):
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"done_keywords": [], "done_products": []}

    def save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    def is_keyword_done(self, keyword: str) -> bool:
        return keyword in self._data["done_keywords"]

    def mark_keyword_done(self, keyword: str):
        if keyword not in self._data["done_keywords"]:
            self._data["done_keywords"].append(keyword)
        self.save()

    def get_done_products(self) -> set[str]:
        return set(self._data["done_products"])

    def mark_products_done(self, product_ids: list[str]):
        existing = set(self._data["done_products"])
        existing.update(product_ids)
        self._data["done_products"] = list(existing)
        self.save()


# ══════════════════════════════════════════════════════════════
#  전체 CSV 병합
# ══════════════════════════════════════════════════════════════

def merge_all(save_dir: str, logger: logging.Logger) -> str:
    files = [f for f in os.listdir(save_dir)
             if f.endswith("_reviews.csv")]
    if not files:
        logger.info("병합할 파일 없음")
        return ""

    dfs = []
    for f in files:
        try:
            dfs.append(pd.read_csv(os.path.join(save_dir, f), encoding="utf-8-sig"))
        except Exception as e:
            logger.warning(f"파일 읽기 실패: {f} → {e}")

    if not dfs:
        return ""

    merged = pd.concat(dfs, ignore_index=True)
    merged.drop_duplicates(
        subset=["product_id", "nickname", "date"],
        inplace=True
    )
    out_path = os.path.join(save_dir, "musinsa_beauty_ALL.csv")
    merged.to_csv(out_path, index=False, encoding="utf-8-sig")
    logger.info(f"전체 병합 완료: {out_path} ({len(merged):,}건)")
    return out_path


# ══════════════════════════════════════════════════════════════
#  메인
# ══════════════════════════════════════════════════════════════

def main():
    os.makedirs(SAVE_DIR, exist_ok=True)
    logger     = setup_logger(SAVE_DIR)
    checkpoint = Checkpoint(os.path.join(SAVE_DIR, "checkpoint.json"))

    logger.info("=" * 60)
    logger.info("무신사 뷰티 리뷰 대량 수집 시작")
    logger.info(f"키워드 {len(KEYWORDS)}개 / 페이지당 {SEARCH_PAGES_PER_KEYWORD}페이지")
    logger.info("=" * 60)

    crawler = MusinsaBeautyCrawler(
        headless=True,               # 장시간 실행 → 헤드리스
        save_interval=300,
        min_delay=2.0,
        max_delay=4.5,
        logger=logger,
    )

    total_collected = 0

    try:
        for keyword in KEYWORDS:
            logger.info(f"\n{'─'*50}")
            logger.info(f"키워드 시작: [{keyword}]")

            # 이미 완료된 키워드 건너뜀
            if checkpoint.is_keyword_done(keyword):
                logger.info(f"  → 이미 완료됨, 건너뜀")
                save_file = os.path.join(SAVE_DIR, f"{keyword}_reviews.csv")
                if os.path.exists(save_file):
                    total_collected += len(pd.read_csv(save_file))
                continue

            save_file    = os.path.join(SAVE_DIR, f"{keyword}_reviews.csv")
            autosave_file= os.path.join(SAVE_DIR, f"{keyword}_autosave.csv")

            try:
                # 1) 상품 URL 수집
                urls = crawler.get_product_urls(keyword, SEARCH_PAGES_PER_KEYWORD)
                if not urls:
                    logger.warning(f"  → 상품 없음, 건너뜀")
                    checkpoint.mark_keyword_done(keyword)
                    continue

                # 2) 이미 완료된 상품 제외
                done_products = checkpoint.get_done_products()

                # 3) 리뷰 수집
                df = crawler.crawl_all(
                    product_urls=urls,
                    max_reviews_per_product=MAX_REVIEWS_PER_PRODUCT,
                    autosave_path=autosave_file,
                    browser_restart_every=BROWSER_RESTART_EVERY,
                    done_ids=done_products,
                )

                # 4) 저장
                if not df.empty:
                    # 이전에 부분 저장된 파일이 있으면 합치기
                    if os.path.exists(save_file):
                        try:
                            prev = pd.read_csv(save_file, encoding="utf-8-sig")
                            df   = pd.concat([prev, df], ignore_index=True)
                            df.drop_duplicates(
                                subset=["product_id", "nickname", "date"],
                                inplace=True
                            )
                        except Exception:
                            pass

                    df.to_csv(save_file, index=False, encoding="utf-8-sig")
                    total_collected += len(df)
                    logger.info(
                        f"  → '{keyword}' 완료: {len(df):,}건 저장 | "
                        f"전체 누적: {total_collected:,}건"
                    )

                    # 완료 상품 체크포인트 기록
                    done_ids = [
                        crawler._product_meta.get(u, {}).get("product_id", "")
                        for u in urls
                    ]
                    checkpoint.mark_products_done([i for i in done_ids if i])

                # autosave 파일 삭제 (정상 완료)
                if os.path.exists(autosave_file):
                    os.remove(autosave_file)

                checkpoint.mark_keyword_done(keyword)

            except KeyboardInterrupt:
                logger.info("사용자 중단 (KeyboardInterrupt)")
                raise

            except Exception as e:
                logger.error(f"키워드 '{keyword}' 처리 중 오류: {e}")
                logger.error(traceback.format_exc())
                logger.info("→ 다음 키워드로 계속 진행")
                # 오류 나도 다음 키워드로 계속 진행 (중단 안 함)
                continue

    except KeyboardInterrupt:
        logger.info("수집 중단됨 — 다음 실행 시 이어서 수집됩니다.")

    finally:
        crawler.quit()

        # 최종 병합
        logger.info("\n전체 CSV 병합 중...")
        out = merge_all(SAVE_DIR, logger)

        logger.info("=" * 60)
        logger.info(f"최종 누적 수집: {total_collected:,}건")
        if out:
            logger.info(f"최종 파일: {out}")
        logger.info("=" * 60)


if __name__ == "__main__":
    main()

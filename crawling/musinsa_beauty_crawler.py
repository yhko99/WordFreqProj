"""
MusinsaBeautyCrawler - 무신사 뷰티 리뷰 대량 수집기
주말 장시간 무인 실행 대응 버전

필수 설치:
    pip install selenium webdriver-manager beautifulsoup4 pandas tqdm
"""

import time
import random
import re
import os
import logging
from datetime import datetime

import pandas as pd
from tqdm import tqdm
from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, WebDriverException
)
from webdriver_manager.chrome import ChromeDriverManager


# ─────────────────────────────────────────────────────────────
#  셀렉터 (사이트 구조 바뀌면 여기만 수정)
# ─────────────────────────────────────────────────────────────
class _SEL:
    PRODUCT_CARD    = "a[data-item-id]"
    REVIEW_ALL_TAB  = "[class*='GoodsReviewTabGroup__TabItem']"
    REVIEW_ITEM     = "[class*='review-list-item__Container']"
    NICKNAME        = "[class*='UserProfileSection__Nickname']"
    PURCHASE_DATE   = "[class*='UserProfileSection__PurchaseDate']"
    STARS_CONTAINER = "[class*='StarsScore__Container']"
    FILLED_STAR     = "path.fill-yellow"
    OPTION_SECTION  = "[class*='GoodsOptionProfileSection__Container']"
    OPTION_ROW      = "[class*='OptionRow__Container']"
    REVIEW_CONTENT  = "[class*='ReviewImageContentSection__Container']"
    HELPFUL_BTN     = "button[class*='HelpButton__Button']"
    PREV_BTN        = "a[class*='ShowPreviousReviewButton__Container']"


class MusinsaBeautyCrawler:
    """
    무신사 뷰티 리뷰 크롤러 (장시간 무인 실행 대응)

    사용 예시:
        crawler = MusinsaBeautyCrawler(headless=True)
        urls = crawler.get_product_urls("토너", max_pages=5)
        df   = crawler.crawl_all(urls)
        crawler.save_to_csv(df, "./data/토너_reviews.csv")
        crawler.quit()
    """

    BASE_URL   = "https://www.musinsa.com"
    SEARCH_URL = (
        "https://www.musinsa.com/search/goods"
        "?keyword={keyword}&category_code=&display_cnt=90&sub_sort=SALE_SCORE&page={page}"
    )

    def __init__(self, headless: bool = True, save_interval: int = 300,
                 min_delay: float = 2.0, max_delay: float = 4.0,
                 logger: logging.Logger = None):
        self.headless      = headless
        self.save_interval = save_interval
        self.min_delay     = min_delay
        self.max_delay     = max_delay
        self.log           = logger or logging.getLogger(__name__)
        self._product_meta: dict[str, dict] = {}
        self._all_reviews:  list[dict] = []

        self.driver = self._init_driver()
        self.wait   = WebDriverWait(self.driver, 15)
        self.log.info(f"브라우저 초기화 완료 (headless={headless})")

    # ──────────────────────────────────────────────────────
    #  브라우저
    # ──────────────────────────────────────────────────────
    def _init_driver(self) -> webdriver.Chrome:
        options = Options()
        if self.headless:
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1280,900")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        service = Service(ChromeDriverManager().install())
        driver  = webdriver.Chrome(service=service, options=options)
        driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        driver.set_page_load_timeout(30)
        return driver

    def restart_browser(self):
        """브라우저 재시작 (메모리 누수 방지용, 장시간 실행 시 주기적 호출)"""
        try:
            self.driver.quit()
        except Exception:
            pass
        time.sleep(3)
        self.driver = self._init_driver()
        self.wait   = WebDriverWait(self.driver, 15)
        self.log.info("브라우저 재시작 완료")

    # ──────────────────────────────────────────────────────
    #  내부 유틸
    # ──────────────────────────────────────────────────────
    def _sleep(self):
        time.sleep(random.uniform(self.min_delay, self.max_delay))

    def _scroll_down(self, times: int = 3, interval: float = 1.2):
        """지연 로드 트리거용 스크롤"""
        for _ in range(times):
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(interval)

    def _safe_get(self, url: str, wait_sel: str = None,
                  timeout: int = 15, retries: int = 3) -> BeautifulSoup | None:
        """페이지 로드 + 재시도 포함. 실패 시 None 반환."""
        for attempt in range(1, retries + 1):
            try:
                self.driver.get(url)
                if wait_sel:
                    WebDriverWait(self.driver, timeout).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, wait_sel))
                    )
                self._sleep()
                return BeautifulSoup(self.driver.page_source, "html.parser")
            except TimeoutException:
                self.log.warning(f"  로딩 타임아웃 ({attempt}/{retries}): {url[:60]}")
                if attempt == retries:
                    return BeautifulSoup(self.driver.page_source, "html.parser")
                time.sleep(3 * attempt)
            except WebDriverException as e:
                self.log.warning(f"  브라우저 오류 ({attempt}/{retries}): {e}")
                if attempt == retries:
                    return None
                self.restart_browser()
                time.sleep(5)
            except Exception as e:
                self.log.warning(f"  예외 ({attempt}/{retries}): {e}")
                if attempt == retries:
                    return None
                time.sleep(3 * attempt)
        return None

    # ──────────────────────────────────────────────────────
    #  1단계: 상품 URL 수집
    # ──────────────────────────────────────────────────────
    def get_product_urls(self, keyword: str, max_pages: int = 5) -> list[str]:
        """
        키워드 검색으로 상품 URL 목록 수집.
        검색 결과 data 속성에서 브랜드·가격·상품명도 함께 추출.
        """
        urls: list[str] = []
        self._product_meta = {}
        self.log.info(f"상품 검색 시작: '{keyword}' / {max_pages}페이지")

        for page in range(1, max_pages + 1):
            url  = self.SEARCH_URL.format(keyword=keyword.replace(" ", "+"), page=page)
            soup = self._safe_get(url, wait_sel=_SEL.PRODUCT_CARD, timeout=15)
            if not soup:
                self.log.warning(f"  p{page}: 페이지 로드 실패 → 건너뜀")
                continue

            cards = soup.select(_SEL.PRODUCT_CARD)
            if not cards:
                self.log.info(f"  p{page}: 상품 없음 → 검색 종료")
                break

            new = 0
            for card in cards:
                href = card.get("href", "")
                if not href:
                    continue
                if href.startswith("/"):
                    href = self.BASE_URL + href
                if href in self._product_meta:
                    continue

                img = card.select_one("img[alt]")
                self._product_meta[href] = {
                    "product_id"    : card.get("data-item-id", ""),
                    "product_name"  : img["alt"] if img else "",
                    "brand_name"    : card.get("data-item-brand", ""),
                    "price"         : card.get("data-price", ""),
                    "original_price": card.get("data-original-price", ""),
                    "discount_rate" : card.get("data-discount-rate", ""),
                    "product_url"   : href,
                }
                urls.append(href)
                new += 1

            self.log.info(f"  p{page}: {new}개 수집 (누적 {len(urls)}개)")
            if new == 0:
                break

        self.log.info(f"상품 수집 완료: 총 {len(urls)}개")
        return urls

    # ──────────────────────────────────────────────────────
    #  2단계: 리뷰 1건 파싱
    # ──────────────────────────────────────────────────────
    def _parse_one_review(self, item: BeautifulSoup, product_info: dict) -> dict | None:
        try:
            nick_el  = item.select_one(_SEL.NICKNAME)
            nickname = (nick_el.get("title") or nick_el.get_text(strip=True)) if nick_el else ""

            date_el = item.select_one(_SEL.PURCHASE_DATE)
            date    = date_el.get_text(strip=True) if date_el else ""

            star_el = item.select_one(_SEL.STARS_CONTAINER)
            rating  = str(len(star_el.select(_SEL.FILLED_STAR))) if star_el else ""

            option_vals: dict[str, str] = {}
            opt_section = item.select_one(_SEL.OPTION_SECTION)
            if opt_section:
                for row in opt_section.select(_SEL.OPTION_ROW):
                    spans = row.select("span[data-mds='Typography']")
                    if len(spans) >= 2:
                        option_vals[spans[0].get_text(strip=True)] = spans[1].get_text(strip=True)

            skin_raw     = option_vals.get("피부정보", "")
            skin_parts   = [s.strip() for s in skin_raw.split("·")]
            skin_tone    = skin_parts[0] if skin_parts else ""
            skin_type    = " · ".join(skin_parts[1:]) if len(skin_parts) > 1 else ""

            content_el  = item.select_one(_SEL.REVIEW_CONTENT)
            review_text = ""
            if content_el:
                # "이전 후기 보기" 버튼이 content 내부에 있으면 제거
                for el in content_el.select(_SEL.PREV_BTN):
                    el.decompose()
                for img_tag in content_el.select("img"):
                    img_tag.decompose()
                raw = content_el.get_text(separator=" ", strip=True)
                # 불필요한 텍스트 제거
                raw = re.sub(r"이전\s*후기\s*보기", "", raw)
                raw = re.sub(r"\s*(더보기|한달후기|&nbsp;)\s*", " ", raw)
                raw = re.sub(r"\s{2,}", " ", raw).strip()
                # 말미 "..." 제거 (CSS truncation 잔재)
                raw = re.sub(r"\s*\.{2,}\s*$", "", raw).strip()
                # Musinsa는 collapse/expand 두 벌 DOM을 동시에 렌더링 → 텍스트 중복
                # 패턴1: "text ... text"  → " ... " 기준 분할
                if " ... " in raw:
                    parts = [p.strip() for p in raw.split(" ... ") if p.strip()]
                    raw = max(parts, key=len)
                else:
                    # 패턴2: "text text" (공백만으로 붙은 중복)
                    # 문자열 중간점 ±20자 범위에서 첫째 반쪽이 둘째 반쪽의 접두사인지 검사
                    n = len(raw)
                    if n >= 10:
                        for mid in range(max(5, n // 2 - 20), min(n - 5, n // 2 + 21)):
                            first  = raw[:mid].strip()
                            second = raw[mid:].strip()
                            if second.startswith(first) and len(first) > 5:
                                raw = first
                                break
                review_text = raw

            if not review_text:
                return None

            helpful_btn = item.select_one(_SEL.HELPFUL_BTN)
            helpful     = helpful_btn.get("data-like-count", "0") if helpful_btn else "0"

            return {
                **product_info,
                "nickname"       : nickname,
                "date"           : date,
                "rating"         : rating,
                "skin_tone"      : skin_tone,
                "skin_type"      : skin_type,
                "skin_raw"       : skin_raw,
                "satisfaction"   : option_vals.get("만족도", ""),
                "purchase_option": option_vals.get("구매옵션", ""),
                "review_text"    : review_text,
                "helpful"        : helpful,
                "crawled_at"     : datetime.now().strftime("%Y-%m-%d %H:%M"),
            }
        except Exception:
            return None

    REVIEW_LIST_URL = "https://www.musinsa.com/review/goods/{product_id}?sort=newest"

    # ──────────────────────────────────────────────────────
    #  3단계: 상품 1개 리뷰 수집 (무한 스크롤 방식)
    # ──────────────────────────────────────────────────────
    def crawl_reviews(self, product_url: str,
                      max_reviews_per_product: int | None = None) -> list[dict]:
        """
        review/goods/{id} 페이지에서 스크롤로 리뷰 무한 로드.
        스크롤 후 새 리뷰가 없으면 종료.
        """
        limit      = (max_reviews_per_product or 0) or float("inf")
        collected: list[dict] = []
        seen_ids:  set[str]   = set()

        product_info = self._product_meta.get(product_url, {
            "product_id"    : "",
            "product_name"  : "",
            "brand_name"    : "",
            "price"         : "",
            "original_price": "",
            "discount_rate" : "",
            "product_url"   : product_url,
        })
        product_id = product_info.get("product_id", "")
        if not product_id:
            m = re.search(r"/(\d+)", product_url)
            product_id = m.group(1) if m else ""
        if not product_id:
            self.log.warning(f"product_id 추출 실패: {product_url}")
            return []

        try:
            url  = self.REVIEW_LIST_URL.format(product_id=product_id)
            soup = self._safe_get(url, wait_sel=_SEL.REVIEW_ITEM, timeout=20)
            if not soup:
                return []

            stale = 0
            scroll_no = 0

            while len(collected) < limit and stale < 4:
                soup  = BeautifulSoup(self.driver.page_source, "html.parser")
                items = soup.select(_SEL.REVIEW_ITEM)

                new_count = 0
                for item in items:
                    cid = item.get("data-content-id", "")
                    if cid and cid in seen_ids:
                        continue
                    if cid:
                        seen_ids.add(cid)
                    review = self._parse_one_review(item, product_info)
                    if review:
                        collected.append(review)
                        new_count += 1
                        if len(collected) >= limit:
                            break

                if new_count > 0:
                    stale = 0
                    self.log.info(
                        f"  scroll {scroll_no}: +{new_count}건 (누적 {len(collected)}건)"
                    )
                else:
                    stale += 1

                if len(collected) >= limit:
                    break

                # 스크롤로 다음 배치 로드 유도
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2.5)
                scroll_no += 1

        except Exception as e:
            self.log.warning(f"crawl_reviews 오류 [{product_url[:50]}]: {e}")

        unique = {r["nickname"] + r["date"] + r.get("review_text", "")[:20]: r
                  for r in collected}
        result = list(unique.values())
        return result[:max_reviews_per_product] if max_reviews_per_product else result

    # ──────────────────────────────────────────────────────
    #  4단계: 전체 상품 순회 수집
    # ──────────────────────────────────────────────────────
    def crawl_all(self, product_urls: list[str],
                  max_reviews_per_product: int | None = None,
                  autosave_path: str = "./data/autosave.csv",
                  browser_restart_every: int = 50,
                  done_ids: set[str] = None) -> pd.DataFrame:
        """
        상품 URL 리스트 전체 순회 수집.

        Args:
            browser_restart_every : N개 상품마다 브라우저 재시작 (메모리 누수 방지)
            done_ids              : 이미 수집 완료한 product_id 집합 (이어 수집용)
        """
        done_ids = done_ids or set()
        self._all_reviews = []
        self.log.info(f"수집 시작: {len(product_urls)}개 상품 / 상품당 {max_reviews_per_product or '무제한'}건")

        for i, url in enumerate(tqdm(product_urls, desc="상품 진행"), start=1):
            pid = self._product_meta.get(url, {}).get("product_id", url)

            # 이미 처리한 상품 건너뜀
            if pid in done_ids:
                tqdm.write(f"  [{i}] SKIP (이미 수집됨): {pid}")
                continue

            reviews = self.crawl_reviews(url, max_reviews_per_product)
            self._all_reviews.extend(reviews)
            tqdm.write(
                f"  [{i}/{len(product_urls)}] {len(reviews)}건 → "
                f"누적 {len(self._all_reviews):,}건"
            )

            # 중간 저장
            if self._all_reviews and i % 10 == 0:
                self._autosave(autosave_path)

            # 브라우저 주기적 재시작
            if i % browser_restart_every == 0:
                self.log.info(f"[{i}] 브라우저 재시작 (메모리 관리)")
                self.restart_browser()

        self._autosave(autosave_path)
        df = pd.DataFrame(self._all_reviews)
        self.log.info(f"수집 완료: 총 {len(df):,}건")
        return df

    # ──────────────────────────────────────────────────────
    #  저장
    # ──────────────────────────────────────────────────────
    def _autosave(self, path: str):
        if not self._all_reviews:
            return
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
        pd.DataFrame(self._all_reviews).to_csv(path, index=False, encoding="utf-8-sig")
        self.log.info(f"자동저장: {path} ({len(self._all_reviews):,}건)")

    def save_to_csv(self, df: pd.DataFrame, filename: str):
        os.makedirs(os.path.dirname(filename) if os.path.dirname(filename) else ".", exist_ok=True)
        df.to_csv(filename, index=False, encoding="utf-8-sig")
        self.log.info(f"저장 완료: {filename} ({len(df):,}건)")

    def quit(self):
        try:
            self.driver.quit()
        except Exception:
            pass
        self.log.info("브라우저 종료")


# ══════════════════════════════════════════════════════════════
#  단일 키워드 테스트 실행
#  대량 수집은 run_musinsa_bulk.py 사용
# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import sys

    # ── 설정 ──────────────────────────────────────────────
    KEYWORD   = "토너"
    MAX_PAGES = 1          # 테스트: 1페이지만
    MAX_URLS  = 3          # 테스트: 상품 3개만
    MAX_REV   = 30         # 테스트: 상품당 30건
    SAVE_FILE = f"./data/{KEYWORD}_test.csv"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    crawler = MusinsaBeautyCrawler(
        headless=False,   # 테스트는 브라우저 보면서
        min_delay=2.0,
        max_delay=4.0,
    )

    try:
        urls = crawler.get_product_urls(KEYWORD, max_pages=MAX_PAGES)
        urls = urls[:MAX_URLS]
        print(f"\n→ 테스트 대상 {len(urls)}개 상품")

        if urls:
            df = crawler.crawl_all(
                product_urls=urls,
                max_reviews_per_product=MAX_REV,
                autosave_path="./data/test_autosave.csv",
                browser_restart_every=50,
            )
            crawler.save_to_csv(df, SAVE_FILE)

            if not df.empty:
                cols = [c for c in
                    ["brand_name", "product_name", "rating",
                     "skin_tone", "skin_type", "review_text"]
                    if c in df.columns]
                print("\n=== 수집 결과 미리보기 ===")
                print(df[cols].head(10).to_string().encode("utf-8", errors="replace").decode("utf-8"))
    finally:
        crawler.quit()

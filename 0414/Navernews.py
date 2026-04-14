"""
네이버 뉴스 크롤러 클래스
- 네이버 검색 API를 사용하여 뉴스 데이터 수집
- 노이즈 제거 기능 포함
- CSV 파일로 저장
"""

import os
import sys
import urllib.request
import urllib.parse
import json
import time
import pandas as pd
import re
from datetime import datetime


class NaverNewsCrawler:
    """
    네이버 뉴스 크롤러 클래스
    
    Attributes:
        client_id (str): 네이버 API Client ID
        client_secret (str): 네이버 API Client Secret
        keyword (str): 검색 키워드
        display (int): 한 번에 가져올 결과 개수 (기본값: 10)
        max_results (int): 최대 수집할 결과 개수 (기본값: 1000)
    """
    
    def __init__(self, client_id, client_secret, keyword, display=10, max_results=1000):
        """
        NaverNewsCrawler 초기화
        
        Args:
            client_id (str): 네이버 API Client ID
            client_secret (str): 네이버 API Client Secret
            keyword (str): 검색 키워드
            display (int, optional): 한 번에 가져올 결과 개수. Defaults to 10.
            max_results (int, optional): 최대 수집할 결과 개수. Defaults to 1000.
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.keyword = keyword
        self.display = display
        self.max_results = max_results
        self.result_list = []
        
    
    def crawl_news(self, start):
        """
        특정 위치부터 뉴스 검색 API 호출
        
        Args:
            start (int): 검색 시작 위치
            
        Returns:
            dict: API 응답 데이터 (JSON 형식), 실패 시 None
        """
        try:
            # 키워드 URL 인코딩
            enc_text = urllib.parse.quote(self.keyword)
            url = f"https://openapi.naver.com/v1/search/news?query={enc_text}"
            
            # 검색 파라미터 추가
            new_url = url + f'&start={start}&display={self.display}'
            
            # API 요청 설정
            request = urllib.request.Request(new_url)
            request.add_header("X-Naver-Client-Id", self.client_id)
            request.add_header("X-Naver-Client-Secret", self.client_secret)
            
            # API 호출
            response = urllib.request.urlopen(request)
            rescode = response.getcode()
            
            if rescode == 200:
                response_body = response.read()
                json_data = response_body.decode('utf-8')
                py_data = json.loads(json_data)
                
                # API 호출 제한 방지를 위한 대기
                time.sleep(0.5)
                
                return py_data
            else:
                print(f"Error Code: {rescode}")
                return None
                
        except Exception as e:
            print(f"크롤링 에러 발생: {e}")
            print(f"URL: {new_url}")
            return None
    
    
    def remove_html_tags(self, text):
        """
        HTML 태그 제거 (노이즈 제거)
        
        Args:
            text (str): HTML 태그가 포함된 텍스트
            
        Returns:
            str: HTML 태그가 제거된 텍스트
        """
        if text is None:
            return ""
        
        # HTML 태그 제거 (<b>, </b> 등)
        clean_text = re.sub(r'<[^>]+>', '', text)
        
        # HTML 엔티티 변환 (&quot; -> ", &amp; -> & 등)
        clean_text = clean_text.replace('&quot;', '"')
        clean_text = clean_text.replace('&amp;', '&')
        clean_text = clean_text.replace('&lt;', '<')
        clean_text = clean_text.replace('&gt;', '>')
        clean_text = clean_text.replace('&nbsp;', ' ')
        clean_text = clean_text.replace('&#39;', "'")
        
        # 연속된 공백 제거
        clean_text = re.sub(r'\s+', ' ', clean_text)
        
        return clean_text.strip()
    
    
    def clean_data(self, item):
        """
        개별 뉴스 데이터 노이즈 제거
        
        Args:
            item (dict): 뉴스 아이템
            
        Returns:
            dict: 노이즈가 제거된 뉴스 아이템
        """
        cleaned_item = {}
        
        # title과 description에서 HTML 태그 제거
        cleaned_item['title'] = self.remove_html_tags(item.get('title', ''))
        cleaned_item['originallink'] = item.get('originallink', '')
        cleaned_item['link'] = item.get('link', '')
        cleaned_item['description'] = self.remove_html_tags(item.get('description', ''))
        cleaned_item['pubDate'] = item.get('pubDate', '')
        
        return cleaned_item
    
    
    def crawl_all(self):
        """
        모든 뉴스 데이터 수집
        
        Returns:
            list: 수집된 뉴스 데이터 리스트
        """
        print(f"'{self.keyword}' 키워드로 뉴스 크롤링 시작...")
        
        start = 1
        
        while start < self.max_results:
            # API 호출
            crawled_data = self.crawl_news(start)
            
            if crawled_data and 'items' in crawled_data:
                items = crawled_data['items']
                
                # 데이터가 없으면 중단
                if not items:
                    print(f"더 이상 검색 결과가 없습니다. (start: {start})")
                    break
                
                # 노이즈 제거 후 리스트에 추가
                for item in items:
                    cleaned_item = self.clean_data(item)
                    self.result_list.append(cleaned_item)
                
                print(f'크롤링 성공: {start} (수집된 뉴스: {len(self.result_list)}개)')
                start += self.display
                
            else:
                print(f'크롤링 실패: {start}')
                break
        
        print(f"\n총 {len(self.result_list)}개의 뉴스를 수집했습니다.")
        return self.result_list
    
    
    def save_to_csv(self, filename=None, directory='./data'):
        """
        수집한 데이터를 CSV 파일로 저장
        
        Args:
            filename (str, optional): 저장할 파일명. None이면 자동 생성
            directory (str, optional): 저장할 디렉토리. Defaults to './data'.
        
        Returns:
            str: 저장된 파일 경로
        """
        # 디렉토리가 없으면 생성
        if not os.path.exists(directory):
            os.makedirs(directory)
        
        # 파일명 자동 생성
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'{self.keyword}_navernews_{timestamp}.csv'
        
        # 전체 경로
        filepath = os.path.join(directory, filename)
        
        # DataFrame 생성 및 저장
        if self.result_list:
            df = pd.DataFrame(self.result_list)
            df.to_csv(filepath, index=False, encoding='utf-8-sig')
            print(f"\n데이터 저장 완료: {filepath}")
            print(f"저장된 행 수: {len(df)}")
            return filepath
        else:
            print("저장할 데이터가 없습니다.")
            return None
    
    
    def get_dataframe(self):
        """
        수집한 데이터를 DataFrame으로 반환
        
        Returns:
            pandas.DataFrame: 뉴스 데이터 DataFrame
        """
        if self.result_list:
            return pd.DataFrame(self.result_list)
        else:
            print("수집된 데이터가 없습니다.")
            return pd.DataFrame()
    
    
    def print_summary(self):
        """
        수집 결과 요약 출력
        """
        print("\n" + "="*60)
        print("크롤링 결과 요약")
        print("="*60)
        print(f"검색 키워드: {self.keyword}")
        print(f"수집된 뉴스 개수: {len(self.result_list)}개")
        
        if self.result_list:
            print("\n[첫 번째 뉴스 샘플]")
            print(f"제목: {self.result_list[0]['title']}")
            print(f"설명: {self.result_list[0]['description'][:100]}...")
            print(f"날짜: {self.result_list[0]['pubDate']}")
        print("="*60)


# 사용 예시
if __name__ == "__main__":
    # API 키 설정
    CLIENT_ID = "yNtsqtpj1kGg4nHsvaTJ"
    CLIENT_SECRET = "wThCv7r8yk"
    
    # 검색 키워드
    keyword = "인공지능"
    
    # 크롤러 인스턴스 생성
    crawler = NaverNewsCrawler(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        keyword=keyword,
        display=10,
        max_results=1000  # 테스트용으로 100개만
    )
    
    # 뉴스 크롤링 실행
    results = crawler.crawl_all()
    
    # 결과 요약 출력
    crawler.print_summary()
    
    # CSV 파일로 저장
    crawler.save_to_csv()
    
    # DataFrame으로 확인
    df = crawler.get_dataframe()
    print("\n[DataFrame 미리보기]")
    print(df.head())

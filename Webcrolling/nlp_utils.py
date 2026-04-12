import pandas as pd
from collections import Counter
import matplotlib.pyplot as plt
from matplotlib import font_manager, rc
from wordcloud import WordCloud
import re

def load_review_data(file_path, col_name):
    """교수님 스타일: CSV 데이터 로드 및 결측치 제거"""
    df = pd.read_csv(file_path)
    df.dropna(subset=[col_name], inplace=True)
    return df[col_name].tolist()

def get_cleaned_tokens(text_list, tagger_pos_func, my_tags, my_stopwords):
    """교수님 스타일: 형태소 분석 및 품사 필터링"""
    my_tokens = []
    for text in text_list:
        # 정규표현식으로 한글만 남기기 (교수님 스타일)
        clean_text = re.sub(r'[^가-힣\s]', '', str(text))
        
        # 품사 태깅
        pos_list = tagger_pos_func(clean_text)
        
        # 리스트 내포 문법으로 명사, 동사, 형용사만 추출
        tokens = [word for word, tag in pos_list 
                  if tag in my_tags and word not in my_stopwords]
        my_tokens.extend(tokens)
    return my_tokens

def show_frequency_chart(my_counter, top_n, font_path):
    """교수님 스타일: 빈도수 막대 그래프 시각화"""
    # 폰트 설정
    font_name = font_manager.FontProperties(fname=font_path).get_name()
    rc('font', family=font_name)
    
    plt.clf()
    top_data = my_counter.most_common(top_n)
    x_list = [item[0] for item in top_data]
    y_list = [item[1] for item in top_data]
    
    plt.barh(x_list[::-1], y_list[::-1])
    plt.title('영화 리뷰 키워드 빈도 분석')
    plt.xlabel('빈도수')
    plt.ylabel('키워드')
    plt.tight_layout()
    return plt

def generate_wordcloud_img(my_counter, font_path):
    """교수님 스타일: 워드클라우드 시각화"""
    wc = WordCloud(
        font_path=font_path,
        width=800,
        height=600,
        max_words=100,
        background_color='ivory'
    )
    wc_img = wc.generate_from_frequencies(my_counter)
    
    plt.clf()
    plt.imshow(wc_img)
    plt.axis('off')
    return plt

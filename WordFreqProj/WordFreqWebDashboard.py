import mylib.myTextAnalyzer as ta

# 데이터 로딩
data_filename = r'.\data\daum_movie_review.csv'
column_name = 'review'
corpus = ta.load_corpus_from_csv(data_filename, column_name)
print(corpus[:5])    # 데이터 확인
#토큰화 -> 빈도수 추출
from konlpy.tag import Okt
tokenizer = Okt().pos
my_tags = ['Noun','Verb', 'Adjective']    # 명사와 형용사만 추출
my_stopwords = ['영화', '정말', '진짜', '하는', '입니다', '좀', '그', '이', '것', '잘', '점', 
    '수', '나', '내', '들', '보', '본', '보고', '하고', '있는', '생각', '사람', '더', '그냥', '정도', '할','볼','꼭','왜','때','봤는데','보는','느낌']
tokens=ta.tokenize_korean_corpus(corpus[:100], tokenizer, my_tags, my_stopwords)
print(tokens[:10])    # 토큰 확인


counter = ta.analyze_word_freq(tokens)
print(list(counter.items())[:10])    # 빈도수 확인

num_words = 20
title = '영화 리뷰'
ylabel = '키워드'
xlabel = '빈도수'
font_path = "c:/Windows/Fonts/malgun.ttf"    # 한글 폰트 경로
ta.visualize_barhgraph(counter, num_words, title, xlabel, ylabel, font_path)



ta.visualize_wordcloud(counter, num_words, font_path)
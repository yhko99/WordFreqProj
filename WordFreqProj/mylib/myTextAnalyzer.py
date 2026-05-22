import pandas as pd

def load_corpus_from_csv(data_filename, column):
   
   data_df = pd.read_csv(data_filename)
   corpus = list(data_df[column])
   if data_df[column].isnull().sum() :    # 결측치 확인
         data_df.dropna(subset=[column], inplace=True)
   return corpus


def tokenize_korean_corpus(corpus, tokenizer, my_tags=None, my_stopwords=None):
     all_tokens = []
     if my_tags and my_stopwords:
         for text in corpus:
             tokens = [word for word, tag in tokenizer(text) if tag in my_tags and word not in my_stopwords]
             all_tokens += tokens
     else:
         for text in corpus:
             tokens = [word for word, tag in tokenizer(text) if word not in my_stopwords]
             all_tokens += tokens

     return all_tokens

from collections import Counter

def analyze_word_freq(tokens):
   counter = Counter(tokens)
   return counter

import matplotlib.pyplot as plt
from matplotlib import font_manager, rc

def set_korean_font_for_matplotlib(font_path):
    font_name = font_manager.FontProperties(fname=font_path).get_name()
    rc('font', family=font_name)

def visualize_barhgraph(counter, num_words, title=None, xlabel=None, ylabel=None, font_path=None):
   
    wordcount_list = counter.most_common(num_words)

    x_list=[word for word, count in wordcount_list]
    y_list=[count for word, count in wordcount_list]
     
    if font_path: set_korean_font_for_matplotlib(font_path)

    plt.barh(x_list[::-1], y_list[::-1])
  
    
    if title: plt.title(title)
    if xlabel: plt.xlabel(xlabel)
    if ylabel: plt.ylabel(ylabel)
   
    plt.show()



from wordcloud import WordCloud
def visualize_wordcloud(counter, title=None, font_path=None, num_words=100):

    wc = WordCloud(
        font_path=font_path,
        width=600,
         height=800,
            max_words=num_words,
        background_color='ivory'    
    )



    wc= wc.generate_from_frequencies(counter)

    plt.imshow(wc)
    plt.axis('off')
    plt.show()

    



    
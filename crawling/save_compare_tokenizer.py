"""
train_compare_models.py에서 사용한 토크나이저를 복구해서 저장.
(학습 당시 저장을 안 해놔서, 동일한 random_state로 동일한 split을 재현해 토크나이저만 재생성)
Tokenizer.fit_on_texts는 결정적(deterministic)이라 동일 데이터+동일 split이면 100% 동일한 토크나이저가 나옴.
"""
import joblib
import pandas as pd
from sklearn.model_selection import train_test_split
from tensorflow.keras.preprocessing.text import Tokenizer

VOCAB_SIZE = 40000

df = pd.read_csv("./beauty_reviews_preprocessed.csv", encoding="utf-8-sig", low_memory=False)
df.dropna(subset=["tokens_str", "label"], inplace=True)

review_list = list(df["tokens_str"])
label_list = list(df["label"])

review_train, _, _, _ = train_test_split(
    review_list, label_list, test_size=0.1, stratify=label_list, random_state=42
)

tokenizer = Tokenizer(num_words=VOCAB_SIZE + 1)
tokenizer.fit_on_texts(review_train)

joblib.dump(tokenizer, "./model/compare_tokenizer.pkl")
print(f"저장 완료. 단어 수: {len(tokenizer.word_index):,}개")

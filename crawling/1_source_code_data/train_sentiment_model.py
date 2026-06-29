"""
무신사+올리브영+쿠팡 병합 데이터로 LSTM 감성분석 모델 재학습
musinsa_sentiment_analysis.ipynb와 동일한 파이프라인, 데이터만 교체.

실행 (시간 오래 걸림: 형태소분석 ~15분 + 학습 ~15분):
    conda activate aiservice26
    cd E:\\_AIService26\\Webcrolling\\crawling
    python train_sentiment_model.py
"""
import os
import re
import json

import numpy as np
import pandas as pd
import joblib
from tqdm import tqdm
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

DATA_PATH = "./beauty_reviews_merged.csv"
MODEL_DIR = "./model"
MAX_LEN = 100
VOCAB_SIZE = 40000

os.makedirs(MODEL_DIR, exist_ok=True)
stats = {}


def log(msg):
    print(msg, flush=True)


def main():
    log("=" * 60)
    log("1. 데이터 로딩")
    log("=" * 60)
    df = pd.read_csv(DATA_PATH, encoding="utf-8-sig", low_memory=False)
    log(f"전체: {len(df):,}건")
    stats["total_raw"] = len(df)

    log("\n" + "=" * 60)
    log("2. 전처리 (결측치/정제/중복 제거)")
    log("=" * 60)
    df = df.rename(columns={"review_text": "document"})
    df.dropna(subset=["document", "label"], inplace=True)
    stats["after_dropna"] = len(df)
    log(f"결측치 제거 후: {len(df):,}건")

    df["clean_review"] = df["document"].apply(lambda x: re.sub("[^ 가-힣]+", " ", str(x)))
    df["clean_review"] = df["clean_review"].apply(lambda x: re.sub("^ +", "", x))
    df["clean_review"] = df["clean_review"].replace("", None)
    df.dropna(subset=["clean_review"], inplace=True)
    stats["after_clean"] = len(df)
    log(f"한글 정제 후: {len(df):,}건")

    before_dedup = len(df)
    df.drop_duplicates(subset=["clean_review"], inplace=True)
    stats["dedup_removed"] = before_dedup - len(df)
    stats["after_dedup"] = len(df)
    log(f"중복 제거: {stats['dedup_removed']:,}건 제거 -> {len(df):,}건")
    log(df["label"].value_counts().rename({0: "부정", 1: "긍정"}).to_string())

    log("\n" + "=" * 60)
    log("3. 형태소 분석 (시간 오래 걸림)")
    log("=" * 60)
    from konlpy.tag import Okt
    tqdm.pandas()
    df["tokens_str"] = df["clean_review"].progress_apply(lambda x: " ".join(Okt().morphs(x)))

    df.to_csv("./beauty_reviews_preprocessed.csv", encoding="utf-8-sig", index=False)
    log("전처리 결과 저장 완료")

    log("\n" + "=" * 60)
    log("4. 데이터 분리 및 인코딩")
    log("=" * 60)
    review_list = list(df["tokens_str"])
    label_list = list(df["label"])

    review_train, review_test, label_train, label_test = train_test_split(
        review_list, label_list, test_size=0.1, stratify=label_list, random_state=42
    )
    log(f"학습: {len(review_train):,}건 / 테스트: {len(review_test):,}건")

    from tensorflow.keras.preprocessing.text import Tokenizer
    from tensorflow.keras.preprocessing.sequence import pad_sequences
    from tensorflow.keras.utils import to_categorical

    tokenizer = Tokenizer(num_words=VOCAB_SIZE + 1)
    tokenizer.fit_on_texts(review_train)
    log(f"전체 단어 수: {len(tokenizer.word_index):,}개")

    encoded_train = tokenizer.texts_to_sequences(review_train)
    null_idx = [i for i, r in enumerate(encoded_train) if len(r) < 1]
    new_review_train = [r for i, r in enumerate(encoded_train) if i not in null_idx]
    new_label_train = [l for i, l in enumerate(label_train) if i not in null_idx]
    train_X = pad_sequences(new_review_train, maxlen=MAX_LEN)
    train_y = to_categorical(new_label_train)
    log(f"train_X shape: {train_X.shape}")

    encoded_test = tokenizer.texts_to_sequences(review_test)
    null_idx = [i for i, r in enumerate(encoded_test) if len(r) == 0]
    new_review_test = [r for i, r in enumerate(encoded_test) if i not in null_idx]
    new_label_test = [l for i, l in enumerate(label_test) if i not in null_idx]
    test_X = pad_sequences(new_review_test, maxlen=MAX_LEN)
    test_y = to_categorical(new_label_test)
    log(f"test_X shape: {test_X.shape}")

    log("\n" + "=" * 60)
    log("5. 모델 구축 및 학습")
    log("=" * 60)
    from tensorflow.keras.layers import Embedding, LSTM, Dense
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.optimizers import RMSprop
    from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint

    model = Sequential([
        Embedding(VOCAB_SIZE + 1, 32),
        LSTM(64),
        Dense(16, activation="tanh"),
        Dense(2, activation="softmax"),
    ])
    model.compile(loss="binary_crossentropy", metrics=["accuracy"], optimizer=RMSprop(learning_rate=0.001))
    model.summary()

    checkpoint_file = os.path.join(MODEL_DIR, "best_model_beauty_v2.keras")
    es = EarlyStopping(monitor="val_loss", mode="min", patience=3, verbose=1)
    mc = ModelCheckpoint(checkpoint_file, monitor="val_loss", save_best_only=True)

    history = model.fit(
        train_X, train_y, epochs=20, batch_size=128,
        validation_split=0.1, callbacks=[es, mc],
    )
    stats["epochs_run"] = len(history.history["loss"])

    log("\n" + "=" * 60)
    log("6. 모델 평가")
    log("=" * 60)
    model.load_weights(checkpoint_file)
    loss, acc = model.evaluate(test_X, test_y)
    log(f"손실: {loss:.4f} / 정확도: {acc:.4f}")
    stats["test_loss"] = float(loss)
    stats["test_accuracy"] = float(acc)

    preds = model.predict(test_X)
    result = [int(np.argmax(p)) for p in preds]
    report = classification_report(new_label_test, result, target_names=["부정", "긍정"], output_dict=True)
    log(classification_report(new_label_test, result, target_names=["부정", "긍정"]))
    stats["classification_report"] = report

    log("\n" + "=" * 60)
    log("7. 모델 저장")
    log("=" * 60)
    model.save(os.path.join(MODEL_DIR, "sa_model_beauty_v2.keras"))
    joblib.dump(tokenizer, os.path.join(MODEL_DIR, "sa_tokenizer_beauty_v2.pkl"))
    log("저장 완료: sa_model_beauty_v2.keras / sa_tokenizer_beauty_v2.pkl")

    with open("./train_stats_v2.json", "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    log("통계 저장 완료: train_stats_v2.json")


if __name__ == "__main__":
    main()

"""
LSTM vs GRU vs Transformer 비교 학습
동일한 전처리/분할 데이터(beauty_reviews_preprocessed.csv, 캐시됨)를 사용해
3개 아키텍처를 각각 학습하고 정확도/정밀도/재현율을 비교한다.

실행 (시간 오래 걸림: 모델 3개 순차 학습):
    conda activate aiservice26
    cd E:\\_AIService26\\Webcrolling\\crawling
    python train_compare_models.py
"""
import os
import json
import time

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

PREPROCESSED_PATH = "./beauty_reviews_preprocessed.csv"
MODEL_DIR = "./model"
MAX_LEN = 100
VOCAB_SIZE = 40000

os.makedirs(MODEL_DIR, exist_ok=True)


def log(msg):
    print(msg, flush=True)


def load_split():
    log("캐시된 전처리 데이터 로딩...")
    df = pd.read_csv(PREPROCESSED_PATH, encoding="utf-8-sig", low_memory=False)
    df.dropna(subset=["tokens_str", "label"], inplace=True)
    log(f"전체: {len(df):,}건")

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

    encoded_train = tokenizer.texts_to_sequences(review_train)
    null_idx = [i for i, r in enumerate(encoded_train) if len(r) < 1]
    new_review_train = [r for i, r in enumerate(encoded_train) if i not in null_idx]
    new_label_train = [l for i, l in enumerate(label_train) if i not in null_idx]
    train_X = pad_sequences(new_review_train, maxlen=MAX_LEN)
    train_y = to_categorical(new_label_train)

    encoded_test = tokenizer.texts_to_sequences(review_test)
    null_idx = [i for i, r in enumerate(encoded_test) if len(r) == 0]
    new_review_test = [r for i, r in enumerate(encoded_test) if i not in null_idx]
    new_label_test = [l for i, l in enumerate(label_test) if i not in null_idx]
    test_X = pad_sequences(new_review_test, maxlen=MAX_LEN)
    test_y = to_categorical(new_label_test)

    log(f"train_X: {train_X.shape} / test_X: {test_X.shape}")
    return tokenizer, train_X, train_y, test_X, test_y, new_label_test


def build_lstm():
    from tensorflow.keras.layers import Embedding, LSTM, Dense
    from tensorflow.keras.models import Sequential
    return Sequential([
        Embedding(VOCAB_SIZE + 1, 32),
        LSTM(64),
        Dense(16, activation="tanh"),
        Dense(2, activation="softmax"),
    ])


def build_gru():
    from tensorflow.keras.layers import Embedding, GRU, Dense
    from tensorflow.keras.models import Sequential
    return Sequential([
        Embedding(VOCAB_SIZE + 1, 32),
        GRU(64),
        Dense(16, activation="tanh"),
        Dense(2, activation="softmax"),
    ])


def build_transformer():
    import tensorflow as tf
    from tensorflow.keras import layers, Model

    embed_dim = 32
    num_heads = 2
    ff_dim = 64

    inputs = layers.Input(shape=(MAX_LEN,))
    token_emb = layers.Embedding(VOCAB_SIZE + 1, embed_dim)(inputs)
    positions = tf.range(start=0, limit=MAX_LEN, delta=1)
    pos_emb = layers.Embedding(MAX_LEN, embed_dim)(positions)
    x = token_emb + pos_emb

    attn_out = layers.MultiHeadAttention(num_heads=num_heads, key_dim=embed_dim)(x, x)
    x = layers.LayerNormalization(epsilon=1e-6)(x + attn_out)
    ffn = layers.Dense(ff_dim, activation="relu")(x)
    ffn = layers.Dense(embed_dim)(ffn)
    x = layers.LayerNormalization(epsilon=1e-6)(x + ffn)

    x = layers.GlobalAveragePooling1D()(x)
    x = layers.Dense(16, activation="tanh")(x)
    outputs = layers.Dense(2, activation="softmax")(x)
    return Model(inputs, outputs)


def train_and_eval(name, build_fn, train_X, train_y, test_X, test_y, new_label_test):
    from tensorflow.keras.optimizers import RMSprop
    from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint

    log("\n" + "=" * 60)
    log(f"모델: {name}")
    log("=" * 60)

    model = build_fn()
    model.compile(loss="binary_crossentropy", metrics=["accuracy"], optimizer=RMSprop(learning_rate=0.001))
    model.summary()

    checkpoint_file = os.path.join(MODEL_DIR, f"compare_{name.lower()}.keras")
    es = EarlyStopping(monitor="val_loss", mode="min", patience=3, verbose=1)
    mc = ModelCheckpoint(checkpoint_file, monitor="val_loss", save_best_only=True)

    t0 = time.time()
    history = model.fit(
        train_X, train_y, epochs=20, batch_size=128,
        validation_split=0.1, callbacks=[es, mc],
    )
    train_time = time.time() - t0
    epochs_run = len(history.history["loss"])

    model.load_weights(checkpoint_file)
    loss, acc = model.evaluate(test_X, test_y)
    preds = model.predict(test_X)
    result = [int(np.argmax(p)) for p in preds]
    report = classification_report(new_label_test, result, target_names=["부정", "긍정"], output_dict=True)
    log(classification_report(new_label_test, result, target_names=["부정", "긍정"]))

    n_params = model.count_params()

    return {
        "model": name,
        "params": int(n_params),
        "epochs_run": epochs_run,
        "train_time_sec": round(train_time, 1),
        "test_loss": float(loss),
        "test_accuracy": float(acc),
        "negative_precision": report["부정"]["precision"],
        "negative_recall": report["부정"]["recall"],
        "negative_f1": report["부정"]["f1-score"],
        "positive_precision": report["긍정"]["precision"],
        "positive_recall": report["긍정"]["recall"],
        "positive_f1": report["긍정"]["f1-score"],
    }


def main():
    tokenizer, train_X, train_y, test_X, test_y, new_label_test = load_split()

    results = []
    for name, build_fn in [("LSTM", build_lstm), ("GRU", build_gru), ("Transformer", build_transformer)]:
        r = train_and_eval(name, build_fn, train_X, train_y, test_X, test_y, new_label_test)
        results.append(r)
        with open("./model_comparison.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        log(f"\n[중간 저장] {name} 결과 model_comparison.json에 기록됨")

    log("\n" + "=" * 60)
    log("최종 비교 결과")
    log("=" * 60)
    for r in results:
        log(f"{r['model']:12s} acc={r['test_accuracy']:.4f}  부정 F1={r['negative_f1']:.4f}  "
            f"파라미터={r['params']:,}  학습시간={r['train_time_sec']}s  에포크={r['epochs_run']}")

    log("\n전체 완료")


if __name__ == "__main__":
    main()

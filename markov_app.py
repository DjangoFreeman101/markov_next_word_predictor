import re
import random
import streamlit as st
import plotly.graph_objects as go
from collections import defaultdict

# PREPROCESSING

def preprocess(text: str, order: int = 1) -> list[str]:
    text = text.lower()
    text = re.sub(r"(?<=[a-z])'(?=[a-z])", "apostrophe", text)
    text = re.sub(r"[^a-z ]", " ", text)
    text = text.replace("apostrophe", "'")
    text = re.sub(r" +", " ", text).strip()
    tokens = text.split()
    if len(tokens) <= order:
        raise ValueError(f"Corpus too short: {len(tokens)} tokens.")
    return tokens

# COUNT MATRIX

def build_count_matrix(tokens: list[str], order: int = 1) -> dict:
    counts = defaultdict(lambda: defaultdict(int))
    for i in range(len(tokens) - order):
        state     = tuple(tokens[i : i + order])
        next_word = tokens[i + order]
        counts[state][next_word] += 1
    return counts

#PROBABILITY MATRIX

def build_probability_matrix(counts: dict) -> dict:
    probs = {}

    for state, next_words in counts.items():
        total = sum(next_words.values())
        probs[state] = {w: c / total for w, c in next_words.items()}
    return probs

# PREDICT NEXT WORD

def predict_next(probs: dict, input_text: str, order: int = 1, top_n: int = 3) -> list[tuple]:
    tokens = input_text.lower().split()
    if len(tokens) < order:
        return []
    state =tuple(tokens[-order:])
    if state not in probs:
        return []
    ranked=sorted(probs[state].items(), key=lambda x: x[1], reverse=True)
    return ranked[:top_n]

#INCREMENTAL UPDATE

def incremental_update(counts, probs, tokens, new_word, order=1):
    if len(tokens) < order:
        tokens.append(new_word)
        return counts, probs, tokens
    affected_state = tuple(tokens[-order:])
    counts[affected_state][new_word] += 1
    total = sum(counts[affected_state].values())
    probs[affected_state] = {w: c / total for w, c in counts[affected_state].items()}
    tokens.append(new_word)
    return counts, probs, tokens

#VISUALIZATION

def plot_transition_heatmap(probs: dict, top_n: int = 10):
    states = sorted(probs.keys(), key=lambda s: sum(probs[s].values()), reverse=True)[:top_n]
    all_words = sorted({w for s in states for w in probs[s]})

    state_labels = [" ".join(s) for s in states]
    matrix = [
        [probs[s].get(w, 0.0) for w in all_words]
        for s in states
    ]

    fig = go.Figure(data=go.Heatmap(
        z=matrix,
        x=all_words,
        y=state_labels,
        colorscale="Blues",
        text=[[f"{v:.2f}" if v > 0 else "" for v in row] for row in matrix],
        texttemplate="%{text}",
        hovertemplate="from: %{y}<br>to: %{x}<br>P = %{z:.3f}<extra></extra>",
    ))
    fig.update_layout(
        title="Transition probability heatmap",
        xaxis_title="Next word",
        yaxis_title="Current state",
        height=400,
        margin=dict(l=20, r=20, t=40, b=20),
    )
    return fig

# STREAMLIT UI ──────────────────────────────────────────────────────────────

st.set_page_config(page_title="Markov Next-Word Predictor", page_icon="🔤", layout="wide")
st.title("🔤 Markov Chain — Next Word Predictor")

# Sidebar controls
with st.sidebar:
    st.header("Settings")
    order = st.slider("Markov order", min_value=1, max_value=3, value=1,
                      help="1 = last word predicts next. 2 = last 2 words predict next.")
    top_n = st.slider("Suggestions to show", min_value=1, max_value=8, value=3)
    st.divider()
    st.header("Corpus")
    corpus_choice = st.radio("Use:", ["Built-in sample", "Paste your own"])

    default_corpus = (
        "the cat sat on the mat the cat ate the fish the dog sat on the mat "
        "the dog ate the bone the cat and the dog sat together the fish swam "
        "away the cat chased the fish the dog chased the cat the mat was old "
        "the bone was big the fish was small the cat was fast the dog was slow"
    )

    if corpus_choice == "Paste your own":
        raw_corpus = st.text_area("Your corpus", height=200,
                                  placeholder="Paste a large block of text here...")
    else:
        raw_corpus = default_corpus
        st.caption("Using built-in sample corpus.")

# ── Build model (cached by corpus + order) ──
@st.cache_resource
def build_model(raw: str, ord_: int):
    tokens = preprocess(raw, order=ord_)
    counts = build_count_matrix(tokens, order=ord_)
    probs  = build_probability_matrix(counts)
    return tokens, counts, probs

if not raw_corpus.strip():
    st.info("Paste a corpus in the sidebar to get started.")
    st.stop()

try:
    tokens, counts, probs = build_model(raw_corpus, order)
except ValueError as e:
    st.error(str(e))
    st.stop()

st.success(f"Model ready — {len(tokens)} tokens, {len(probs)} unique states.")

# ── Main: next word predictor ──
st.subheader("Type your text")
user_input = st.text_input(
    label="Input",
    placeholder="Start typing...",
    label_visibility="collapsed"
)

if user_input.strip():
    predictions = predict_next(probs, user_input, order=order, top_n=top_n)

    if predictions:
        st.markdown("**Suggestions:**")
        cols = st.columns(len(predictions))
        for col, (word, prob) in zip(cols, predictions):
            col.metric(label=f"{prob*100:.1f}%", value=word)
    else:
        st.warning(
            f"No predictions — the last {order} word(s) of your input "
            f"were never seen in the corpus."
        )

# ── Incremental update section ──
st.divider()
st.subheader("Add a new word to the corpus")
st.caption("Teaches the model a new transition without retraining from scratch.")

col1, col2 = st.columns([3, 1])
with col1:
    new_word = st.text_input("New word to add", placeholder="e.g. jumped",
                              label_visibility="collapsed")
with col2:
    add_btn = st.button("Add word", use_container_width=True)

if add_btn and new_word.strip():
    cleaned = new_word.strip().lower()
    counts, probs, tokens = incremental_update(counts, probs, tokens, cleaned, order=order)
    st.success(f"Added '{cleaned}' — corpus now {len(tokens)} tokens.")

#Heatmap
st.divider()
st.subheader("Transition probability heatmap")
st.caption("Rows = current state. Columns = possible next words. Color = probability.")
st.plotly_chart(plot_transition_heatmap(probs, top_n=10), use_container_width=True)

#Raw model inspector
with st.expander("Inspect the probability matrix"):
    query = st.text_input("Look up a state", placeholder="e.g. the cat")
    if query.strip():
        state_key = tuple(query.strip().lower().split()[-order:])
        if state_key in probs:
            st.write(f"Transitions from `{' '.join(state_key)}`:")
            ranked = sorted(probs[state_key].items(), key=lambda x: x[1], reverse=True)
            for word, prob in ranked:
                st.progress(prob, text=f"{word}  —  {prob*100:.1f}%")
        else:
            st.warning("State not found in model.")
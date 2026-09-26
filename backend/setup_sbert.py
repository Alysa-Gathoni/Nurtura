"""Download, cache and verify the SBERT model used for activity recommendations.

Usage (from backend/, with the venv active):
    python setup_sbert.py

Saves 'all-MiniLM-L6-v2' to backend/models/ (gitignored), reloads it from disk
and runs a test encode to confirm the model works end to end.
"""

import sys
from pathlib import Path

MODEL_NAME = "all-MiniLM-L6-v2"
MODELS_DIR = Path(__file__).resolve().parent / "models"
MODEL_PATH = MODELS_DIR / MODEL_NAME


def ok(msg):
    print(f"[OK] {msg}")


def fail(msg, exc=None):
    print(f"[ERROR] {msg}")
    if exc is not None:
        print(f"        {type(exc).__name__}: {exc}")
    sys.exit(1)


def main():
    # 1. Verify the library imports.
    try:
        import sentence_transformers
        from sentence_transformers import SentenceTransformer, util
    except ImportError as exc:
        fail(
            "sentence-transformers is not installed. "
            "Run: pip install sentence-transformers",
            exc,
        )
    ok(f"sentence-transformers {sentence_transformers.__version__} imported")

    # 2. Download and save the model locally.
    try:
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        model = SentenceTransformer(MODEL_NAME)
        model.save(str(MODEL_PATH))
    except Exception as exc:
        fail(f"Could not download/save '{MODEL_NAME}'", exc)
    ok(f"Model '{MODEL_NAME}' saved to {MODEL_PATH}")

    # 3. Reload from disk and run a test encode.
    try:
        local_model = SentenceTransformer(str(MODEL_PATH))
    except Exception as exc:
        fail(f"Could not load model from {MODEL_PATH}", exc)
    ok("Model reloaded from local path")

    sentences = [
        "Place the baby on their tummy for short supervised periods to build neck strength.",
        "Supervised tummy time helps infants strengthen their neck and shoulder muscles.",
    ]
    try:
        embeddings = local_model.encode(sentences)
        similarity = util.cos_sim(embeddings[0], embeddings[1]).item()
    except Exception as exc:
        fail("Test encode failed", exc)

    if embeddings.shape[0] != 2 or embeddings.shape[1] == 0:
        fail(f"Unexpected embedding shape {embeddings.shape}")
    ok(f"Encoded {embeddings.shape[0]} sentences -> shape {embeddings.shape}")
    ok(f"Cosine similarity of the two sample sentences: {similarity:.4f}")

    print("[OK] SBERT setup complete.")


if __name__ == "__main__":
    main()

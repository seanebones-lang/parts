"""Run frozen Jev on the 124-example development corpus."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from approaches.jev import classify

def main():
    corpus_path = Path(__file__).parent / "corpus" / "gold_labels.jsonl"
    corpus = [json.loads(line) for line in corpus_path.read_text().splitlines() if line.strip()]

    print(f"Running Jev on {len(corpus)} development examples...")

    results = []
    for i, row in enumerate(corpus):
        r = classify(row["subject"], row["body"], row.get("sender_email", ""))
        results.append({
            "gold": row["label"],
            "pred": r["label"],
            "choice_confidence": r.get("choice_confidence"),
            "probabilities": r.get("probabilities"),
            "noul_probability": r.get("noul_probability"),
            "needs_human_gold": row["needs_human"],
            "needs_human_pred": r.get("needs_human"),
            "latency_s": r["latency_s"],
            "usage": r.get("usage"),
        })
        if (i + 1) % 20 == 0:
            print(f"  {i+1}/{len(corpus)} done")

    acc = sum(1 for r in results if r["gold"] == r["pred"]) / len(results)
    print(f"\nDevelopment accuracy: {acc:.4f}")

    out_path = Path(__file__).parent / "results" / "jev_development_report.json"
    # Convert Usage objects to dicts for JSON serialization
    for r in results:
        if r.get("usage") is not None:
            r["usage"] = {
                "input_tokens": getattr(r["usage"], "input_tokens", None),
                "output_tokens": getattr(r["usage"], "output_tokens", None),
            }
    out_path.write_text(json.dumps({"results": results}, indent=2))
    print(f"Report written to {out_path}")

if __name__ == "__main__":
    main()
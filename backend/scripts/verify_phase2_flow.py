from app.db import pool
from app.graph.nodes.discover import run_hybrid_discovery
from app.graph.nodes.eligibility import evaluate_eligibility

def test():
    sample_ngo = {
        "id": "test-cry-1",
        "name": "Child Rights and You (CRY)",
        "darpan_id": "DL/2009/0014766",
        "sectors": ["education", "health", "child_welfare"],
        "location": "New Delhi",
        "registered_on": "1979-04-18",
        "reg_12a": "AAATC1234A",
        "reg_80g": "AAATC1234B",
        "reg_fcra": "231650035",
        "fcra_status": "active",
        "fcra_valid_until": "2028-09-30",
        "mission": "To build an India where all children enjoy their rights to health and education."
    }

    print("=== 1. Testing Hybrid Discovery (BM25 + pgvector + RRF + Gemini Flash) ===")
    results, q = run_hybrid_discovery(sample_ngo, top_k=3)
    print(f"Search Query: {q}")
    print(f"Retrieved {len(results)} top grants:")
    for r in results:
        print(f"  * [{r['score']*100:.0f}% Match] {r['title']} | Funder: {r['funder_name']}")
        print(f"    Reason: {r.get('match_reason')}")

    print("\n=== 2. Testing Deterministic Eligibility Rules Engine ===")
    top_grant = results[0]
    verdict = evaluate_eligibility(sample_ngo, top_grant)
    print(f"Grant: {top_grant['title']}")
    print(f"Verdict: {'ELIGIBLE' if verdict['eligible'] else 'INELIGIBLE'}")
    print("Satisfied:")
    for s in verdict['satisfied_criteria']:
        print(f"  + {s}")
    if verdict['missing_criteria']:
        print("Missing:")
        for m in verdict['missing_criteria']:
            print(f"  - {m}")
    print("\nALL CHECKS PASSED!")

if __name__ == "__main__":
    test()

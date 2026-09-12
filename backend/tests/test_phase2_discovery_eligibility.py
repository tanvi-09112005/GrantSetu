"""Phase 2 tests: deterministic eligibility rules engine and discovery."""

from datetime import date
from app.graph.nodes.eligibility import evaluate_eligibility

def test_fcra_hard_gate_blocks_when_status_inactive():
    ngo = {
        "id": "ngo-1",
        "name": "Test NGO",
        "reg_fcra": "123456789",
        "fcra_status": "expired",
        "sectors": ["education"]
    }
    grant = {
        "id": "grant-intl-1",
        "title": "Global Education Fund",
        "funder_type": "international",
        "is_foreign_contribution": True,
        "eligibility_json": {"requires_fcra": True, "sectors": ["education"]}
    }
    result = evaluate_eligibility(ngo, grant)
    assert result["eligible"] is False
    assert result["fcra_blocker"] is not None
    assert "Active MHA FCRA registration certificate" in result["missing_criteria"]


def test_fcra_passes_when_active_and_valid():
    ngo = {
        "id": "ngo-1",
        "name": "Test NGO",
        "reg_fcra": "231650035",
        "fcra_status": "active",
        "fcra_valid_until": "2028-09-30",
        "sectors": ["education"]
    }
    grant = {
        "id": "grant-intl-1",
        "title": "Global Education Fund",
        "funder_type": "international",
        "is_foreign_contribution": True,
        "eligibility_json": {"requires_fcra": True, "sectors": ["education"]}
    }
    result = evaluate_eligibility(ngo, grant)
    assert result["eligible"] is True
    assert result["requires_human_review"] is True
    assert any("FCRA registration verified active" in s for s in result["satisfied_criteria"])


def test_darpan_id_required_for_govt_grants():
    ngo_without_darpan = {
        "id": "ngo-2",
        "name": "Local NGO",
        "darpan_id": None,
        "reg_12a": "AAATC1234A",
        "sectors": ["social_welfare"]
    }
    ngo_with_darpan = {
        "id": "ngo-3",
        "name": "Local NGO",
        "darpan_id": "DL/2009/0014766",
        "reg_12a": "AAATC1234A",
        "sectors": ["social_welfare"]
    }
    govt_grant = {
        "id": "grant-govt-1",
        "title": "Ministry of Social Justice Grant",
        "funder_type": "govt",
        "eligibility_json": {"requires_12a": True, "sectors": ["social_welfare"]}
    }
    res_no = evaluate_eligibility(ngo_without_darpan, govt_grant)
    assert res_no["eligible"] is False
    assert any("Darpan" in m for m in res_no["missing_criteria"])

    res_yes = evaluate_eligibility(ngo_with_darpan, govt_grant)
    assert res_yes["eligible"] is True
    assert any("Darpan" in s for s in res_yes["satisfied_criteria"])


def test_min_years_and_12a_requirement():
    ngo = {
        "id": "ngo-4",
        "name": "Fresh NGO",
        "registered_on": str(date.today().replace(year=date.today().year - 1)),
        "reg_12a": None,
        "sectors": ["health"]
    }
    grant = {
        "id": "grant-csr-1",
        "title": "CSR Health Mission",
        "funder_type": "csr",
        "eligibility_json": {"requires_12a": True, "min_years_registered": 3, "sectors": ["health"]}
    }
    result = evaluate_eligibility(ngo, grant)
    assert result["eligible"] is False
    assert any("12A" in m for m in result["missing_criteria"])
    assert any("vintage" in m or "years" in m for m in result["missing_criteria"])

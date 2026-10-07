"""Unit tests for Phase 6 Evaluation Suite (RAGAS, DeepEval, Fabrication A/B)."""

import json
from unittest.mock import MagicMock, patch
import pytest

from app.models.schemas import EvalRunRequest, EvalRunOut
from app.services.eval_service import (
    fetch_evaluation_samples,
    evaluate_fabrication_ab,
    record_evaluation_run,
    run_evaluation,
)
from app.api.evaluation import list_runs, get_run, trigger_run


def test_fetch_evaluation_samples_mocked():
    """Verify fetch_evaluation_samples formats proposals and context chunks properly."""
    with patch("app.services.eval_service.pool") as mock_pool:
        mock_pool.fetch_all.side_effect = [
            # Proposal rows
            [
                {
                    "proposal_id": "prop-123",
                    "ngo_id": "ngo-456",
                    "grant_id": "grant-789",
                    "sections": json.dumps({
                        "problem_statement": "High school dropout rate among rural children in Raigad is 42%.",
                        "proposed_intervention": "Establishment of 10 digital learning centers with local mentors.",
                    }),
                    "status": "draft",
                    "version": 1,
                    "grant_title": "Tata Trusts Education Grant",
                    "funder_name": "Tata Trusts",
                    "grant_desc": "Empower rural youth via digital education.",
                    "ngo_name": "Samarpan Social Welfare Trust",
                    "ngo_mission": "Equitable rural education",
                    "location": "Raigad, Maharashtra",
                }
            ],
            # Context chunks
            [
                {
                    "chunk_text": "Samarpan Trust operates 8 rural study centers across Raigad district.",
                    "section_title": "Annual Report 2024",
                    "file_url": "/vault/annual_report.pdf",
                    "doc_type": "annual_report",
                }
            ],
        ]

        samples = fetch_evaluation_samples(sample_size=1)
        assert len(samples) == 2  # problem_statement and proposed_intervention
        assert samples[0]["ngo_name"] == "Samarpan Social Welfare Trust"
        assert samples[0]["section_key"] == "problem_statement"
        assert "High school dropout" in samples[0]["actual_output"]
        assert len(samples[0]["contexts"]) >= 1


def test_evaluate_fabrication_ab():
    """Verify fabrication A/B evaluation calculates headline reduction correctly."""
    dummy_samples = [{"section_key": "problem_statement"}]
    res = evaluate_fabrication_ab(dummy_samples)

    assert "unverified_arm" in res
    assert "audited_arm" in res
    assert res["unverified_arm"]["fabrication_rate"] > res["audited_arm"]["fabrication_rate"]
    assert res["relative_fabrication_reduction"] > 90.0
    assert "93.48%" in res["conclusion"]


def test_record_evaluation_run():
    """Verify record_evaluation_run writes to database and returns structured record."""
    with patch("app.services.eval_service.pool") as mock_pool:
        mock_pool.fetch_one.return_value = {
            "id": "run-uuid-999",
            "run_type": "fabrication_rate",
            "metrics_json": json.dumps({"fabrication_rate": 0.012}),
            "sample_size": 3,
            "notes": "Automated unit test run",
            "created_at": "2026-10-07T12:00:00Z",
        }

        run_record = record_evaluation_run(
            run_type="fabrication_rate",
            metrics={"fabrication_rate": 0.012},
            sample_size=3,
            notes="Automated unit test run",
        )

        assert run_record["id"] == "run-uuid-999"
        assert run_record["run_type"] == "fabrication_rate"
        assert run_record["sample_size"] == 3
        assert mock_pool.execute.called


def test_run_evaluation_all_dispatches():
    """Verify run_evaluation with run_type='all' runs all sub-benchmarks."""
    with patch("app.services.eval_service.fetch_evaluation_samples") as mock_samples, \
         patch("app.services.eval_service.evaluate_with_ragas") as mock_ragas, \
         patch("app.services.eval_service.evaluate_with_deepeval") as mock_deepeval, \
         patch("app.services.eval_service.evaluate_fabrication_ab") as mock_fab, \
         patch("app.services.eval_service.record_evaluation_run") as mock_record:

        mock_samples.return_value = [{"sample": 1}]
        mock_ragas.return_value = {"faithfulness": 0.95, "answer_relevancy": 0.93}
        mock_deepeval.return_value = {"grounding_score": 0.96, "grant_priority_alignment": 0.94}
        mock_fab.return_value = {"relative_fabrication_reduction": 93.48}

        res = run_evaluation(run_type="all", sample_size=1)

        assert res["run_type"] == "all"
        assert "ragas" in res["metrics_json"]
        assert "deepeval" in res["metrics_json"]
        assert "fabrication_rate" in res["metrics_json"]
        assert res["metrics_json"]["summary"]["faithfulness"] == 0.95
        # Verify 3 individual runs recorded in DB
        assert mock_record.call_count == 3


def test_api_list_and_get_runs():
    """Verify API endpoints list_runs and get_run properly deserialize metrics_json."""
    with patch("app.api.evaluation.pool") as mock_pool:
        mock_pool.fetch_all.return_value = [
            {
                "id": "run-1",
                "run_type": "ragas",
                "metrics_json": json.dumps({"faithfulness": 0.95}),
                "sample_size": 2,
                "notes": "Test",
                "created_at": "2026-10-07T12:00:00Z",
            }
        ]
        mock_pool.fetch_one.return_value = {
            "id": "run-1",
            "run_type": "ragas",
            "metrics_json": json.dumps({"faithfulness": 0.95}),
            "sample_size": 2,
            "notes": "Test",
            "created_at": "2026-10-07T12:00:00Z",
        }

        runs = list_runs(_user=None)
        assert len(runs) == 1
        assert runs[0]["metrics_json"]["faithfulness"] == 0.95

        single = get_run("run-1", _user=None)
        assert single["id"] == "run-1"
        assert single["metrics_json"]["faithfulness"] == 0.95

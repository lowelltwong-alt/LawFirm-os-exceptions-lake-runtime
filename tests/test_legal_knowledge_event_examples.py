from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_legal_knowledge_example_does_not_embed_raw_real_payload() -> None:
    payload = json.loads((ROOT / "examples" / "legal_knowledge_retrieval_trace_event.json").read_text(encoding="utf-8"))
    boundary = payload["data_boundary"]
    assert boundary["contains_real_client_data"] is False
    assert boundary["contains_real_matter_data"] is False
    assert boundary["raw_document_payload_embedded"] is False
    assert payload["canonical_mutation_control"]["direct_mutation_attempted"] is False

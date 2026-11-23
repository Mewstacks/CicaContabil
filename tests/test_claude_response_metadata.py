import json
from unittest.mock import patch

import pytest

from apps.intelligence.gateway import generate_claude_fallback_completion


class ProviderResponse:
    status = 200
    headers = {"request-id": "req_synthetic12345"}

    def __init__(self, content, usage=None, stop_reason="end_turn"):
        self.body = json.dumps(
            {
                "model": "claude-haiku-5-5",
                "content": content,
                "usage": usage or {},
                "stop_reason": stop_reason,
            }
        ).encode()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def read(self, limit):
        return self.body[:limit]


@pytest.mark.parametrize(
    "model,minimal,disabled",
    [
        ("claude-haiku-5-5", True, True),
        ("claude-haiku-5-5", False, False),
        ("claude-haiku-4-5-20251001", True, False),
    ],
)
def test_bounded_classification_configures_supported_model_without_changing_other_uses(
    model,
    minimal,
    disabled,
):
    response = ProviderResponse(
        [
            {
                "type": "thinking",
                "thinking": "synthetic reasoning",
                "signature": "private-signature",
            },
            {"type": "text", "text": '{"suggestions":[]}'},
        ],
        usage={"input_tokens": 20, "output_tokens": 10},
    )
    observed = []
    with patch("apps.intelligence.gateway.urlopen", return_value=response) as http:
        result = generate_claude_fallback_completion(
            api_key="synthetic-only",
            model=model,
            question="Classify for review",
            company_name="Generic",
            conversation_context="",
            evidence=[],
            allow_full_data=False,
            minimal_reasoning=minimal,
            on_response_usage=observed.append,
        )
    sent = json.loads(http.call_args.args[0].data)
    assert http.call_count == 1 and sent["max_tokens"] == 420
    assert sent.get("thinking") == ({"type": "disabled"} if disabled else None)
    assert sent.get("output_config") == ({"effort": "low"} if disabled else None)
    assert result.content == '{"suggestions":[]}' and observed == [result]
    assert "private-signature" not in repr(result) and "synthetic reasoning" not in repr(result)


def test_empty_final_text_still_reports_usage_without_returning_thinking_or_retrying():
    response = ProviderResponse(
        [
            {"type": "thinking", "thinking": "", "signature": "private-signature"},
        ],
        usage={"input_tokens": 973, "output_tokens": 420},
        stop_reason="max_tokens",
    )
    observed = []
    with patch("apps.intelligence.gateway.urlopen", return_value=response) as http:
        result = generate_claude_fallback_completion(
            api_key="synthetic-only",
            model="claude-haiku-5-5",
            question="Classify",
            company_name="Generic",
            conversation_context="",
            evidence=[],
            allow_full_data=False,
            on_response_usage=observed.append,
        )
    assert result is None and http.call_count == 1
    assert observed[0].input_tokens == 973 and observed[0].output_tokens == 420
    assert observed[0].content == "" and observed[0].stop_reason == "max_tokens"
    assert "private-signature" not in repr(observed)


def test_response_usage_callback_never_receives_unbounded_or_untrusted_metadata():
    response = ProviderResponse(
        [{"type": "text", "text": "{}"}],
        usage={
            "input_tokens": -1,
            "output_tokens": "420",
            "cache_creation_input_tokens": 100_000_001,
        },
        stop_reason="untrusted text with spaces",
    )
    observed = []
    with patch("apps.intelligence.gateway.urlopen", return_value=response):
        generate_claude_fallback_completion(
            api_key="synthetic-only",
            model="claude-haiku-5-5",
            question="Classify",
            company_name="Generic",
            conversation_context="",
            evidence=[],
            allow_full_data=False,
            on_response_usage=observed.append,
        )
    assert observed[0].input_tokens == observed[0].output_tokens == 0
    assert observed[0].cache_creation_input_tokens == 0 and observed[0].stop_reason == ""

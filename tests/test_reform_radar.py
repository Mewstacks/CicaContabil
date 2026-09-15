from __future__ import annotations

from unittest.mock import patch
from urllib.error import URLError

import pytest

from apps.hub.models import ReformAlert, ReformSourceStatus
from apps.hub.reform import refresh_reform_source


class _Response:
    def __init__(self, body: bytes) -> None:
        self.body = body

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self, _size: int) -> bytes:
        return self.body


@pytest.mark.django_db
@patch("apps.hub.reform.urlopen")
def test_refreshing_an_official_source_is_idempotent(mocked_urlopen) -> None:
    mocked_urlopen.return_value = _Response(
        b'<html><h2><a href="/receitafederal/noticias/reforma">'
        b'Regras de IBS e CBS</a></h2><nav><a href="/">Ignorar</a></nav></html>'
    )

    created, updated = refresh_reform_source(ReformAlert.Source.RFB)
    repeat_created, repeat_updated = refresh_reform_source(ReformAlert.Source.RFB)

    assert (created, updated) == (1, 0)
    assert (repeat_created, repeat_updated) == (0, 0)
    alert = ReformAlert.objects.get(source=ReformAlert.Source.RFB)
    assert alert.relevance == ReformAlert.Relevance.REFORM
    assert alert.source_url == "https://www.gov.br/receitafederal/noticias/reforma"
    assert ReformSourceStatus.objects.get(source=ReformAlert.Source.RFB).last_error == ""


@pytest.mark.django_db
@patch("apps.hub.reform.urlopen", side_effect=URLError("offline"))
def test_a_source_failure_is_recorded_without_raising(_mocked_urlopen) -> None:
    assert refresh_reform_source(ReformAlert.Source.PLANALTO) == (0, 0)

    status = ReformSourceStatus.objects.get(source=ReformAlert.Source.PLANALTO)
    assert status.last_error

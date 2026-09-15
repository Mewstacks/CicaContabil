import json
from unittest.mock import patch, MagicMock
from urllib.error import URLError

import pytest
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.test import Client
from django.urls import reverse

from apps.common.cnpj import normalize_cnpj, lookup_company
from apps.platform.forms import LeadForm
from apps.platform.models import Lead


def test_numeric_and_alphanumeric_cnpj():
    assert normalize_cnpj('19.131.243/0001-97') == '19131243000197'
    assert normalize_cnpj('00.000.000/E08G-12') == '00000000E08G12'
    for invalid in ['00000000000000','19131243000198','https://evil.test','19A131243000197']:
        with pytest.raises(ValidationError):
            normalize_cnpj(invalid)


def test_registry_minimizes_data_and_caches():
    cache.clear()
    payload = {'cnpj':'19131243000197','razao_social':'Empresa exemplo','municipio':'São Paulo','uf':'SP','qsa':[{'nome_socio':'Do not retain'}],'ddd_telefone_1':'Do not retain'}
    response = MagicMock()
    response.__enter__.return_value.read.return_value = json.dumps(payload).encode()
    with patch('apps.common.cnpj.urlopen', return_value=response) as request:
        result = lookup_company('19131243000197')
        assert result['razao_social'] == 'Empresa exemplo'
        assert 'qsa' not in result and 'ddd_telefone_1' not in result
        assert lookup_company('19131243000197') == result
        assert request.call_count == 1
    cache.clear()
    with patch('apps.common.cnpj.urlopen', side_effect=URLError('offline')):
        assert lookup_company('19131243000197')['status'] == 'unavailable'


@pytest.mark.django_db
def test_three_required_fields_and_fallback_submission():
    form = LeadForm({'contact_name':'Pessoa Teste','contact_email':'person@example.test','cnpj':'19131243000197'})
    assert tuple(form.fields) == ('contact_name','contact_email','cnpj')
    assert form.is_valid(), form.errors
    with patch('apps.platform.forms.lookup_company', return_value={'status':'unavailable'}):
        lead = form.save()
    assert lead.cnpj == '19131243000197'
    assert lead.office_name == 'CNPJ 19131243000197'
    assert Lead.objects.count() == 1


@pytest.mark.django_db
def test_lookup_validation_csrf_and_rate_limit():
    cache.clear()
    client = Client()
    url = reverse('hub:proposal-cnpj')
    assert client.get(url).status_code == 405
    with patch('apps.hub.views.lookup_company') as lookup:
        assert client.post(url, {'cnpj':'invalid'}).status_code == 400
        lookup.assert_not_called()
    with patch('apps.hub.views.rate_limited', return_value=True):
        assert client.post(url, {'cnpj':'19131243000197'}).status_code == 429
    assert Client(enforce_csrf_checks=True).post(url, {'cnpj':'19131243000197'}).status_code == 403

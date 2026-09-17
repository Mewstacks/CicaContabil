import pytest

from apps.hub.models import OfficeProfile
from apps.integra.errors import IntegraConfigurationError
from apps.integra.parties import author_cnpj_for

pytestmark = pytest.mark.django_db


def test_author_is_the_office_cnpj(organization):
    OfficeProfile.objects.create(organization=organization, cnpj="68.340.160/0001-13")

    assert author_cnpj_for(organization) == "68340160000113"


def test_missing_office_cnpj_blocks_the_serpro_request(organization):
    OfficeProfile.objects.create(organization=organization, cnpj="")

    with pytest.raises(IntegraConfigurationError, match="CNPJ do escritório"):
        author_cnpj_for(organization)

"""T10.2: every read of the registry has a typed reader, or is a known legacy read."""

from __future__ import annotations

from apps.integra.catalog import SERVICES, EffectClass, service
from apps.integra.typed_registry import LEGACY_UNTYPED_READS, TYPED
from integra_fixtures import fixture_names, official_payload


def test_every_class_a_service_is_typed_or_a_known_legacy_read() -> None:
    reads = {spec.key for spec in SERVICES.values() if spec.effect_class is EffectClass.READ}

    assert len(reads) == 68
    assert reads - set(TYPED) == LEGACY_UNTYPED_READS
    assert set(TYPED) <= reads
    assert len(TYPED) == 59


def test_the_56_reads_of_the_spec_are_typed_by_this_epic() -> None:
    # 27 services of 10 systems + 29 parcelamento consultations (7 modalities x 4 + PARCSN 165).
    typed_now = {key for key in TYPED if not key.startswith("parcelamento.parcsn.")}
    parcsn_new = {"parcelamento.parcsn.pagamento"}
    assert len(typed_now) + len(parcsn_new) == 56


def test_request_models_are_absent_only_for_services_without_dados() -> None:
    for key, typed in TYPED.items():
        assert service(key).copilot_allowed
        assert callable(typed.read)
        if typed.request is not None:
            assert hasattr(typed.request, "to_dados")


def test_every_non_parcelamento_service_has_an_official_fixture_that_reads() -> None:
    for key, typed in TYPED.items():
        if key.startswith("parcelamento."):
            continue
        spec = service(key)
        names = fixture_names(f"{spec.id_sistema}.{spec.id_servico}")
        assert names, key
        for name in names:
            typed.read(official_payload(name))

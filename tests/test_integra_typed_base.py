"""T10.2: the strict, bounded engine behind the typed requests and readers."""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Annotated, Any

import pytest

from apps.integra.errors import IntegraPayloadError, IntegraRequestError
from apps.integra.typed.base import (
    MAX_ITEMS,
    Fmt,
    J,
    Model,
    Request,
    normalize_cpf,
    open_envelope,
)

BRT = timezone(timedelta(hours=-3))
PDF = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"


def b64(data: bytes) -> str:
    return base64.b64encode(data).decode()


def envelope(dados: Any, *, status: int = 200, mensagens: Any = None) -> dict[str, Any]:
    return {
        "status": status,
        "mensagens": [{"codigo": "[Sucesso-TESTE]", "texto": "ok"}]
        if mensagens is None
        else mensagens,
        "dados": json.dumps(dados) if not isinstance(dados, str) else dados,
    }


@dataclass(frozen=True, kw_only=True)
class Leaf(Model):
    name: Annotated[str, J("nome")]
    amount: Annotated[Decimal | None, J("valor")] = None


@dataclass(frozen=True, kw_only=True)
class Scalars(Model):
    text: Annotated[str, J("texto")]
    number: Annotated[int, J("numero")]
    money: Annotated[Decimal, J("dinheiro")]
    flag: Annotated[bool, J("marca")]
    note: Annotated[str | None, J("nota")] = None
    count: Annotated[int | None, J("quantidade")] = None


@dataclass(frozen=True, kw_only=True)
class Dates(Model):
    day: Annotated[date, J("dia", fmt=Fmt.DATE8)]
    moment: Annotated[datetime, J("momento", fmt=Fmt.DATETIME14)]
    iso_day: Annotated[date, J("diaIso", fmt=Fmt.ISO_DATE)]
    iso_moment: Annotated[datetime, J("momentoIso", fmt=Fmt.ISO_DATETIME)]
    br_day: Annotated[date, J("diaBr", fmt=Fmt.BR_DATE)]
    period: Annotated[int, J("periodo", fmt=Fmt.YEAR_MONTH)]
    maybe_day: Annotated[date | None, J("talvez", fmt=Fmt.DATE8)] = None


@dataclass(frozen=True, kw_only=True)
class Documents(Model):
    pdf: Annotated[bytes, J("pdf", fmt=Fmt.PDF)]
    xml: Annotated[bytes | None, J("xml", fmt=Fmt.XML)] = None
    resolution: Annotated[str | None, J("texto", fmt=Fmt.TEXT_B64)] = None


@dataclass(frozen=True, kw_only=True)
class Node(Model):
    name: Annotated[str, J("nome")]
    child: Annotated[Node | None, J("filho")] = None


@dataclass(frozen=True, kw_only=True)
class Tree(Model):
    title: Annotated[str, J("titulo")]
    leaf: Annotated[Leaf | None, J("folha")] = None
    leaves: Annotated[tuple[Leaf, ...], J("folhas")] = ()
    tags: Annotated[tuple[str, ...], J("etiquetas")] = ()
    free: Annotated[Any, J("livre")] = None
    parsed: Annotated[str | None, J("custom", parse=lambda raw: str(raw).upper())] = None


# ---- envelope ---------------------------------------------------------------------------


def test_the_envelope_exposes_status_messages_and_the_decoded_dados() -> None:
    reply = open_envelope(envelope({"a": 1}, mensagens=[{"codigo": "[Aviso-X-001]", "texto": "t"}]))

    assert reply.status == 200
    assert [(m.codigo, m.texto) for m in reply.mensagens] == [("[Aviso-X-001]", "t")]
    assert reply.dados == {"a": 1}


def test_dados_may_already_be_an_object_a_list_or_empty() -> None:
    assert open_envelope({"status": 200, "dados": {"a": 1}}).dados == {"a": 1}
    assert open_envelope({"status": 200, "dados": [1, 2]}).dados == [1, 2]
    assert open_envelope({"status": 200, "dados": ""}).dados is None
    assert open_envelope({"status": 200, "dados": None}).dados is None
    assert open_envelope({"status": 200}).dados is None


def test_only_the_accepted_statuses_open() -> None:
    assert open_envelope(envelope({}, status=202), accept=(200, 202)).status == 202
    with pytest.raises(IntegraPayloadError, match="status 202"):
        open_envelope(envelope({}, status=202))
    with pytest.raises(IntegraPayloadError, match="status"):
        open_envelope({"dados": "{}"})


@pytest.mark.parametrize(
    "payload",
    [
        [],
        "texto",
        {"status": 200, "dados": 12},
        {"status": 200, "dados": "{quebrado"},
        {"status": 200, "dados": "12"},
        {"status": 200, "dados": "x" * 2_100_000},
        {"status": 200, "dados": "{}", "mensagens": {"codigo": "x"}},
        {"status": 200, "dados": "{}", "mensagens": [1]},
        {"status": True, "dados": "{}"},
    ],
)
def test_an_unreadable_envelope_is_refused(payload: Any) -> None:
    with pytest.raises(IntegraPayloadError):
        open_envelope(payload)


# ---- scalars ----------------------------------------------------------------------------


def test_scalars_are_read_with_their_python_types() -> None:
    result = Scalars.parse(
        {"texto": "abc", "numero": "2018", "dinheiro": 1200.42, "marca": True, "extra": 1}
    )

    assert result == Scalars(text="abc", number=2018, money=Decimal("1200.42"), flag=True)
    lenient = {
        "texto": "", "numero": 3, "dinheiro": "10.50", "marca": "false", "nota": "",
        "quantidade": 7,
    }
    assert Scalars.parse(lenient) == Scalars(
        text="", number=3, money=Decimal("10.50"), flag=False, note=None, count=7
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("numero", True),
        ("numero", 1.5),
        ("numero", "12a"),
        ("dinheiro", True),
        ("dinheiro", "abc"),
        ("dinheiro", "NaN"),
        ("dinheiro", 1e30),
        ("marca", 1),
        ("marca", "talvez"),
        ("texto", 12),
        ("texto", "x" * 5000),
        ("texto", None),
    ],
)
def test_a_scalar_of_the_wrong_kind_is_refused_without_echoing_it(
    field: str, value: Any
) -> None:
    data: dict[str, Any] = {"texto": "a", "numero": 1, "dinheiro": 1, "marca": True}
    data[field] = value

    with pytest.raises(IntegraPayloadError) as error:
        Scalars.parse(data)

    assert field in str(error.value)
    if isinstance(value, str) and len(value) < 100:
        assert value not in str(error.value) or value == "a"


def test_a_missing_required_field_names_its_path() -> None:
    with pytest.raises(IntegraPayloadError, match=r"dados\.numero"):
        Scalars.parse({"texto": "a", "dinheiro": 1, "marca": True})
    with pytest.raises(IntegraPayloadError, match=r"dados deve ser um objeto"):
        Scalars.parse([1])


# ---- dates ------------------------------------------------------------------------------


def test_every_documented_date_format_is_read() -> None:
    result = Dates.parse(
        {
            "dia": 20230131,
            "momento": "20260408123015",
            "diaIso": "2019-09-01",
            "momentoIso": "2019-01-01T00:00:00-03:00",
            "diaBr": "31/01/2023",
            "periodo": 202304,
        }
    )

    assert result.day == date(2023, 1, 31)
    assert result.moment == datetime(2026, 4, 8, 12, 30, 15, tzinfo=BRT)
    assert result.iso_day == date(2019, 9, 1)
    assert result.iso_moment == datetime(2019, 1, 1, tzinfo=BRT)
    assert result.br_day == date(2023, 1, 31)
    assert result.period == 202304
    assert result.maybe_day is None


def test_an_iso_moment_without_offset_is_brasilia_time_and_z_is_utc() -> None:
    base = {
        "dia": "20230131", "momento": 20260408123015, "diaIso": "2019-09-01",
        "diaBr": "01/02/2023", "periodo": "202304",
    }

    naive = Dates.parse({**base, "momentoIso": "2022-08-08T00:00:00"})
    zulu = Dates.parse({**base, "momentoIso": "2022-08-08T03:00:00.000Z"})

    assert naive.iso_moment == datetime(2022, 8, 8, tzinfo=BRT)
    assert zulu.iso_moment == naive.iso_moment
    assert naive.day == date(2023, 1, 31)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("dia", 20231301),
        ("dia", "2023013"),
        ("dia", "abcdefgh"),
        ("momento", "20261301120000"),
        ("diaIso", "2019-02-30"),
        ("diaIso", "01/02/2019"),
        ("diaBr", "2019-02-01"),
        ("periodo", 202313),
        ("periodo", 1999),
        ("periodo", True),
    ],
)
def test_an_invalid_date_is_refused(field: str, value: Any) -> None:
    data: dict[str, Any] = {
        "dia": 20230131, "momento": 20260408123015, "diaIso": "2019-09-01",
        "momentoIso": "2019-01-01T00:00:00", "diaBr": "31/01/2023", "periodo": 202304,
    }
    data[field] = value

    with pytest.raises(IntegraPayloadError, match=field):
        Dates.parse(data)


def test_zero_or_empty_dates_are_absent_when_optional_and_refused_when_required() -> None:
    base = {
        "dia": 20230131, "momento": 20260408123015, "diaIso": "2019-09-01",
        "momentoIso": "2019-01-01T00:00:00", "diaBr": "31/01/2023", "periodo": 202304,
    }
    for empty in (None, "", 0, "00000000"):
        assert Dates.parse({**base, "talvez": empty}).maybe_day is None
    with pytest.raises(IntegraPayloadError, match="dia"):
        Dates.parse({**base, "dia": 0})


# ---- documents --------------------------------------------------------------------------


def test_embedded_documents_are_decoded_and_validated() -> None:
    xml = b'<?xml version="1.0"?><declaracao><a>1</a></declaracao>'

    result = Documents.parse(
        {"pdf": b64(PDF), "xml": b64(xml), "texto": b64("Resolução do caixa".encode())}
    )

    assert result.pdf == PDF
    assert result.xml == xml
    assert result.resolution == "Resolução do caixa"
    assert Documents.parse({"pdf": b64(PDF)[:30] + "\n" + b64(PDF)[30:]}).pdf == PDF


@pytest.mark.parametrize(
    "value",
    [
        "não é base64!",
        b64(b"<html>fake</html>"),
        b64(b"%PDF-1.4\ntruncated"),
        "",
        None,
        12,
    ],
)
def test_a_document_that_is_not_a_real_pdf_is_refused(value: Any) -> None:
    with pytest.raises(IntegraPayloadError, match="pdf"):
        Documents.parse({"pdf": value})


def test_a_document_above_the_size_limit_is_refused() -> None:
    huge = b64(b"%PDF-1.4\n" + b"0" * 9_000_000 + b"%%EOF")

    with pytest.raises(IntegraPayloadError, match="excede") as error:
        Documents.parse({"pdf": huge})

    assert len(str(error.value)) < 200


@pytest.mark.parametrize(
    "xml",
    [
        b"nao e xml",
        b"<a><b></a>",
        b'<?xml version="1.0"?><!DOCTYPE a [<!ENTITY x "y">]><a>&x;</a>',
    ],
)
def test_an_xml_document_must_be_well_formed_and_free_of_entities(xml: bytes) -> None:
    with pytest.raises(IntegraPayloadError, match="xml"):
        Documents.parse({"pdf": b64(PDF), "xml": b64(xml)})


# ---- structure --------------------------------------------------------------------------


def test_nested_objects_lists_and_free_values_are_read() -> None:
    result = Tree.parse(
        {
            "titulo": "t",
            "folha": {"nome": "a", "valor": 1.5},
            "folhas": [{"nome": "b"}, {"nome": "c", "valor": "2"}],
            "etiquetas": ["x", "y"],
            "livre": {"qualquer": [1, 2]},
            "custom": "abc",
        }
    )

    assert result.leaf == Leaf(name="a", amount=Decimal("1.5"))
    assert result.leaves == (Leaf(name="b"), Leaf(name="c", amount=Decimal(2)))
    assert result.tags == ("x", "y")
    assert result.free == {"qualquer": [1, 2]}
    assert result.parsed == "ABC"
    assert Tree.parse({"titulo": "t", "folhas": None, "etiquetas": ""}) == Tree(title="t")


@pytest.mark.parametrize(
    ("data", "path"),
    [
        ({"titulo": "t", "folha": [1]}, r"dados\.folha"),
        ({"titulo": "t", "folhas": {"nome": "a"}}, r"dados\.folhas"),
        ({"titulo": "t", "folhas": [{"nome": "a"}, {"valor": 1}]}, r"dados\.folhas\[1\]\.nome"),
        ({"titulo": "t", "folhas": [1]}, r"dados\.folhas\[0\]"),
        ({"titulo": "t", "etiquetas": [1]}, r"dados\.etiquetas\[0\]"),
        ({"titulo": "t", "folhas": [None]}, r"dados\.folhas\[0\]"),
    ],
)
def test_structure_errors_carry_the_path_of_the_offending_item(data: Any, path: str) -> None:
    with pytest.raises(IntegraPayloadError, match=path):
        Tree.parse(data)


def test_lists_and_depth_are_bounded() -> None:
    with pytest.raises(IntegraPayloadError, match="limite"):
        Tree.parse({"titulo": "t", "etiquetas": ["x"] * (MAX_ITEMS + 1)})
    nested: Any = {"nome": "a"}
    for _ in range(12):
        nested = {"nome": "a", "filho": nested}
    with pytest.raises(IntegraPayloadError, match="profund"):
        Node.parse(nested)
    shallow: Any = {"nome": "a"}
    for _ in range(4):
        shallow = {"nome": "a", "filho": shallow}
    assert Node.parse(shallow).child is not None


def test_a_custom_converter_failure_is_a_payload_error() -> None:
    @dataclass(frozen=True, kw_only=True)
    class Strict(Model):
        value: Annotated[int, J("v", parse=lambda raw: int(raw) // 0)]

    with pytest.raises(IntegraPayloadError, match=r"dados\.v"):
        Strict.parse({"v": 3})


def test_an_unsupported_annotation_is_a_programming_error() -> None:
    @dataclass(frozen=True, kw_only=True)
    class Broken(Model):
        value: Annotated[dict[str, int], J("v")]

    with pytest.raises(TypeError, match=r"Broken\.value"):
        Broken.parse({"v": {}})


# ---- requests ---------------------------------------------------------------------------


@dataclass(frozen=True, kw_only=True)
class Interval(Request):
    start: Annotated[date | None, J("dataInicial", fmt=Fmt.ISO_DATE)] = None
    end: Annotated[date | None, J("dataFinal", fmt=Fmt.ISO_DATE)] = None


@dataclass(frozen=True, kw_only=True)
class Ask(Request):
    year: Annotated[str, J("anoCalendario", pattern=r"\d{4}")]
    period: Annotated[int | None, J("periodoApuracao", fmt=Fmt.YEAR_MONTH, text=True)] = None
    page: Annotated[int, J("tamanhoDaPagina", ge=1, le=100)] = 10
    amount: Annotated[Decimal | None, J("valorImposto", fmt=Fmt.MONEY_STR)] = None
    ceiling: Annotated[Decimal | None, J("teto")] = None
    stamp: Annotated[datetime | None, J("vencimento", fmt=Fmt.ISO_DATETIME)] = None
    day: Annotated[date | None, J("data", fmt=Fmt.DATE8)] = None
    moment: Annotated[datetime | None, J("momento", fmt=Fmt.DATETIME14)] = None
    br_day: Annotated[date | None, J("dataBr", fmt=Fmt.BR_DATE)] = None
    cnpj: Annotated[str | None, J("cnpjPrestador", fmt=Fmt.CNPJ)] = None
    cpf: Annotated[str | None, J("cpf", fmt=Fmt.CPF)] = None
    ni: Annotated[str | None, J("ni", fmt=Fmt.NI)] = None
    flag: Annotated[bool | None, J("confirma")] = None
    interval: Annotated[Interval | None, J("intervalo")] = None
    codes: Annotated[tuple[str, ...], J("codigos")] = ()
    document: Annotated[bytes | None, J("xml", fmt=Fmt.XML)] = None


def test_a_request_builds_its_dados_with_documented_names_and_formats() -> None:
    request = Ask(
        year="2018",
        period=201801,
        amount=Decimal("1000"),
        ceiling=Decimal("600.5"),
        stamp=datetime(2018, 1, 31, 10, 30, tzinfo=BRT),
        day=date(2023, 1, 5),
        moment=datetime(2026, 4, 8, 12, 30, 15, tzinfo=BRT),
        br_day=date(2023, 1, 5),
        cnpj="11.222.333/0001-81",
        cpf="529.982.247-25",
        ni="52998224725",
        flag=False,
        interval=Interval(start=date(2019, 9, 1)),
        codes=("9999", "1162"),
        document=b"<a/>",
    )

    assert request.to_dados() == {
        "anoCalendario": "2018",
        "periodoApuracao": "201801",
        "tamanhoDaPagina": 10,
        "valorImposto": "1000.00",
        "teto": 600.5,
        "vencimento": "2018-01-31T10:30:00",
        "data": "20230105",
        "momento": "20260408123015",
        "dataBr": "05/01/2023",
        "cnpjPrestador": "11222333000181",
        "cpf": "52998224725",
        "ni": "52998224725",
        "confirma": False,
        "intervalo": {"dataInicial": "2019-09-01"},
        "codigos": ["9999", "1162"],
        "xml": base64.b64encode(b"<a/>").decode(),
    }
    assert Ask(year="2018").to_dados() == {"anoCalendario": "2018", "tamanhoDaPagina": 10}


@pytest.mark.parametrize(
    "kwargs",
    [
        {"year": "18"},
        {"year": "2018", "period": 202313},
        {"year": "2018", "page": 0},
        {"year": "2018", "page": 101},
        {"year": "2018", "amount": Decimal("10.001")},
        {"year": "2018", "cnpj": "11.222.333/0001-82"},
        {"year": "2018", "cpf": "123.456.789-00"},
        {"year": "2018", "ni": "123"},
        {"year": "2018", "codes": ("x" * 5000,)},
    ],
)
def test_an_invalid_request_is_refused_before_anything_is_sent(kwargs: dict[str, Any]) -> None:
    with pytest.raises(IntegraRequestError):
        Ask(**kwargs)


def test_an_alphanumeric_cnpj_is_accepted_in_a_request() -> None:
    # The alphanumeric CNPJ of the official SICALC example (retorno_consolidado_alfa).
    alpha = "YV9IAOAXNTRV65"
    assert Ask(year="2018", cnpj="YV.9IA.OAX/NTRV-65").to_dados()["cnpjPrestador"] == alpha
    assert Ask(year="2018", ni=alpha).to_dados()["ni"] == alpha


def test_cpf_numbers_are_checked() -> None:
    assert normalize_cpf("529.982.247-25") == "52998224725"
    for bad in ("111.111.111-11", "123", "529.982.247-26", "abc"):
        with pytest.raises(IntegraRequestError):
            normalize_cpf(bad)


def test_a_dados_whose_root_is_a_list_is_read_item_by_item() -> None:
    assert Leaf.parse_many([{"nome": "a"}, {"nome": "b", "valor": 2}]) == (
        Leaf(name="a"),
        Leaf(name="b", amount=Decimal(2)),
    )
    assert Leaf.parse_many([]) == ()
    with pytest.raises(IntegraPayloadError, match=r"dados\[1\]\.nome"):
        Leaf.parse_many([{"nome": "a"}, {}])
    with pytest.raises(IntegraPayloadError, match="uma lista"):
        Leaf.parse_many({"nome": "a"})
    with pytest.raises(IntegraPayloadError, match="limite"):
        Leaf.parse_many([{"nome": "a"}] * (MAX_ITEMS + 1))

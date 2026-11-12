"""Synthetic fiscal capture: preserve original facts and require semantic review."""

from __future__ import annotations

import base64
import hashlib
import io
import json
import sqlite3
from copy import deepcopy
from datetime import date
from uuid import uuid4

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.hub.models import (
    ClientCompany,
    FinancialAccount,
    JournalEntry,
    LedgerAccount,
    ProductModule,
    ReconciliationSourceFile,
    ReconciliationTitleAllocation,
    ReconciliationTitleSnapshot,
)
from apps.intelligence.agent_scope import build_portfolio_scope
from apps.intelligence.models import EdgeAgent, NativeTitleCollection
from apps.intelligence.native_title_contract import (
    COVERAGE,
    FAMILIES,
    ROOT,
    VERSION,
    canonical_hash,
    manifest,
    validate_scope,
    validate_snapshot,
)
from apps.organizations.models import Membership
from apps.platform.models import TenantContract
from test_native_ledger import post

pytestmark = pytest.mark.django_db


def raw_row(contract, family, kind):
    result = {}
    for spec in contract["queries"][f"{family}_{kind}"]["columns"]:
        if spec["nullable"]:
            value = None
        elif spec["type"] == "int":
            value = 0
        elif spec["type"] == "date":
            value = "2026-09-12"
        elif spec["type"] == "decimal":
            value = "0.00"
        else:
            value = ""
        result[spec["name"]] = value
    return result


def sample(capture_id=None):
    contract = manifest()
    families = []
    for name in FAMILIES:
        spec = contract["families"][name]
        parts, payments, links = [], [], []
        if name != "servicos":
            part = raw_row(contract, name, "installments")
            part.update(codi_emp=212, origem_reg=0)
            part[spec["note_field"]] = 10
            part[spec["installment_field"]] = 1
            part[spec["due_field"]] = "2026-10-02" if name == "saidas" else "2026-09-20"
            for prefix, value in [("vlor_", "100.00"), ("vbru_", "105.00")]:
                field = next(c for c in part if c.startswith(prefix))
                part[field] = value
            title_field = next(c for c in part if c.startswith("numero_titulo_"))
            part[title_field] = "0001/A  "
            parts.append(part)
            components = (
                [(1, 1, "40.00"), (1, 2, "30.00"), (9, 1, "0.00")]
                if name == "entradas"
                else [(1, 1, "-2.00")]
            )
            for index, (kind, number, amount) in enumerate(components):
                payment = raw_row(contract, name, "payments")
                payment.update(codi_emp=212, origem_reg=0)
                payment[spec["note_field"]] = 10
                payment[spec["installment_field"]] = 1
                payment[spec["payment_date_field"]] = "2026-09-12"
                payment[spec["payment_type_field"]] = kind
                payment[spec["payment_number_field"]] = number
                payment[next(c for c in payment if c.startswith("vpag_"))] = amount
                payments.append(payment)
                if kind == 9:
                    continue
                link = raw_row(contract, name, "accounting_links")
                link.update(
                    codi_emp=999 if name == "saidas" else 212,
                    fili_lan=212,
                    nume_lan=index + 1,
                    grupo=1,
                )
                for field in [
                    spec["note_field"],
                    spec["installment_field"],
                    spec["payment_date_field"],
                    spec["payment_type_field"],
                    spec["payment_number_field"],
                ]:
                    link[field] = payment[field]
                links.append(link)
        control = {
            "due_installments": int(name == "entradas"),
            "selected_installments": len(parts),
            "payments": len(payments),
            "accounting_links": len(links),
            "missing_headers": 0,
            "missing_installments": 0,
        }
        families.append(
            {
                "name": name,
                "control": control,
                "installments": parts,
                "payments": payments,
                "accounting_links": links,
            }
        )
    scope = validate_scope(
        {
            "capture_id": str(capture_id or uuid4()),
            "company_code": 212,
            "comparison_bank_account_code": 8,
            "period_start": "2026-09-01",
            "period_end_exclusive": "2026-10-01",
            "expected_counts": {
                f["name"]: {
                    key: f["control"][key]
                    for key in ("due_installments", "payments", "accounting_links")
                }
                for f in families
            },
        }
    )
    return scope, {
        "version": VERSION,
        "scope_revision": canonical_hash(scope),
        "coverage": deepcopy(COVERAGE),
        "families": families,
    }


def encode(data):
    return json.dumps(data, ensure_ascii=False).encode()


@pytest.fixture
def fiscal(organization, user, membership, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "private"
    settings.EDGE_AGENT_MTLS_REQUIRED = False
    ProductModule.objects.create(organization=organization, code="reconciliation", enabled=True)
    TenantContract.objects.create(
        organization=organization, status="active", selected_modules=["reconciliation"]
    )
    company = ClientCompany.objects.create(
        organization=organization, name="Sintética", dominio_code="212"
    )
    account = FinancialAccount.objects.create(
        organization=organization,
        company=company,
        name="Comparação sintética",
        account_reference="SYN-8",
        ledger_code="8",
    )
    agent = EdgeAgent.objects.create(
        organization=organization,
        label="Sintético",
        fingerprint="test",
        shared_secret="synthetic-fiscal-only",
        is_official=True,
        sync_scope=build_portfolio_scope(
            organization=organization,
            start=date(2026, 9, 1),
            end=date(2026, 9, 30),
            company_status_map={"A": True},
            active_only=True,
        ),
    )
    scope, data = sample()
    scope_file = tmp_path / "scope.json"
    scope_file.write_bytes(encode(scope))
    options = {
        "organization": str(organization.pk),
        "agent": str(agent.pk),
        "account": str(account.pk),
        "actor": str(user.pk),
        "scope": str(scope_file),
        "evidence": "Synthetic financial capture approval",
    }
    preview = io.StringIO()
    call_command("queue_contad_native_titles", **options, stdout=preview)
    assert json.loads(preview.getvalue())["queued"] is False
    assert not NativeTitleCollection.objects.exists()
    call_command(
        "queue_contad_native_titles", **options, allow_financial_capture=True, stdout=io.StringIO()
    )
    return agent, account, user, NativeTitleCollection.objects.get(), data, options


def complete(agent, job, data, **kwargs):
    content = encode(data)
    return post(
        agent,
        "agent-v2-titles-complete",
        {
            "scope_revision": job.scope_revision,
            "contract_hash": job.contract_hash,
            "content_sha256": hashlib.sha256(content).hexdigest(),
            "content_base64": base64.b64encode(content).decode(),
        },
        job=job,
        **kwargs,
    )


def test_raw_capture_round_trip_never_normalizes_or_posts(fiscal):
    agent, account, _, job, data, options = fiscal
    queued = post(agent, "agent-v2-titles-next", {"version": "1.0.9"})
    assert queued.status_code == 200 and queued.json()["job"]["id"] == str(job.pk)
    response = complete(agent, job, data)
    assert response.status_code == 200, response.content
    assert response.json()["state"] == "captured"
    assert response.json()["result"]["requires_semantic_review"] is True
    job.refresh_from_db()
    source = job.source_file
    assert source.financial_account == account and source.origin == "obligation"
    with source.content.open("rb") as stream:
        original = stream.read()
    assert original == encode(data)
    assert validate_snapshot(original, job.scope) == data
    assert b'"-2.00"' in original and b'"0.00"' in original and b"0001/A  " in original
    assert complete(agent, job, data).json() == response.json()
    call_command(
        "queue_contad_native_titles", **options, allow_financial_capture=True, stdout=io.StringIO()
    )
    assert NativeTitleCollection.objects.count() == ReconciliationSourceFile.objects.count() == 1
    for model in [
        JournalEntry,
        LedgerAccount,
        ReconciliationTitleSnapshot,
        ReconciliationTitleAllocation,
    ]:
        assert not model.objects.exists()
    pending = post(agent, "agent-v2-titles-next", {"version": "1.0.9"}).json()
    assert pending == {"job": None, "review_required": True}


@pytest.mark.parametrize(
    "change",
    [
        "company",
        "part_missing",
        "part_duplicate",
        "payment_duplicate",
        "payment_type_key",
        "payment_sequence_key",
        "payment_date",
        "extra_part",
        "wrong_link_company",
        "link_duplicate",
        "count",
        "coverage",
        "float_amount",
        "extra_field",
    ],
)
def test_invalid_source_is_rejected_in_full(fiscal, change):
    agent, _, _, job, data, _ = fiscal
    f = data["families"][0]
    if change == "company":
        f["installments"][0]["codi_emp"] = 999
    elif change == "part_missing":
        f["installments"] = []
        f["control"]["selected_installments"] = 0
    elif change == "part_duplicate":
        f["installments"] *= 2
        f["control"]["selected_installments"] = 2
    elif change == "payment_duplicate":
        f["payments"][1] = deepcopy(f["payments"][0])
    elif change == "payment_type_key":
        f["accounting_links"][0]["tipo_entp"] = 2
    elif change == "payment_sequence_key":
        f["accounting_links"][1]["nropag_entp"] = 99
    elif change == "payment_date":
        f["payments"][0]["pgto_entp"] = "2026-10-01"
    elif change == "extra_part":
        extra = deepcopy(f["installments"][0])
        extra.update(parc_entp=2, vcto_entp="2026-10-10")
        f["installments"].append(extra)
        f["control"]["selected_installments"] = 2
    elif change == "wrong_link_company":
        f["accounting_links"][0]["fili_lan"] = 999
    elif change == "link_duplicate":
        f["accounting_links"][1] = deepcopy(f["accounting_links"][0])
    elif change == "count":
        f["control"]["payments"] += 1
    elif change == "coverage":
        data["coverage"]["settlements_complete"] = 0
    elif change == "float_amount":
        f["payments"][0]["vpag_entp"] = 40.0
    elif change == "extra_field":
        f["payments"][0]["inferred_bank_account"] = 8
    response = complete(agent, job, data)
    assert response.status_code == 400, response.content
    assert not ReconciliationSourceFile.objects.exists()
    job.refresh_from_db()
    assert job.state == "queued" and job.source_file is None


@pytest.mark.parametrize(
    "revocation", ["agent", "official", "role", "user", "contract", "module", "account"]
)
def test_capture_revalidates_current_authority(fiscal, revocation):
    agent, account, actor, job, data, _ = fiscal
    if revocation == "agent":
        EdgeAgent.objects.filter(pk=agent.pk).update(status="revoked", is_official=False)
    elif revocation == "official":
        EdgeAgent.objects.filter(pk=agent.pk).update(is_official=False)
    elif revocation == "role":
        Membership.objects.filter(user=actor, organization=account.organization).update(
            role="auditor"
        )
    elif revocation == "user":
        actor.is_active = False
        actor.save(update_fields=["is_active"])
    elif revocation == "contract":
        TenantContract.objects.filter(organization=account.organization).update(status="suspended")
    elif revocation == "module":
        ProductModule.objects.filter(
            organization=account.organization, code="reconciliation"
        ).update(enabled=False)
    elif revocation == "account":
        FinancialAccount.objects.filter(pk=account.pk).update(active=False)
    assert complete(agent, job, data).status_code in (401, 409)
    assert not ReconciliationSourceFile.objects.exists()


def test_signature_protocol_and_agent_isolation(fiscal):
    agent, _, _, job, data, _ = fiscal
    assert complete(agent, job, data, secret="wrong").status_code == 401
    assert complete(agent, job, data, protocol="scoped-v3").status_code == 401
    assert complete(agent, job, data, secure=False).status_code == 401
    assert post(agent, "agent-v2-titles-next", {"version": "1.0.8"}).status_code == 400
    assert not ReconciliationSourceFile.objects.exists()


def test_rollback_removes_file_and_replay_checks_original(fiscal, monkeypatch, settings):
    agent, _, _, job, data, _ = fiscal

    def failure(**kwargs):
        raise RuntimeError("synthetic audit failure")

    with monkeypatch.context() as patch:
        patch.setattr("apps.intelligence.native_titles.record_event", failure)
        with pytest.raises(RuntimeError, match="synthetic audit"):
            complete(agent, job, data)
    assert not ReconciliationSourceFile.objects.exists()
    assert not list(settings.MEDIA_ROOT.rglob("*.json"))
    assert complete(agent, job, data).status_code == 200
    job.refresh_from_db()
    with job.source_file.content.open("wb") as stream:
        stream.write(b"tampered")
    assert complete(agent, job, data).status_code == 409
    assert ReconciliationSourceFile.objects.count() == 1


def test_capture_identity_cannot_be_reused_with_other_context(fiscal):
    _, _, _, _, _, options = fiscal
    with pytest.raises(CommandError, match="outro contexto"):
        call_command(
            "queue_contad_native_titles",
            **dict(options, evidence="Changed approval"),
            allow_financial_capture=True,
            stdout=io.StringIO(),
        )


def test_replay_cannot_bypass_semantic_review_with_changed_result(fiscal):
    agent, _, _, job, data, _ = fiscal
    assert complete(agent, job, data).status_code == 200
    job.refresh_from_db()
    NativeTitleCollection.objects.filter(pk=job.pk).update(
        result=dict(job.result, requires_semantic_review=False)
    )
    assert complete(agent, job, data).status_code == 409
    assert not ReconciliationTitleSnapshot.objects.exists()
    assert not JournalEntry.objects.exists()


@pytest.mark.parametrize("code", ["source_changed", "source_unavailable", "source_contract"])
def test_transient_failures_retry_same_job_and_contract_fault_stops(fiscal, code):
    agent, _, _, job, data, _ = fiscal
    response = post(
        agent,
        "agent-v2-titles-failure",
        {
            "scope_revision": job.scope_revision,
            "contract_hash": job.contract_hash,
            "code": code,
        },
        job=job,
    )
    assert response.status_code == 200
    job.refresh_from_db()
    assert job.error_code == code and not ReconciliationSourceFile.objects.exists()
    poll = post(agent, "agent-v2-titles-next", {"version": "1.0.9"}).json()
    if code == "source_contract":
        assert job.state == "review" and poll == {"job": None, "review_required": True}
        assert complete(agent, job, data).status_code == 409
    else:
        assert job.state == "queued" and poll["job"]["id"] == str(job.pk)
        assert complete(agent, job, data).status_code == 200


def test_unscoped_or_replacement_agent_cannot_claim_pending_capture(fiscal):
    agent, account, _, job, data, _ = fiscal
    EdgeAgent.objects.filter(pk=agent.pk).update(sync_scope={})
    assert complete(agent, job, data).status_code == 401
    EdgeAgent.objects.filter(pk=agent.pk).update(is_official=False)
    replacement = EdgeAgent.objects.create(
        organization=account.organization,
        label="Replacement synthetic",
        fingerprint="other",
        shared_secret="another-synthetic-only",
        is_official=True,
        sync_scope=agent.sync_scope,
    )
    assert complete(replacement, job, data).status_code == 404
    assert not ReconciliationSourceFile.objects.exists()


@pytest.mark.django_db(transaction=True)
def test_concurrent_capture_retry_keeps_one_private_file_and_audit(fiscal):
    from concurrent.futures import ThreadPoolExecutor

    from django.db import close_old_connections, connection

    from apps.audit.models import AuditEvent

    if connection.vendor != "postgresql":
        pytest.skip("Requires independent PostgreSQL transactions and row locks")
    agent, _, _, job, data, _ = fiscal

    def send():
        close_old_connections()
        try:
            response = complete(agent, job, data)
            return response.status_code, response.json()
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda _: send(), range(2)))
    assert responses[0] == responses[1] and responses[0][0] == 200
    assert ReconciliationSourceFile.objects.count() == 1
    assert (
        AuditEvent.objects.filter(
            action="intelligence.native_titles_captured", target_id=str(job.pk)
        ).count()
        == 1
    )
    assert not ReconciliationTitleSnapshot.objects.exists() and not JournalEntry.objects.exists()


def test_embedded_query_manifest_detects_local_query_tampering(tmp_path, monkeypatch):
    import shutil

    import apps.intelligence.native_title_contract as contract

    shutil.copytree(ROOT, tmp_path / "contract")
    monkeypatch.setattr(contract, "ROOT", tmp_path / "contract")
    assert contract.contract_hash()
    p = tmp_path / "contract" / "entradas_payments.sql"
    p.write_text(p.read_text() + " ")
    with pytest.raises(ValueError, match="contract_invalid"):
        contract.contract_hash()


def test_duplicate_json_and_nonliteral_decimals_are_rejected():
    scope, data = sample()
    assert validate_snapshot(encode(data), scope) == data
    raw = encode(data).replace(b'"version":', b'"version":"duplicate","version":', 1)
    with pytest.raises(ValueError, match="json"):
        validate_snapshot(raw, scope)
    for invalid in ["1.001", "1e2", "NaN", "999999999999.00", True]:
        bad = deepcopy(data)
        bad["families"][0]["payments"][0]["vpag_entp"] = invalid
        with pytest.raises(ValueError):
            validate_snapshot(encode(bad), scope)


def test_fixed_sql_union_and_fiscal_company_keys_execute_against_synthetic_rows():
    contract = manifest()
    scope, data = sample()
    with sqlite3.connect(":memory:") as db:
        for family in FAMILIES:
            spec = contract["families"][family]
            # Fixed synthetic table names; no input participates in SQL construction.
            table = "ef" + family
            db.execute(
                f"CREATE TABLE {table}(codi_emp INTEGER,{spec['note_field']} INTEGER,"
                f"PRIMARY KEY(codi_emp,{spec['note_field']}))"
            )
            db.execute(f"INSERT INTO {table} VALUES(212,10)")
            f = next(x for x in data["families"] if x["name"] == family)
            for kind, suffix in [
                ("installments", "par"),
                ("payments", "pag"),
                ("accounting_links", "pag_lancto"),
            ]:
                columns = contract["queries"][family + "_" + kind]["columns"]
                fields = ",".join(
                    c["name"] + (" INTEGER" if c["type"] == "int" else " TEXT") for c in columns
                )
                db.execute(f"CREATE TABLE {table + suffix}({fields})")
                marks = ",".join("?" for _ in columns)
                for row in f[kind]:
                    db.execute(
                        f"INSERT INTO {table + suffix} VALUES({marks})",
                        [row[c["name"]] for c in columns],
                    )
            for kind in ("control", "installments", "payments", "accounting_links"):
                query = contract["queries"][family + "_" + kind]
                sql = (
                    (ROOT / query["file"])
                    .read_text()
                    .replace("TOP 50001 ", "")
                    .replace("bethadba.", "")
                )
                values = {
                    "company": 212,
                    "start": scope["period_start"],
                    "end": scope["period_end_exclusive"],
                }
                rows = db.execute(sql, [values[k] for k in query["parameters"]]).fetchall()
                actual = [
                    dict(zip([c["name"] for c in query["columns"]], row, strict=True))
                    for row in rows
                ]
                assert actual == ([f["control"]] if kind == "control" else f[kind])

"""Montagem comum dos testes Django do Contraprova: escritório, módulo ligado e arquivos."""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import date
from tempfile import TemporaryDirectory
from typing import Any

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.crosscheck import agent, services
from apps.crosscheck.engine.tools import SPED_XML, UF_DOMINIO
from apps.crosscheck.models import CrosscheckAgentJob, CrosscheckRun
from apps.crosscheck.synthetic import (
    DocSpec,
    EfdSpec,
    NfeSpec,
    build_efd,
    build_nfe_xml,
    build_zip,
    make_cnpj,
    make_key,
)
from apps.hub.models import ClientCompany, Connector, ProductModule
from apps.intelligence.agents import issue_enrollment, redeem_enrollment
from apps.organizations.models import Membership, Organization

EMPRESA = make_cnpj("12345678", "0001")
FORNECEDOR = make_cnpj("98765432", "0001")
OUTRA = make_cnpj("55555555", "0001")
COMPETENCIA = "2026-09"


def mask(cnpj: str) -> str:
    return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"


def chave(numero: int, *, emit: str = FORNECEDOR, model: str = "55") -> str:
    return make_key(cnpj=emit, number=numero, model=model)


def doc(numero: int, **campos: Any) -> DocSpec:
    return DocSpec(number=numero, key=chave(numero), **campos)


def nfe(numero: int, **campos: Any) -> NfeSpec:
    campos.setdefault("emit_cnpj", FORNECEDOR)
    campos.setdefault("dest_cnpj", EMPRESA)
    return NfeSpec(key=chave(numero, emit=campos["emit_cnpj"]), number=numero, **campos)


def sped_upload(
    docs: list[DocSpec], *, name: str = "sped.txt", cnpj: str = EMPRESA, **opcoes: Any
) -> SimpleUploadedFile:
    spec = {k: opcoes.pop(k) for k in ("dt_ini", "dt_fin") if k in opcoes}
    return SimpleUploadedFile(
        name, build_efd(EfdSpec(cnpj=cnpj, docs=docs, **spec), **opcoes), "text/plain"
    )


def zip_upload(*notas: NfeSpec, name: str = "notas.zip") -> SimpleUploadedFile:
    arquivos = {f"nota-{item.number}.xml": build_nfe_xml(item) for item in notas}
    return SimpleUploadedFile(name, build_zip(arquivos), "application/zip")


def xml_upload(item: NfeSpec) -> SimpleUploadedFile:
    return SimpleUploadedFile(f"nota-{item.number}.xml", build_nfe_xml(item), "text/xml")


class CrosscheckCase(TestCase):
    """Escritório com o Contraprova ligado, um dono logado e uma empresa na carteira."""

    def setUp(self) -> None:
        self.enterContext(override_settings(MEDIA_ROOT=self.enterContext(TemporaryDirectory())))
        self.office = Organization.objects.create(name="Escritório Teste", slug="escritorio-teste")
        self.user = User.objects.create_user(email="dono@example.com", password="uma-senha-longa")
        self.membership = Membership.objects.create(
            organization=self.office, user=self.user, role=Membership.Role.OWNER
        )
        self.company = ClientCompany.objects.create(
            organization=self.office,
            name="Padaria Central",
            cnpj_masked=mask(EMPRESA),
            dominio_code="25",
        )
        ProductModule.objects.create(
            organization=self.office, code=ProductModule.Code.CROSSCHECK, enabled=True
        )
        self.client = self.login(self.user)

    def login(self, user: User, office: Organization | None = None) -> Client:
        client = Client()
        client.force_login(user)
        session = client.session
        session["hub_organization_id"] = str((office or self.office).id)
        session.save()
        return client

    def member(self, role: str, email: str, *, office: Organization | None = None) -> User:
        user = User.objects.create_user(email=email, password="uma-senha-longa")
        Membership.objects.create(organization=office or self.office, user=user, role=role)
        return user

    def draft(
        self, tool: str = SPED_XML, *, company: ClientCompany | None = None, **options: Any
    ) -> CrosscheckRun:
        return services.create_draft(
            organization=self.office,
            company=company or self.company,
            tool=tool,
            competence=date(2026, 9, 1),
            options=options,
            actor=self.user,
        )

    def attach(self, run: CrosscheckRun, role: str, *files: SimpleUploadedFile) -> Any:
        result = services.attach_files(run, role, list(files), actor=self.user)
        assert not result.errors, result.errors
        return result.stored

    def ready_run(self) -> CrosscheckRun:
        """Rascunho de SPED x XML com um documento que confere e três achados."""

        run = self.draft()
        self.attach(
            run,
            "sped",
            sped_upload(
                [
                    doc(1),
                    doc(2, vl_doc="200,00", vl_merc="200,00"),
                    doc(3),
                ]
            ),
        )
        self.attach(run, "xml", zip_upload(nfe(1), nfe(2, v_nf="150.00"), nfe(4)))
        return run


class AgentCase(CrosscheckCase):
    def setUp(self) -> None:
        super().setUp()
        Connector.objects.create(
            organization=self.office, kind=Connector.Kind.DOMINIO_AGENT, enabled=True
        )
        self.agent_client = Client()
        credentials = redeem_enrollment(
            code=issue_enrollment(organization=self.office).code,
            label="Servidor Domínio",
            fingerprint="device-fp",
        )
        self.agent_id = credentials.agent_id
        self.secret = credentials.shared_secret

    def post(
        self,
        name: str,
        payload: dict[str, Any],
        *args: Any,
        secret: str | None = None,
        agent_id: Any = None,
    ) -> Any:
        body = json.dumps(payload).encode()
        timestamp = str(int(timezone.now().timestamp()))
        signature = hmac.new(
            (secret or self.secret).encode(), timestamp.encode() + b"." + body, hashlib.sha256
        ).hexdigest()
        return self.agent_client.post(
            reverse(name, args=args),
            data=body,
            content_type="application/json",
            secure=True,
            headers={
                "X-Hub-Agent-ID": str(agent_id or self.agent_id),
                "X-Hub-Agent-Timestamp": timestamp,
                "X-Hub-Agent-Signature": signature,
            },
        )

    def next(self, **kwargs: Any) -> Any:
        return self.post("agent-v2-crosscheck-next", {"source_system": "dominio"}, **kwargs)

    def batch(self, job_id: Any, sequence: int, rows: list[dict[str, str]], **kwargs: Any) -> Any:
        return self.post(
            "agent-v2-crosscheck-batch", {"sequence": sequence, "rows": rows}, job_id, **kwargs
        )

    def complete(self, job_id: Any, rows: int, pages: int) -> Any:
        return self.post(
            "agent-v2-crosscheck-complete", {"row_count": rows, "pages": pages}, job_id
        )

    def uf_draft(self, **options: Any) -> CrosscheckRun:
        return self.draft(UF_DOMINIO, dominio_source="agente", **options)

    def requested(self) -> tuple[CrosscheckRun, CrosscheckAgentJob]:
        run = self.uf_draft()
        return run, agent.request_agent_job(run, actor=self.user)

    @staticmethod
    def row(numero: int, uf: str = "SP", direcao: str = "E") -> dict[str, str]:
        return {"chave_nfe": chave(numero), "direcao": direcao, "uf": uf}

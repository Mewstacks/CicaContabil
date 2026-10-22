"""Conferências sintéticas do Contraprova para revisar a interface (somente com DEBUG).

Tudo é fictício e passa pelo caminho de produção: os arquivos entram por `attach_files`, a
conferência roda em `process_run` e o resultado é o que a tela mostra. Nada aqui lê ou imita
dado de cliente.
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from typing import Any

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.accounts.models import User
from apps.crosscheck import services
from apps.crosscheck.engine.tools import ICMS51, SPED_SPED, SPED_XML, UF_DOMINIO
from apps.crosscheck.models import CrosscheckInput, CrosscheckRun
from apps.crosscheck.synthetic import (
    AnalyticSpec,
    DocSpec,
    EfdSpec,
    ItemSpec,
    NfeSpec,
    build_efd,
    build_nfe_xml,
    build_zip,
    make_cnpj,
    make_key,
)
from apps.hub.models import ClientCompany, ProductModule
from apps.organizations.models import Organization

FORNECEDOR = make_cnpj("98765432", "0001")
OUTRA = make_cnpj("55555555", "0001")


def mask(cnpj: str) -> str:
    return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"


class Seeder:
    def __init__(self, office: Organization, user: User, companies: list[ClientCompany]) -> None:
        self.office = office
        self.user = user
        self.companies = companies
        self.cnpjs = [make_cnpj(f"{10000000 + index}", "0001") for index in range(len(companies))]

    # -- peças -------------------------------------------------------------------------
    def key(self, number: int, *, aamm: str = "2609") -> str:
        return make_key(cnpj=FORNECEDOR, number=number, aamm=aamm)

    def doc(self, number: int, **fields: Any) -> DocSpec:
        return DocSpec(number=number, key=self.key(number), **fields)

    def nfe(self, index: int, number: int, **fields: Any) -> NfeSpec:
        fields.setdefault("emit_cnpj", FORNECEDOR)
        fields.setdefault("dest_cnpj", self.cnpjs[index])
        return NfeSpec(key=self.key(number), number=number, **fields)

    def sped(self, index: int, docs: list[DocSpec], name: str = "sped.txt", **spec: Any) -> Any:
        data = build_efd(EfdSpec(cnpj=self.cnpjs[index], docs=docs, **spec))
        return SimpleUploadedFile(name, data, "text/plain")

    def zip(self, *items: NfeSpec | tuple[str, bytes], name: str = "xml.zip") -> Any:
        files: dict[str, bytes] = {}
        for position, item in enumerate(items):
            if isinstance(item, tuple):
                files[item[0]] = item[1]
            else:
                files[f"nota-{item.number}-{position}.xml"] = build_nfe_xml(item)
        return SimpleUploadedFile(name, build_zip(files), "application/zip")

    def draft(self, index: int, tool: str, competence: date, **options: Any) -> CrosscheckRun:
        company = self.companies[index]
        return services.create_draft(
            organization=self.office,
            company=company,
            tool=tool,
            competence=competence,
            options=options,
            actor=self.user,
        )

    def attach(self, run: CrosscheckRun, role: str, *files: Any) -> None:
        result = services.attach_files(run, role, list(files), actor=self.user)
        if result.errors:
            raise CommandError("; ".join(result.errors))

    def process(self, run: CrosscheckRun) -> CrosscheckRun:
        services.start_run(run, actor=self.user, dispatch=False)
        services.process_run(str(run.id))
        run.refresh_from_db()
        return run

    # -- cenários ----------------------------------------------------------------------
    def sped_xml_mixed(self, index: int) -> CrosscheckRun:
        docs: list[DocSpec] = []
        notes: list[NfeSpec | tuple[str, bytes]] = []
        for number in range(1, 131):
            if number % 10 == 0:
                docs.append(self.doc(number, vl_doc="150,00", vl_merc="150,00"))
                notes.append(self.nfe(index, number))
            elif number % 17 == 0:
                docs.append(self.doc(number))
            elif number % 23 == 0:
                docs.append(
                    self.doc(
                        number,
                        vl_icms="0,00",
                        analytics=[AnalyticSpec(cfop="1551", vl_icms="0,00")],
                    )
                )
                notes.append(self.nfe(index, number))
            else:
                docs.append(self.doc(number))
                notes.append(self.nfe(index, number))
        docs.append(self.doc(5))
        docs.append(self.doc(300, cod_sit="02"))
        notes.append(self.nfe(index, 300))
        notes.extend(self.nfe(index, number) for number in range(200, 205))
        run = self.draft(index, SPED_XML, date(2026, 9, 1))
        self.attach(run, "sped", self.sped(index, docs))
        self.attach(run, "xml", self.zip(*notes))
        return self.process(run)

    def sped_xml_clean(self, index: int) -> CrosscheckRun:
        docs = [self.doc(number) for number in range(1, 9)]
        notes = [self.nfe(index, number) for number in range(1, 9)]
        run = self.draft(index, SPED_XML, date(2026, 8, 1))
        self.attach(
            run,
            "sped",
            self.sped(index, docs, dt_ini="01082026", dt_fin="31082026", name="agosto.txt"),
        )
        self.attach(run, "xml", self.zip(*notes, name="agosto.zip"))
        return self.process(run)

    def sped_xml_draft(self, index: int) -> CrosscheckRun:
        docs = [self.doc(number) for number in range(1, 4)]
        run = self.draft(index, SPED_XML, date(2026, 10, 1))
        self.attach(run, "sped", self.sped(index, docs))
        self.attach(run, "xml", self.zip(*(self.nfe(index, n) for n in range(1, 4))))
        return run

    def sped_sped(self, index: int) -> CrosscheckRun:
        first = [self.doc(number) for number in range(1, 13)]
        second = [self.doc(number) for number in range(1, 11)]
        second[2] = self.doc(3, vl_doc="999,00", vl_merc="999,00")
        second[4] = self.doc(5, cod_sit="02")
        second.append(self.doc(20))
        run = self.draft(index, SPED_SPED, date(2026, 9, 1))
        self.attach(run, "sped1", self.sped(index, first, name="original.txt"))
        self.attach(run, "sped2", self.sped(index, second, name="retificadora.txt"))
        return self.process(run)

    def icms51(self, index: int) -> CrosscheckRun:
        docs = []
        notes: list[NfeSpec | tuple[str, bytes]] = []
        for number in range(1, 9):
            docs.append(self.doc(number, analytics=[AnalyticSpec(cfop="1551", vl_icms="66,67")]))
            wrong = number % 4 == 0
            notes.append(
                self.nfe(
                    index,
                    number,
                    items=[
                        ItemSpec(
                            cfop="5551",
                            group="ICMS51",
                            v_icms_op="100.00",
                            p_dif="33.3333",
                            v_icms_dif="33.33",
                            v_icms="60.00" if wrong else "66.67",
                        )
                    ],
                )
            )
        run = self.draft(index, ICMS51, date(2026, 9, 1))
        self.attach(run, "sped", self.sped(index, docs))
        self.attach(run, "xml", self.zip(*notes))
        return self.process(run)

    def uf_dominio(self, index: int) -> CrosscheckRun:
        notes = [self.nfe(index, number) for number in range(1, 21)]
        rows = ["chave;uf;direcao"]
        for number in range(1, 21):
            if number % 9 == 0:
                continue
            uf = "RJ" if number % 6 == 0 else "SP"
            rows.append(f"{self.key(number)};{uf};E")
        planilha = SimpleUploadedFile("dominio.csv", "\n".join(rows).encode(), "text/csv")
        run = self.draft(index, UF_DOMINIO, date(2026, 9, 1))
        self.attach(run, "xml", self.zip(*notes))
        self.attach(run, "dominio", planilha)
        return self.process(run)

    def failed(self, index: int) -> CrosscheckRun:
        run = self.draft(index, SPED_XML, date(2026, 7, 1))
        for role, kind, upload in (
            ("sped", "efd", self._foreign_sped()),
            ("xml", "xml", self.zip(self.nfe(index, 1))),
        ):
            item = CrosscheckInput(
                organization=self.office,
                run=run,
                role=role,
                kind=kind,
                original_name=upload.name,
                size_bytes=upload.size,
                sha256=uuid.uuid4().hex * 2,
            )
            item.content.save(upload.name, upload, save=False)
            item.save()
        return self.process(run)

    def _foreign_sped(self) -> Any:
        data = build_efd(
            EfdSpec(cnpj=OUTRA, docs=[self.doc(1)], dt_ini="01072026", dt_fin="31072026")
        )
        return SimpleUploadedFile("sped-outra-empresa.txt", data, "text/plain")

    def in_flight(self, index: int) -> tuple[CrosscheckRun, CrosscheckRun, CrosscheckRun]:
        queued = self.sped_xml_draft(index)
        CrosscheckRun.objects.filter(pk=queued.pk).update(
            state=CrosscheckRun.State.QUEUED, stage="queued", queued_at=timezone.now()
        )
        running = self.draft(index, SPED_XML, date(2026, 6, 1))
        CrosscheckRun.objects.filter(pk=running.pk).update(
            state=CrosscheckRun.State.PROCESSING,
            stage="Lendo XML",
            progress_done=4200,
            progress_total=10000,
            lease_token=uuid.uuid4(),
            lease_until=timezone.now() + timedelta(days=1),
            started_at=timezone.now(),
        )
        canceled = self.draft(index, ICMS51, date(2026, 5, 1))
        services.cancel_run(canceled, actor=self.user)
        for run in (queued, running, canceled):
            run.refresh_from_db()
        return queued, running, canceled


class Command(BaseCommand):
    help = "Cria conferências sintéticas do Contraprova para revisar a interface (só com DEBUG)."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--organization", required=True, help="slug do escritório")
        parser.add_argument("--user", required=True, help="e-mail de quem aparece como autor")
        parser.add_argument("--force", action="store_true", help="cria mesmo se já houver")

    def handle(self, *args: Any, **options: Any) -> None:
        if not settings.DEBUG:
            raise CommandError("seed_crosscheck só roda com DEBUG ligado.")
        try:
            office = Organization.objects.get(slug=options["organization"])
            user = User.objects.get(email=options["user"].casefold())
        except (Organization.DoesNotExist, User.DoesNotExist) as exc:
            raise CommandError("Escritório ou usuário não encontrado.") from exc
        if CrosscheckRun.objects.filter(organization=office).exists() and not options["force"]:
            self.stdout.write("Já há conferências neste escritório; nada a fazer (use --force).")
            return
        ProductModule.objects.update_or_create(
            organization=office,
            code=ProductModule.Code.CROSSCHECK,
            defaults={"enabled": True, "enabled_at": timezone.now()},
        )
        companies = list(ClientCompany.objects.filter(organization=office, active=True)[:3])
        if not companies:
            raise CommandError("O escritório não tem empresas ativas.")
        seeder = Seeder(office, user, companies)
        for index, company in enumerate(companies):
            company.cnpj_masked = mask(seeder.cnpjs[index])
            company.save()
        count = len(companies)
        runs = [
            seeder.sped_xml_mixed(0),
            seeder.sped_xml_clean(1 % count),
            seeder.sped_sped(2 % count),
            seeder.icms51(0),
            seeder.uf_dominio(1 % count),
            seeder.failed(2 % count),
            seeder.sped_xml_draft(0),
            *seeder.in_flight(1 % count),
        ]
        self.stdout.write(self.style.SUCCESS(f"{len(runs)} conferências criadas."))

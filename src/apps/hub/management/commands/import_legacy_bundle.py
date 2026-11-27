"""Import a HubFedrizzi export bundle into one office. Idempotent; --dry-run rolls back."""

from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.hub.legacy_import import BundleError, import_bundle
from apps.hub.legacy_nfse import import_nfse_documents
from apps.organizations.models import Organization


class Command(BaseCommand):
    help = "Importa o pacote exportado do HubFedrizzi para um escritório."

    def add_arguments(self, parser) -> None:  # type: ignore[no-untyped-def]
        parser.add_argument("--org", required=True, help="slug do escritório")
        parser.add_argument("--bundle", required=True, help="zip ou pasta do pacote")
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument(
            "--skip", action="append", default=[], help="tabela a pular (repetível)"
        )
        parser.add_argument(
            "--with-users", action="store_true", help="cria usuários sem senha (reset depois)"
        )
        parser.add_argument(
            "--no-convert", action="store_true", help="só guarda as linhas cruas, sem converter"
        )
        parser.add_argument(
            "--hold-generation",
            action="store_true",
            help="vínculos empresa x obrigação entram inativos (o motor não gera atividade)",
        )
        parser.add_argument(
            "--enable-nfse-sync",
            action="store_true",
            help="liga a sincronização NFS-e das empresas ativas (só na virada)",
        )
        parser.add_argument(
            "--activate-layouts",
            action="store_true",
            help="ativa os layouts de fechamento que já leem a própria amostra",
        )
        parser.add_argument(
            "--nfse-documents",
            choices=["robo", "mongo", "all"],
            help="estágio das notas: grava NfseDocument direto do pacote, em lotes",
        )
        parser.add_argument("--docs-only", action="store_true", help="roda só o estágio das notas")
        parser.add_argument(
            "--measure-only", action="store_true", help="estágio das notas: mede, não grava"
        )
        parser.add_argument("--limit", type=int, help="estágio das notas: máximo por fonte")
        parser.add_argument(
            "--offset",
            type=int,
            default=0,
            help="estágio das notas: pula as N primeiras de cada fonte",
        )
        parser.add_argument(
            "--batch-size", type=int, default=200, help="estágio das notas: notas por lote"
        )

    def handle(self, *args: object, **options: object) -> None:
        organization = Organization.objects.filter(slug=str(options["org"])).first()
        if organization is None:
            raise CommandError("Escritório não encontrado.")
        path = Path(str(options["bundle"]))
        if not path.exists():
            raise CommandError("Pacote não encontrado.")
        try:
            if not options["docs_only"]:
                report = import_bundle(
                    organization=organization,
                    path=path,
                    dry_run=bool(options["dry_run"]),
                    with_users=bool(options["with_users"]),
                    skip=frozenset(str(name) for name in options["skip"]),  # type: ignore[attr-defined]
                    convert=not options["no_convert"],
                    hold_generation=bool(options["hold_generation"]),
                    enable_nfse_sync=bool(options["enable_nfse_sync"]),
                    activate_layouts=bool(options["activate_layouts"]),
                )
                for line in report.lines():
                    self.stdout.write(line)
            stage = options["nfse_documents"]
            if stage and not options["dry_run"]:
                docs = import_nfse_documents(
                    organization=organization,
                    path=path,
                    sources=("robo", "mongo") if stage == "all" else (str(stage),),
                    measure_only=bool(options["measure_only"]),
                    limit=options["limit"],  # type: ignore[arg-type]
                    offset=int(options["offset"]),  # type: ignore[call-overload]
                    batch_size=int(options["batch_size"]),  # type: ignore[call-overload]
                )
                for line in docs.lines():
                    self.stdout.write(line)
        except BundleError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(
            self.style.SUCCESS("dry-run: nada gravado" if options["dry_run"] else "importado")
        )

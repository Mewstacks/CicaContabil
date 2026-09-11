from django.contrib import admin

from apps.hub.models import (
    AccumulatorObservation,
    AccumulatorRule,
    Certificate,
    ClientCompany,
    Connector,
    ConsumptionConfirmation,
    DteMessage,
    DteRun,
    DteRunItem,
    IntegrationArtifact,
    NfseDocument,
    NfseSync,
    OfficeProfile,
    OperationalTask,
    ProductModule,
    ReviewCase,
    UsageAllowance,
)

admin.site.register(
    (
        OfficeProfile,
        ProductModule,
        UsageAllowance,
        ClientCompany,
        Certificate,
        NfseSync,
        AccumulatorRule,
        AccumulatorObservation,
        ReviewCase,
        Connector,
        ConsumptionConfirmation,
        DteRun,
        DteRunItem,
        OperationalTask,
    )
)


@admin.register(NfseDocument)
class NfseDocumentAdmin(admin.ModelAdmin):
    readonly_fields = (
        "organization",
        "company",
        "source_nsu",
        "document_hash",
        "original_xml",
        "normalized_data",
        "captured_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return request.method in {"GET", "HEAD"}


@admin.register(IntegrationArtifact)
class IntegrationArtifactAdmin(admin.ModelAdmin):
    readonly_fields = (
        "organization",
        "document",
        "accumulator_code",
        "applied_rule",
        "confidence",
        "evidence",
        "export_format",
        "payload",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return request.method in {"GET", "HEAD"}


@admin.register(DteMessage)
class DteMessageAdmin(admin.ModelAdmin):
    readonly_fields = (
        "organization",
        "company",
        "source_isn",
        "subject",
        "sender",
        "sent_at",
        "read_at",
        "first_seen_at",
        "raw_payload",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return request.method in {"GET", "HEAD"}

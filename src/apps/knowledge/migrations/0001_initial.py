from django.db import migrations, models

import apps.common.encryption


class Migration(migrations.Migration):
    initial = True
    dependencies = []

    operations = [
        migrations.CreateModel(
            name="SharedKnowledgeSource",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                (
                    "kind",
                    models.CharField(
                        choices=[
                            ("manual", "Manual oficial"),
                            ("regulation", "Norma/regra"),
                            ("procedure", "Procedimento geral aprovado"),
                            ("validated_case", "Caso anonimizado validado"),
                        ],
                        max_length=24,
                    ),
                ),
                ("title", models.CharField(max_length=180)),
                ("version", models.CharField(max_length=80)),
                ("source_reference", models.CharField(max_length=300)),
                ("content", apps.common.encryption.EncryptedTextField()),
                ("content_hash", models.CharField(max_length=64, unique=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("draft", "Em curadoria"),
                            ("approved", "Aprovado"),
                            ("retired", "Retirado"),
                        ],
                        default="draft",
                        max_length=16,
                    ),
                ),
                ("approved_by_subject_hash", models.CharField(blank=True, max_length=64)),
                ("approved_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ("title", "version")},
        ),
        migrations.CreateModel(
            name="GlobalLearningPromotion",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("origin_fingerprint", models.CharField(db_index=True, max_length=64)),
                ("source_reference", models.CharField(max_length=300)),
                ("sanitized_correction", apps.common.encryption.EncryptedTextField()),
                ("correction_hash", models.CharField(max_length=64, unique=True)),
                ("evaluation_specification", models.JSONField(default=dict)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("candidate", "Em curadoria"),
                            ("approved", "Aprovado"),
                            ("published", "Publicado"),
                            ("rejected", "Rejeitado"),
                        ],
                        default="candidate",
                        max_length=16,
                    ),
                ),
                ("reviewed_by_subject_hash", models.CharField(blank=True, max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name="SharedKnowledgeChunk",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("ordinal", models.PositiveIntegerField()),
                ("content", apps.common.encryption.EncryptedTextField()),
                ("content_hash", models.CharField(db_index=True, max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "source",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="chunks",
                        to="knowledge.sharedknowledgesource",
                    ),
                ),
            ],
            options={"ordering": ("source", "ordinal")},
        ),
        migrations.AddConstraint(
            model_name="sharedknowledgechunk",
            constraint=models.UniqueConstraint(
                fields=("source", "content_hash"), name="knowledge_unique_shared_chunk"
            ),
        ),
    ]

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0003_apikey_key_hash"),
    ]

    operations = [
        migrations.CreateModel(
            name="WhatsAppDiagnosticEvent",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("event_id", models.CharField(db_index=True, max_length=64, unique=True)),
                ("correlation_id", models.CharField(db_index=True, max_length=100)),
                ("direction", models.CharField(choices=[("inbound", "Inbound"), ("outbound", "Outbound"), ("system", "System")], db_index=True, max_length=12)),
                ("event_type", models.CharField(db_index=True, max_length=80)),
                ("stage", models.CharField(db_index=True, max_length=80)),
                ("status", models.CharField(choices=[("started", "Started"), ("ok", "OK"), ("failed", "Failed"), ("ignored", "Ignored")], db_index=True, max_length=12)),
                ("phone_last4", models.CharField(blank=True, max_length=8)),
                ("external_id", models.CharField(blank=True, db_index=True, max_length=200)),
                ("duration_ms", models.PositiveIntegerField(blank=True, null=True)),
                ("error_message", models.TextField(blank=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="whatsappdiagnosticevent",
            index=models.Index(fields=["correlation_id", "created_at"], name="core_wa_corr_created"),
        ),
        migrations.AddIndex(
            model_name="whatsappdiagnosticevent",
            index=models.Index(fields=["direction", "status", "created_at"], name="core_wa_dir_status_created"),
        ),
        migrations.AddIndex(
            model_name="whatsappdiagnosticevent",
            index=models.Index(fields=["event_type", "created_at"], name="core_wa_type_created"),
        ),
    ]

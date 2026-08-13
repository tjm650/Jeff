import uuid

from django.db import models


class WhatsAppDiagnosticEvent(models.Model):
    """Durable observability events for the WhatsApp message pipeline."""

    DIRECTION_CHOICES = [
        ("inbound", "Inbound"),
        ("outbound", "Outbound"),
        ("system", "System"),
    ]

    STATUS_CHOICES = [
        ("started", "Started"),
        ("ok", "OK"),
        ("failed", "Failed"),
        ("ignored", "Ignored"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_id = models.CharField(max_length=64, unique=True, db_index=True)
    correlation_id = models.CharField(max_length=100, db_index=True)
    direction = models.CharField(max_length=12, choices=DIRECTION_CHOICES, db_index=True)
    event_type = models.CharField(max_length=80, db_index=True)
    stage = models.CharField(max_length=80, db_index=True)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, db_index=True)
    phone_last4 = models.CharField(max_length=8, blank=True)
    external_id = models.CharField(max_length=200, blank=True, db_index=True)
    duration_ms = models.PositiveIntegerField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["correlation_id", "created_at"]),
            models.Index(fields=["direction", "status", "created_at"]),
            models.Index(fields=["event_type", "created_at"]),
        ]

    def __str__(self):
        return f"{self.event_type} [{self.status}] {self.correlation_id}"

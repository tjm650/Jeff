from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal

class Payment(models.Model):
    """Payment transaction model for WhatsApp agent Paynow payment"""

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
        ('failed', 'Failed'),
    ]

    # Core transaction fields
    transaction_id = models.CharField(
        max_length=255,
        unique=True,
        db_index=True
    )
    poll_url = models.URLField(
        max_length=500,
        blank=True
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('1.00')
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True
    )

    # Payment method
    payment_method = models.CharField(
        max_length=50,
        default='paynow'
    )

    # WhatsApp & Payment numbers
    whatsapp_number = models.CharField(
        max_length=15,
        db_index=True,
        help_text="User's WhatsApp number"
    )
    payment_number = models.CharField(
        max_length=15,
        db_index=True,
        help_text="Mobile payment number"
    )

    # PayNow references
    reference = models.CharField(
        max_length=255,
        blank=True,
        help_text="Internal reference"
    )
    paynow_reference = models.CharField(
        max_length=255,
        blank=True,
        help_text="PayNow reference"
    )

    # Optional user link
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Payment'
        verbose_name_plural = 'payment'
        indexes = [
            models.Index(fields=['whatsapp_number', 'status']),
            models.Index(fields=['payment_number', 'status']),
        ]

    def __str__(self):
        return f"{self.transaction_id} - WA: {self.whatsapp_number} Pay: {self.payment_number} - ${self.amount}"

    @property
    def is_successful(self):
        return self.status == 'paid'

    @property
    def is_pending(self):
        return self.status == 'pending'

    @classmethod
    def get_user_payment(cls, whatsapp_number):
        """Get all payment for a WhatsApp user"""
        return cls.objects.filter(whatsapp_number=whatsapp_number)

    @classmethod
    def get_successful_payment(cls, whatsapp_number):
        """Get successful payment for a WhatsApp user"""
        return cls.objects.filter(
            whatsapp_number=whatsapp_number,
            status='paid'
        )
from django.contrib import admin
from .models import Payment

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        'transaction_id',
        'whatsapp_number',
        'payment_number',
        'amount',
        'status',
        'created_at'
    ]
    list_filter = [
        'status',
        'created_at',
        'payment_method'
    ]
    search_fields = [
        'transaction_id',
        'whatsapp_number',
        'payment_number',
        'paynow_reference',
        'reference'
    ]
    readonly_fields = [
        'created_at',
        'updated_at'
    ]

    fieldsets = (
        (
            'Transaction Info',
            {
                'fields': (
                    'transaction_id',
                    'status',
                    'amount',
                    'payment_method'
                )
            }
        ),
        (
            'WhatsApp & Payment Numbers',
            {
                'fields': (
                    'whatsapp_number',
                    'payment_number'
                ),
                'description': 'WhatsApp number is where user messages from. Payment number is their EcoCash number.'
            }
        ),
        (
            'PayNow Details',
            {
                'fields': (
                    'poll_url',
                    'paynow_reference',
                    'reference'
                )
            }
        ),
        (
            'Timestamps',
            {
                'fields': (
                    'created_at',
                    'updated_at'
                )
            }
        ),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user')
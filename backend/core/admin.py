from django.contrib import admin
from .models import AccommodationProvider, Property, Token, Transaction, Booking, ConversationState, Review, Conversation

@admin.register(AccommodationProvider)
class AccommodationProviderAdmin(admin.ModelAdmin):
    list_display = ['name', 'phone_number', 'email', 'verified', 'rating', 'total_reviews']
    list_filter = ['verified', 'created_at', 'rating']
    search_fields = ['name', 'phone_number', 'email']
    readonly_fields = ['id', 'created_at', 'rating', 'total_reviews']

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'phone_number', 'email')
        }),
        ('Verification', {
            'fields': ('verified',)
        }),
        ('Statistics', {
            'fields': ('rating', 'total_reviews'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ['name', 'provider', 'property_no', 'available_rooms', 'price_per_month', 'campus_name', 'is_active']
    list_filter = ['is_active', 'campus_name', 'gender_preference', 'created_at']
    search_fields = ['name', 'provider__name', 'campus_name', 'address']
    readonly_fields = ['id', 'created_at', 'updated_at']

    fieldsets = (
        ('Basic Information', {
            'fields': ('provider', 'name', 'property_no', 'address', 'description')
        }),
        ('Room Configuration', {
            'fields': (
                # 'heads_per_room',
                'total_rooms',
                'available_rooms',
                'available_1h_rooms',
                'available_2h_rooms',
                'available_3h_rooms',
                'available_4h_rooms',
            )
        }),
        ('Amenities & Pricing', {
            'fields': ('amenities', 'price_per_semester', 'price_per_month', 'price_per_week', 'price_per_day')
        }),
        ('Location', {
            'fields': ('distance_from_campus', 'campus_name')
        }),
        ('Preferences', {
            'fields': ('gender_preference',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('provider')

@admin.register(Token)
class TokenAdmin(admin.ModelAdmin):
    list_display = ['token_number', 'cell_number', 'remaining_uses', 'is_active', 'expires_at']
    list_filter = ['is_active', 'expires_at', 'purchased_at']
    search_fields = ['token_number', 'cell_number']
    readonly_fields = ['id', 'token_number', 'purchased_at']

    fieldsets = (
        ('Token Information', {
            'fields': ('token_number', 'cell_number')
        }),
        ('Usage', {
            'fields': ('total_uses', 'used_count', 'is_active')
        }),
        ('Validity', {
            'fields': ('purchased_at', 'expires_at')
        }),
        ('Transaction', {
            'fields': ('transaction',)
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('transaction')

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['transaction_number', 'cell_number', 'amount', 'payment_method', 'status', 'created_at']
    list_filter = ['status', 'payment_method', 'created_at']
    search_fields = ['transaction_number', 'cell_number']
    readonly_fields = ['id', 'transaction_number', 'created_at']

    fieldsets = (
        ('Transaction Information', {
            'fields': ('transaction_number', 'cell_number', 'amount', 'payment_method')
        }),
        ('Payment Proof', {
            'fields': ('pop_image',)
        }),
        ('Verification', {
            'fields': ('pop_verified', 'status', 'verified_at')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['booking_number', 'cell_number', 'property', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['booking_number', 'cell_number', 'property__name']
    readonly_fields = ['id', 'booking_number', 'created_at']

    fieldsets = (
        ('Booking Information', {
            'fields': ('booking_number', 'cell_number', 'property', 'status')
        }),
        ('Response', {
            'fields': ('provider_response', 'additional_info_requested')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'confirmed_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('property')

@admin.register(ConversationState)
class ConversationStateAdmin(admin.ModelAdmin):
    list_display = ['cell_number', 'current_step', 'is_active', 'last_message_at']
    list_filter = ['current_step', 'is_active', 'last_message_at']
    search_fields = ['cell_number']
    readonly_fields = ['id', 'last_message_at']

    fieldsets = (
        ('Conversation Information', {
            'fields': ('cell_number', 'current_step', 'is_active')
        }),
        ('Context Data', {
            'fields': ('context_data', 'selected_properties')
        }),
        ('Timestamps', {
            'fields': ('last_message_at',),
            'classes': ('collapse',)
        }),
    )

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['cell_number', 'property', 'rating', 'created_at']
    list_filter = ['rating', 'created_at']
    search_fields = ['cell_number', 'property__name', 'comment']
    readonly_fields = ['id', 'created_at']

    fieldsets = (
        ('Review Information', {
            'fields': ('cell_number', 'property', 'rating', 'comment')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('property')
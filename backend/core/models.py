from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.utils.crypto import get_random_string
import uuid
import string
import hashlib

def generate_property_no():
    """Generate a unique property number (2 letters + hyphen + 4 digits, e.g. AB-1234)."""
    letters = ''.join(get_random_string(2, allowed_chars=string.ascii_uppercase))
    numbers = ''.join(get_random_string(4, allowed_chars=string.digits))
    return f"{letters}-{numbers}"

property_no_validator = RegexValidator(
    regex='^[A-Z]{2}-[0-9]{4}$',
    message='Property number must be 2 capital letters followed by a hyphen and 4 digits (e.g. AB-1234)'
)

class AccommodationProvider(models.Model):
    """Accommodation provider model"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone_number = models.CharField(max_length=20, unique=True, db_index=True)
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    verified = models.BooleanField(default=False)
    rating = models.FloatField(default=0.0, validators=[MinValueValidator(0.0), MaxValueValidator(5.0)])
    total_reviews = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['phone_number']),
            models.Index(fields=['verified']),
        ]

    def __str__(self):
        return f'{self.name} - {self.phone_number}'

class Property(models.Model):
    """Property model for accommodation listings"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.ForeignKey(AccommodationProvider, on_delete=models.CASCADE, related_name='properties')
    property_no = models.CharField(max_length=7, unique=True, db_index=True, 
                              help_text='Property reference number (2 letters followed by a hyphen and 4 digits, e.g. AB-1234)',
                              validators=[property_no_validator])

    # Basic information
    name = models.CharField(max_length=200)
    address = models.TextField()
    description = models.TextField(blank=True)

    # Room configuration
    total_rooms = models.PositiveIntegerField()
    available_rooms = models.PositiveIntegerField()
    # Availability by heads-per-room configuration
    available_1h_rooms = models.PositiveIntegerField(default=0)
    available_2h_rooms = models.PositiveIntegerField(default=0)
    available_3h_rooms = models.PositiveIntegerField(default=0)
    available_4h_rooms = models.PositiveIntegerField(default=0)

    # Amenities (stored as JSON)
    amenities = models.JSONField(default=list)  # wifi, parking, DSTV, etc.

    # Pricing
    price_per_semester = models.DecimalField(max_digits=10, decimal_places=2)
    price_per_month = models.DecimalField(max_digits=10, decimal_places=2)
    price_per_week = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    price_per_day = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    # Location
    distance_from_campus = models.FloatField(help_text='Distance in kilometers')
    campus_name = models.CharField(max_length=100)

    # Preferences
    gender_preference = models.CharField(
        max_length=10,
        choices=[('male', 'Male'), ('female', 'Female'), ('any', 'Any'), ('mixed', 'Mixed')],
        default='any'
    )

    # Ratings
    rating = models.FloatField(default=0.0, validators=[MinValueValidator(0.0), MaxValueValidator(5.0)])
    total_reviews = models.PositiveIntegerField(default=0)

    # Status
    is_active = models.BooleanField(default=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-rating', 'price_per_month', 'distance_from_campus']
        indexes = [
            models.Index(fields=['is_active', 'available_rooms']),
            models.Index(fields=['campus_name']),
            models.Index(fields=['gender_preference']),
            models.Index(fields=['price_per_month']),
            models.Index(fields=['distance_from_campus']),
            models.Index(fields=['rating']),
            models.Index(fields=['is_active', 'campus_name', 'available_rooms']),
        ]

    def __str__(self):
        return f'{self.name}'

class Token(models.Model):
    """Token model for payment-based search access"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # User identification
    cell_number = models.CharField(max_length=20, db_index=True)

    # Token details
    token_number = models.CharField(max_length=20, unique=True, db_index=True)
    total_uses = models.PositiveIntegerField(default=1)
    used_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    # Validity period
    purchased_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    # Payment reference
    transaction = models.OneToOneField('Transaction', on_delete=models.CASCADE, related_name='token')

    class Meta:
        indexes = [
            models.Index(fields=['token_number']),
            models.Index(fields=['cell_number']),
            models.Index(fields=['is_active', 'expires_at']),
        ]

    def __str__(self):
        return f'{self.token_number} - {self.remaining_uses()} uses left'

    def remaining_uses(self):
        """Calculate remaining token uses"""
        return max(0, self.total_uses - self.used_count)

    def is_valid(self):
        """Check if token is valid for use"""
        return (
            self.is_active and
            self.remaining_uses() > 0 and
            timezone.now() <= self.expires_at
        )

    def use_token(self):
        """Use one token count"""
        if self.is_valid():
            self.used_count += 1
            self.save()
            return True
        return False

class Transaction(models.Model):
    """Transaction model for payment records"""
    PAYMENT_METHODS = [
        ('ecocash', 'EcoCash'),
        ('paynow', 'Paynow'),
    ]

    STATUSES = [
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('failed ', 'failed '),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # User identification
    cell_number = models.CharField(max_length=20, db_index=True)

    # Transaction details
    transaction_number = models.CharField(max_length=50, unique=True, db_index=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    # Payment method
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)

    # Proof of payment
    pop_image = models.ImageField(upload_to='proofs/', blank=True, null=True)

    # Verification status
    pop_verified = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUSES, default='pending')

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['transaction_number']),
            models.Index(fields=['cell_number']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f'{self.transaction_number} - ${self.amount}'

class Booking(models.Model):
    """Booking model for accommodation bookings"""
    STATUSES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # User identification
    cell_number = models.CharField(max_length=20, db_index=True, default='')
    student_name = models.CharField(max_length=100, blank=True)

    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='bookings')

    # Booking details
    booking_number = models.CharField(max_length=20, unique=True)
    status = models.CharField(max_length=20, choices=STATUSES, default='pending')
    
    # Rental details
    rental_period = models.CharField(
        max_length=10,
        choices=[('day', 'Daily'), ('week', 'Weekly'), ('month', 'Monthly')],
        default='month'
    )
    price_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    # Provider response
    provider_response = models.TextField(blank=True)

    # Additional information requested by provider
    additional_info_requested = models.JSONField(default=dict)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['booking_number']),
            models.Index(fields=['cell_number']),
            models.Index(fields=['status']),
        ]
        unique_together = ['cell_number', 'property', 'status']

    def __str__(self):
        return f'{self.booking_number} - {self.status}'


class ConversationState(models.Model):
    """Conversation state model for WhatsApp conversation flow"""
    STEPS = [
        ('inquiry', 'Inquiry'),
        ('token_check', 'Token Check'),
        ('payment', 'Payment'),
        ('property_selection', 'Property Selection'),
        ('booking_confirmation', 'Booking Confirmation'),
        ('additional_info', 'Additional Info'),
        ('completed', 'Completed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # User identification
    cell_number = models.CharField(max_length=20, db_index=True)

    # Current step in conversation
    current_step = models.CharField(max_length=50, choices=STEPS, default='inquiry')

    # Context data (temporary storage for conversation)
    context_data = models.JSONField(default=dict)

    # Selected properties for current search
    selected_properties = models.JSONField(default=list)  # List of property IDs

    # Timestamps
    last_message_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-last_message_at']
        indexes = [
            models.Index(fields=['cell_number', 'is_active']),
            models.Index(fields=['current_step']),
        ]

    def __str__(self):
        return f'{self.cell_number} - {self.current_step}'

class Review(models.Model):
    """Review model for property reviews (bonus feature)"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # User identification
    cell_number = models.CharField(max_length=20, db_index=True)

    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='reviews')

    # Review details
    rating = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['property', 'rating']),
            models.Index(fields=['cell_number']),
        ]
        unique_together = ['cell_number', 'property']

    def __str__(self):
        return f'{self.rating} stars for {self.property.name}'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update property provider rating
        self._update_provider_rating()

    def _update_provider_rating(self):
        """Update the provider's average rating"""
        avg_rating = self.property.reviews.aggregate(
            models.Avg('rating')
        )['rating__avg'] or 0

        total_reviews = self.property.reviews.count()

        self.property.provider.rating = avg_rating
        self.property.provider.total_reviews = total_reviews
        self.property.provider.save()





class APIKey(models.Model):
    """API Key model for authenticating API requests from frontend"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    # Historically this field stored the raw API key. To improve security we now
    # store a hash of the key instead (and use key_hash for lookups). Existing
    # rows will be migrated lazily on save.
    key = models.CharField(max_length=64, unique=True, db_index=True)
    # New field used for verification; stores a SHA‑256 hex digest of the key.
    key_hash = models.CharField(max_length=64, unique=True, db_index=True, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        # Avoid leaking the full key or hash; only show a short prefix.
        display = (self.key or '')[:8]
        return f'{self.name} - {display}...'

    @staticmethod
    def hash_key(raw_key: str) -> str:
        """
        Hash an API key using SHA‑256.

        The resulting 64‑character hex digest is what we persist for verification.
        """
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    def set_key(self, raw_key: str) -> None:
        """
        Helper to set the key and its hash from a raw API key string.

        Call this when creating or rotating keys so that we never need to
        persist the raw secret beyond initial generation.
        """
        digest = self.hash_key(raw_key)
        self.key = digest
        self.key_hash = digest

    def save(self, *args, **kwargs):
        """
        Ensure key_hash is always populated when a key value exists.

        This gives us a backwards‑compatible migration path: existing rows with
        only `key` set will get a hash computed on next save.
        """
        if self.key and not self.key_hash:
            self.key_hash = self.hash_key(self.key)
        super().save(*args, **kwargs)

    def is_valid(self):
        """Check if API key is valid"""
        if not self.is_active:
            return False
        if self.expires_at and timezone.now() > self.expires_at:
            return False
        return True


class Conversation(models.Model):
    """Conversation model for tracking user conversations with the agent for security purposes"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # User identification
    cell_number = models.CharField(max_length=20, db_index=True)

    # Agent information
    agent_id = models.CharField(max_length=100, db_index=True)
    time_of_active_of_the_agent = models.DateTimeField(auto_now_add=True)

    # Conversation details
    message_count = models.PositiveIntegerField(default=0)
    last_message_at = models.DateTimeField(auto_now=True)

    # Security tracking
    is_suspicious = models.BooleanField(default=False)
    flagged_reason = models.TextField(blank=True)

    class Meta:
        ordering = ['-last_message_at']
        indexes = [
            models.Index(fields=['cell_number', 'agent_id']),
            models.Index(fields=['time_of_active_of_the_agent']),
            models.Index(fields=['is_suspicious']),
        ]

    def __str__(self):
        return f'{self.cell_number} - Agent {self.agent_id} - {self.message_count} messages'
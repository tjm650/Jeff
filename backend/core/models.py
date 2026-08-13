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
        indexes = [models.Index(fields=['phone_number']), models.Index(fields=['verified'])]
    def __str__(self):
        return f'{self.name} - {self.phone_number}'

class Property(models.Model):
    """Property model for accommodation listings"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.ForeignKey(AccommodationProvider, on_delete=models.CASCADE, related_name='properties')
    property_no = models.CharField(max_length=7, unique=True, db_index=True, help_text='Property reference number (2 letters followed by a hyphen and 4 digits, e.g. AB-1234)', validators=[property_no_validator])
    name = models.CharField(max_length=200)
    address = models.TextField()
    description = models.TextField(blank=True)
    total_rooms = models.PositiveIntegerField()
    available_rooms = models.PositiveIntegerField()
    available_1h_rooms = models.PositiveIntegerField(default=0)
    available_2h_rooms = models.PositiveIntegerField(default=0)
    available_3h_rooms = models.PositiveIntegerField(default=0)
    available_4h_rooms = models.PositiveIntegerField(default=0)
    amenities = models.JSONField(default=list)
    price_per_semester = models.DecimalField(max_digits=10, decimal_places=2)
    price_per_month = models.DecimalField(max_digits=10, decimal_places=2)
    price_per_week = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    price_per_day = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    distance_from_campus = models.FloatField(help_text='Distance in kilometers')
    campus_name = models.CharField(max_length=100)
    gender_preference = models.CharField(max_length=10, choices=[('male', 'Male'), ('female', 'Female'), ('any', 'Any'), ('mixed', 'Mixed')], default='any')
    rating = models.FloatField(default=0.0, validators=[MinValueValidator(0.0), MaxValueValidator(5.0)])
    total_reviews = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ['-rating', 'price_per_month', 'distance_from_campus']
        indexes = [models.Index(fields=['is_active', 'available_rooms']), models.Index(fields=['campus_name']), models.Index(fields=['gender_preference']), models.Index(fields=['price_per_month']), models.Index(fields=['distance_from_campus']), models.Index(fields=['rating']), models.Index(fields=['is_active', 'campus_name', 'available_rooms'])]
    def __str__(self):
        return f'{self.name}'

class Booking(models.Model):
    """Booking model for accommodation bookings"""
    STATUSES = [('pending', 'Pending'), ('confirmed', 'Confirmed'), ('rejected', 'Rejected'), ('cancelled', 'Cancelled')]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cell_number = models.CharField(max_length=20, db_index=True, default='')
    student_name = models.CharField(max_length=100, blank=True)
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='bookings')
    booking_number = models.CharField(max_length=20, unique=True)
    status = models.CharField(max_length=20, choices=STATUSES, default='pending')
    rental_period = models.CharField(max_length=10, choices=[('day', 'Daily'), ('week', 'Weekly'), ('month', 'Monthly')], default='month')
    price_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    provider_response = models.TextField(blank=True)
    additional_info_requested = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(blank=True, null=True)
    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['booking_number']), models.Index(fields=['cell_number']), models.Index(fields=['status'])]
        unique_together = ['cell_number', 'property', 'status']
    def __str__(self):
        return f'{self.booking_number} - {self.status}'

class ConversationState(models.Model):
    """Conversation state model for the free accommodation search and booking flow."""
    STEPS = [
        ('inquiry', 'Inquiry'),
        ('property_selection', 'Property Selection'),
        ('booking_confirmation', 'Booking Confirmation'),
        ('additional_info', 'Additional Info'),
        ('completed', 'Completed'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cell_number = models.CharField(max_length=20, db_index=True)
    current_step = models.CharField(max_length=50, choices=STEPS, default='inquiry')
    context_data = models.JSONField(default=dict)
    selected_properties = models.JSONField(default=list)
    last_message_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    class Meta:
        ordering = ['-last_message_at']
        indexes = [models.Index(fields=['cell_number', 'is_active']), models.Index(fields=['current_step'])]
    def __str__(self):
        return f'{self.cell_number} - {self.current_step}'

class Review(models.Model):
    """Review model for property reviews (bonus feature)"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cell_number = models.CharField(max_length=20, db_index=True)
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['property', 'rating']), models.Index(fields=['cell_number'])]
        unique_together = ['cell_number', 'property']
    def __str__(self):
        return f'{self.rating} stars for {self.property.name}'
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self._update_provider_rating()
    def _update_provider_rating(self):
        avg_rating = self.property.reviews.aggregate(models.Avg('rating'))['rating__avg'] or 0
        total_reviews = self.property.reviews.count()
        self.property.provider.rating = avg_rating
        self.property.provider.total_reviews = total_reviews
        self.property.provider.save()

class APIKey(models.Model):
    """API Key model for authenticating API requests from frontend"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    key = models.CharField(max_length=64, unique=True, db_index=True)
    key_hash = models.CharField(max_length=64, unique=True, db_index=True, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(blank=True, null=True)
    class Meta:
        ordering = ['-created_at']
    def __str__(self):
        display = (self.key or '')[:8]
        return f'{self.name} - {display}...'
    @staticmethod
    def hash_key(raw_key: str) -> str:
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
    def set_key(self, raw_key: str) -> None:
        digest = self.hash_key(raw_key)
        self.key = digest
        self.key_hash = digest
    def save(self, *args, **kwargs):
        if self.key and not self.key_hash:
            self.key_hash = self.hash_key(self.key)
        super().save(*args, **kwargs)
    def is_valid(self):
        if not self.is_active:
            return False
        if self.expires_at and timezone.now() > self.expires_at:
            return False
        return True

class Conversation(models.Model):
    """Conversation model for tracking user conversations with the agent for security purposes"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cell_number = models.CharField(max_length=20, db_index=True)
    agent_id = models.CharField(max_length=100, db_index=True)
    time_of_active_of_the_agent = models.DateTimeField(auto_now_add=True)
    message_count = models.PositiveIntegerField(default=0)
    last_message_at = models.DateTimeField(auto_now=True)
    is_suspicious = models.BooleanField(default=False)
    flagged_reason = models.TextField(blank=True)
    class Meta:
        ordering = ['-last_message_at']
        indexes = [models.Index(fields=['cell_number', 'agent_id']), models.Index(fields=['time_of_active_of_the_agent']), models.Index(fields=['is_suspicious'])]
    def __str__(self):
        return f'{self.cell_number} - Agent {self.agent_id} - {self.message_count} messages'

"""Operational analytics for the Jeff platform."""

from datetime import timedelta
import logging
from typing import Dict

from django.db.models import Avg, Count, Min, Max, Sum
from django.utils import timezone

from .models import Property, Conversation, Booking, Review

logger = logging.getLogger(__name__)


class JeffAnalytics:
    """Analytics service for properties, conversations, bookings and reviews."""

    def get_dashboard_metrics(self) -> Dict:
        try:
            now = timezone.now()
            last_24h = now - timedelta(hours=24)
            total_properties = Property.objects.filter(is_active=True).count()
            total_conversations = Conversation.objects.count()
            total_bookings = Booking.objects.count()
            recent_conversations = Conversation.objects.filter(last_message_at__gte=last_24h).count()
            recent_bookings = Booking.objects.filter(created_at__gte=last_24h).count()
            avg_rating = Property.objects.aggregate(avg_rating=Avg('provider__rating'))['avg_rating'] or 0
            reviewed_properties = Property.objects.filter(reviews__isnull=False).distinct().count()
            return {
                'overview': {
                    'total_properties': total_properties,
                    'total_conversations': total_conversations,
                    'total_bookings': total_bookings,
                },
                'recent_activity': {
                    'conversations_24h': recent_conversations,
                    'bookings_24h': recent_bookings,
                },
                'properties': {
                    'avg_rating': round(avg_rating, 2),
                    'properties_with_reviews': reviewed_properties,
                    'review_coverage': reviewed_properties / total_properties * 100 if total_properties else 0,
                },
            }
        except Exception as exc:
            logger.error("Error getting dashboard metrics: %s", exc)
            return {'error': str(exc)}

    def get_conversation_analytics(self, days: int = 7) -> Dict:
        try:
            end_date = timezone.now()
            start_date = end_date - timedelta(days=days)
            daily = Conversation.objects.filter(last_message_at__gte=start_date).extra(
                select={'day': 'date(last_message_at)'}
            ).values('day').annotate(count=Count('id')).order_by('day')
            total_messages = Conversation.objects.filter(last_message_at__gte=start_date).aggregate(
                total=Sum('message_count')
            )['total'] or 0
            active = Conversation.objects.filter(last_message_at__gte=end_date - timedelta(hours=24)).count()
            suspicious = Conversation.objects.filter(
                is_suspicious=True, last_message_at__gte=start_date
            ).count()
            return {
                'period_days': days,
                'daily_conversations': list(daily),
                'total_messages': total_messages,
                'active_conversations': active,
                'suspicious_conversations': suspicious,
                'avg_messages_per_conversation': total_messages / len(daily) if daily else 0,
            }
        except Exception as exc:
            logger.error("Error getting conversation analytics: %s", exc)
            return {'error': str(exc)}

    def get_property_analytics(self) -> Dict:
        try:
            active = Property.objects.filter(is_active=True)
            campus = active.values('campus_name').annotate(count=Count('id')).order_by('-count')
            prices = active.aggregate(
                avg_price=Avg('price_per_month'),
                min_price=Min('price_per_month'),
                max_price=Max('price_per_month'),
            )
            total_rooms = active.aggregate(total=Sum('total_rooms'))['total'] or 0
            available_rooms = active.aggregate(total=Sum('available_rooms'))['total'] or 0
            amenities = {}
            for prop in active.filter(amenities__isnull=False):
                for amenity in prop.amenities or []:
                    amenities[amenity] = amenities.get(amenity, 0) + 1
            return {
                'campus_distribution': list(campus),
                'price_statistics': {
                    'avg_price': float(prices['avg_price'] or 0),
                    'min_price': float(prices['min_price'] or 0),
                    'max_price': float(prices['max_price'] or 0),
                },
                'availability': {
                    'total_rooms': total_rooms,
                    'available_rooms': available_rooms,
                    'occupancy_rate': (total_rooms - available_rooms) / total_rooms * 100 if total_rooms else 0,
                },
                'top_amenities': sorted(amenities.items(), key=lambda item: item[1], reverse=True)[:10],
            }
        except Exception as exc:
            logger.error("Error getting property analytics: %s", exc)
            return {'error': str(exc)}


analytics = JeffAnalytics()

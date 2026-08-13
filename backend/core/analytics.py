"""
Analytics module for Jeff Platform
Provides insights and metrics for system monitoring
"""

from django.db.models import Count, Avg, Sum, Q, Min, Max
from django.utils import timezone
from datetime import timedelta
from typing import Dict, List
import logging

from .models import Property, Conversation, Booking, Review

logger = logging.getLogger(__name__)

class JeffAnalytics:
    """Analytics service for Jeff Platform"""
    
    def get_dashboard_metrics(self) -> Dict:
        """Get key dashboard metrics"""
        try:
            now = timezone.now()
            last_24h = now - timedelta(hours=24)
            last_7d = now - timedelta(days=7)
            last_30d = now - timedelta(days=30)
            
            # Basic counts
            total_properties = Property.objects.filter(is_active=True).count()

            total_conversations = Conversation.objects.count()
            
            # Recent activity
            recent_conversations = Conversation.objects.filter(
                last_message_at__gte=last_24h
            ).count()
            
            
            recent_bookings = Booking.objects.filter(
                created_at__gte=last_24h
            ).count()
            
            
            
            # Property statistics
            avg_property_rating = Property.objects.aggregate(
                avg_rating=Avg('provider__rating')
            )['avg_rating'] or 0
            
            properties_with_reviews = Property.objects.filter(
                reviews__isnull=False
            ).distinct().count()
            
            return {
                'overview': {
                    'total_properties': total_properties,
                    'total_conversations': total_conversations,
                },
                'recent_activity': {
                    'conversations_24h': recent_conversations,
                    'bookings_24h': recent_bookings,
                },
                'properties': {
                    'avg_rating': round(avg_property_rating, 2),
                    'properties_with_reviews': properties_with_reviews,
                    'review_coverage': (properties_with_reviews / total_properties * 100) if total_properties > 0 else 0,
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting dashboard metrics: {str(e)}")
            return {'error': str(e)}
    
    def get_conversation_analytics(self, days: int = 7) -> Dict:
        """Get conversation analytics for the last N days"""
        try:
            end_date = timezone.now()
            start_date = end_date - timedelta(days=days)
            
            # Daily conversation counts
            daily_conversations = Conversation.objects.filter(
                last_message_at__gte=start_date
            ).extra(
                select={'day': 'date(last_message_at)'}
            ).values('day').annotate(
                count=Count('id')
            ).order_by('day')
            
            # Message volume
            total_messages = Conversation.objects.filter(
                last_message_at__gte=start_date
            ).aggregate(
                total=Sum('message_count')
            )['total'] or 0
            
            # Active conversations (conversations with messages in last 24h) 
            active_conversations = Conversation.objects.filter(
                last_message_at__gte=end_date - timedelta(hours=24)
            ).count()
            
            # Suspicious activity
            suspicious_conversations = Conversation.objects.filter(
                is_suspicious=True,
                last_message_at__gte=start_date
            ).count()
            
            return {
                'period_days': days,
                'daily_conversations': list(daily_conversations),
                'total_messages': total_messages,
                'active_conversations': active_conversations,
                'suspicious_conversations': suspicious_conversations,
                'avg_messages_per_conversation': total_messages / len(daily_conversations) if daily_conversations else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting conversation analytics: {str(e)}")
            return {'error': str(e)}
    
    def get_property_analytics(self) -> Dict:
        """Get property analytics and insights"""
        try:
            # Property distribution by campus
            campus_distribution = Property.objects.filter(
                is_active=True
            ).values('campus_name').annotate(
                count=Count('id')
            ).order_by('-count')
            
            # Price distribution
            price_stats = Property.objects.filter(
                is_active=True
            ).aggregate(
                avg_price=Avg('price_per_month'),
                min_price=Min('price_per_month'),
                max_price=Max('price_per_month')
            )
            
            # Room size distribution
            room_size_distribution = Property.objects.filter(
                is_active=True
            ).annotate(
                count=Count('id')
            )
            
            # Availability stats
            total_rooms = Property.objects.filter(
                is_active=True
            ).aggregate(
                total=Sum('total_rooms')
            )['total'] or 0
            
            available_rooms = Property.objects.filter(
                is_active=True
            ).aggregate(
                total=Sum('available_rooms')
            )['total'] or 0
            
            # Top amenities
            # Note: This is a simplified version. In production, you'd want to properly
            # aggregate JSON field data
            amenities_count = {}
            for prop in Property.objects.filter(is_active=True, amenities__isnull=False):
                for amenity in prop.amenities or []:
                    amenities_count[amenity] = amenities_count.get(amenity, 0) + 1
            
            top_amenities = sorted(
                amenities_count.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:10]
            
            return {
                'campus_distribution': list(campus_distribution),
                'price_statistics': {
                    'avg_price': float(price_stats['avg_price'] or 0),
                    'min_price': float(price_stats['min_price'] or 0),
                    'max_price': float(price_stats['max_price'] or 0),
                },
                'room_size_distribution': list(room_size_distribution),
                'availability': {
                    'total_rooms': total_rooms,
                    'available_rooms': available_rooms,
                    'occupancy_rate': ((total_rooms - available_rooms) / total_rooms * 100) if total_rooms > 0 else 0
                },
                'top_amenities': top_amenities
            }
            
        except Exception as e:
            logger.error(f"Error getting property analytics: {str(e)}")
            return {'error': str(e)}
    
# Global instance
analytics = JeffAnalytics()

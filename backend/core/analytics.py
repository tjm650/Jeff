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

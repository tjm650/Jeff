from decimal import Decimal

from django.test import TestCase

from core.models import AccommodationProvider, Property
from providers.insights.insights import InsightsHandler


class InsightsHandlerTests(TestCase):
    def setUp(self):
        self.provider = AccommodationProvider.objects.create(
            phone_number='+100000000', name='Prov', email='prov@example.com', verified=True
        )
        self.prop = Property.objects.create(
            provider=self.provider,
            property_no='AB-1234',
            name='Test Property',
            address='Somewhere',
            description='',
            total_rooms=5,
            available_rooms=5,
            price_per_semester=Decimal('0.00'),
            price_per_month=Decimal('0.00'),
            price_per_week=Decimal('0.00'),
            price_per_day=Decimal('0.00'),
            distance_from_campus=1.0,
            campus_name='Main',
            gender_preference='any'
        )

    def test_submit_partial_insights_updates_fields(self):
        insights = {
            'gender_preference': 'female',
            'total_rooms': 4,
            'available_rooms': 2,
            'available_slots': {'1h/room': 1, '2h/room': 1},
            'amenities': ['Wifi', 'Gas stove'],
            'pricing': {'price/term': '1000.00', 'price/month': '100.00', 'price/week': '25.00', 'price/day': '5.00'}
        }

        res = InsightsHandler.submit_insights(
            provider_phone=self.provider.phone_number,
            property_no=self.prop.property_no,
            insights=insights,
        )
        self.assertTrue(res['success'])

        p = Property.objects.get(id=self.prop.id)
        self.assertEqual(p.gender_preference, 'female')
        self.assertEqual(p.total_rooms, 4)
        self.assertEqual(p.available_rooms, 2)
        self.assertEqual(p.available_1h_rooms, 1)
        self.assertEqual(p.available_2h_rooms, 1)
        self.assertIn('Wifi', p.amenities)
        self.assertIn('Gas stove', p.amenities)
        self.assertEqual(p.price_per_semester, Decimal('1000.00'))
        self.assertEqual(p.price_per_month, Decimal('100.00'))
        self.assertEqual(p.price_per_week, Decimal('25.00'))
        self.assertEqual(p.price_per_day, Decimal('5.00'))

    def test_cannot_update_property_not_owned_by_provider(self):
        other = AccommodationProvider.objects.create(phone_number='+200000', name='Other', email='other@example.com')
        insights = {'available_rooms': 1}
        res = InsightsHandler.submit_insights(
            provider_phone=other.phone_number,
            property_no=self.prop.property_no,
            insights=insights,
        )
        self.assertFalse(res['success'])
        self.assertIn('not found for this provider', res['message'])

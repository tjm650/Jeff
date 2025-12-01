import json
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from .nlp_processor import nlp_processor
from .property_matcher import property_matcher
from core.models import Property

@require_http_methods(["GET"])
def matching_index(request):
    """Property matching API index"""
    return JsonResponse({
        'status': 'ok',
        'service': 'Jeff Property Matching API',
        'version': '1.0.0',
        'endpoints': [
            '/api/matching/search/',
            '/api/matching/match/',
            '/api/matching/properties/',
            '/api/matching/nlp/test/'
        ]
    })

@csrf_exempt
@require_http_methods(["POST"])
def search_properties(request):
    """Search properties based on requirements"""
    try:
        data = json.loads(request.body)
        requirements_text = data.get('requirements', '')

        if not requirements_text:
            return JsonResponse({
                'status': 'error',
                'message': 'Requirements text is required'
            }, status=400)

        # Extract requirements using NLP
        requirements = nlp_processor.extract_requirements(requirements_text)

        # Find matching properties
        matched_properties = property_matcher.match_properties(requirements, limit=5)

        # Format response
        properties = []
        for match in matched_properties:
            prop = match['property']
            properties.append({
                'id': prop.id,
                'name': prop.name,
                'price_per_month': float(prop.price_per_month),
                'room_config': {
                    'single': prop.available_1h_rooms,
                    'double': prop.available_2h_rooms,
                    'triple': prop.available_3h_rooms,
                    'quad': prop.available_4h_rooms
                },
                'distance_from_campus': float(prop.distance_from_campus),
                'campus_name': prop.campus_name,
                'amenities': prop.amenities or [],
                'available_rooms': prop.available_rooms,
                'match_score': match['score']
            })

        return JsonResponse({
            'status': 'ok',
            'requirements_extracted': requirements,
            'properties': properties,
            'total_found': len(properties)
        })

    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Search error: {str(e)}'
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def match_properties(request):
    """Match properties with detailed requirements"""
    try:
        data = json.loads(request.body)
        requirements = data.get('requirements', {})

        if not requirements:
            return JsonResponse({
                'status': 'error',
                'message': 'Requirements object is required'
            }, status=400)

        # Find matching properties
        matched_properties = property_matcher.match_properties(requirements, limit=5)

        # Format detailed response
        results = []
        for match in matched_properties:
            prop = match['property']
            results.append({
                'property': {
                    'id': prop.id,
                    'name': prop.name,
                    'price_per_month': float(prop.price_per_month),
                    'room_config': {
                        'single': prop.available_1h_rooms,
                        'double': prop.available_2h_rooms,
                        'triple': prop.available_3h_rooms,
                        'quad': prop.available_4h_rooms
                    },
                    'distance_from_campus': float(prop.distance_from_campus),
                    'campus_name': prop.campus_name,
                    'amenities': prop.amenities or [],
                    'available_rooms': prop.available_rooms,
                    'gender_preference': prop.gender_preference,
                    'is_active': prop.is_active
                },
                'match_score': match['score'],
                'match_reasons': match.get('match_reasons', [])
            })

        return JsonResponse({
            'status': 'ok',
            'matches': results,
            'total_found': len(results)
        })

    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Matching error: {str(e)}'
        }, status=500)

@require_http_methods(["GET"])
def list_properties(request):
    """List all available properties"""
    try:
        # Get query parameters
        campus = request.GET.get('campus')
        max_price = request.GET.get('max_price')
        heads = request.GET.get('heads')

        # Build query
        properties = Property.objects.filter(is_active=True)

        if campus:
            properties = properties.filter(campus_name__icontains=campus)

        if max_price:
            properties = properties.filter(price_per_month__lte=max_price)

        if heads:
            # Filter by head configuration
            heads = int(heads)
            if heads == 1:
                properties = properties.filter(available_1h_rooms__gt=0)
            elif heads == 2:
                properties = properties.filter(available_2h_rooms__gt=0)
            elif heads == 3:
                properties = properties.filter(available_3h_rooms__gt=0)
            elif heads == 4:
                properties = properties.filter(available_4h_rooms__gt=0)

        # Apply default ordering: rating (desc), then price, then distance
        properties = properties.order_by('-rating', 'price_per_month', 'distance_from_campus')[:20]

        # Format response
        props_list = []
        for prop in properties:
            props_list.append({
                'id': prop.id,
                'name': prop.name,
                'price_per_month': float(prop.price_per_month),
                'room_config': {
                    'single': prop.available_1h_rooms,
                    'double': prop.available_2h_rooms,
                    'triple': prop.available_3h_rooms,
                    'quad': prop.available_4h_rooms
                },
                'distance_from_campus': float(prop.distance_from_campus),
                'campus_name': prop.campus_name,
                'amenities': prop.amenities or [],
                'available_rooms': prop.available_rooms,
                'gender_preference': prop.gender_preference
            })

        return JsonResponse({
            'status': 'ok',
            'properties': props_list,
            'total_found': len(props_list)
        })

    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'List properties error: {str(e)}'
        }, status=500)

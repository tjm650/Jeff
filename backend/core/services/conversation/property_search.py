"""
Property search and formatting handlers

This module handles property search operations including:
- Property search execution using property matcher
- Search result processing and enhancement
- Property listing formatting
- Search criteria relaxation
- Match reason calculation
"""

import logging, os
from typing import Dict, List
from django.utils import timezone

logger = logging.getLogger(__name__)


class PropertySearchHandler:
    """Property search and formatting functionality"""

    def proceed_to_property_search(self, conversation, requirements: Dict) -> str:
        """Proceed with property search using enhanced NLP requirements"""
        try:
            logger.info(f"Starting property search for {conversation.cell_number}")

            # Get validated requirements from conversation context
            validated_requirements = requirements.get('validated_requirements', requirements)
            logger.info(f"Validated requirements: {validated_requirements}")

            # Validate that we have requirements to work with
            if not validated_requirements:
                logger.error(f"No validated requirements found for {conversation.cell_number}")
                return "Error: No valid requirements found. Please try again."

            # Ensure we have at least some structured search criteria OR keywords/raw message to attempt
            search_criteria = ['heads', 'budget_max', 'amenities', 'location_context', 'gender_preference']
            has_structured = any(validated_requirements.get(criteria) for criteria in search_criteria)

            # If MCP/keyword expansion produced keywords, or a raw message exists, we can attempt a probable search
            has_keywords = bool(validated_requirements.get('expanded_keywords') or validated_requirements.get('keyword_tokens'))
            has_raw_message = bool(validated_requirements.get('raw_message'))

            if not (has_structured or has_keywords or has_raw_message):
                logger.error(f"No search criteria or keywords found in requirements for {conversation.cell_number}: {validated_requirements}")
                return "Error: No search criteria found. Please provide more details about what you're looking for."

            # Add search metadata
            search_metadata = {
                'search_timestamp': timezone.now().isoformat(),
                'confidence_score': requirements.get('confidence_score', 0.0),
                'nlp_processed': requirements.get('nlp_processed', False)
            }

            # Find matching properties using enhanced requirements
            logger.info(f"Calling property_matcher.match_properties for {conversation.cell_number}")
            from matching.property_matcher import property_matcher
            matched_properties = property_matcher.match_properties(validated_requirements, limit=5)
            logger.info(f"Property matcher returned {len(matched_properties) if matched_properties else 0} properties")

            if not matched_properties:
                # Try with relaxed criteria if no matches found
                logger.info(f"No properties found, trying relaxed criteria for {conversation.cell_number}")
                relaxed_requirements = self._relax_search_criteria(validated_requirements)
                if relaxed_requirements != validated_requirements:
                    logger.info(f"Retrying search with relaxed criteria for {conversation.cell_number}")
                    matched_properties = property_matcher.match_properties(relaxed_requirements, limit=3)
                    logger.info(f"Relaxed search returned {len(matched_properties) if matched_properties else 0} properties")

                if not matched_properties:
                    logger.info(f"No properties found even with relaxed criteria for {conversation.cell_number}")
                    return self._get_no_properties_message(validated_requirements, conversation.cell_number)

            # Process and enhance property data
            logger.info(f"Processing {len(matched_properties)} search results for {conversation.cell_number}")
            try:
                properties_list = self._process_search_results(matched_properties, validated_requirements)
                logger.info(f"Processed {len(properties_list)} properties successfully")
            except Exception as e:
                logger.error(f"Error processing search results for {conversation.cell_number}: {str(e)}", exc_info=True)
                return "Error processing search results. Please try again."

            # Additionally include properties that are below the user's budget (if budget provided)
            try:
                budget_max = validated_requirements.get('budget_max')
                if budget_max:
                    # Determine which price field to use for the budget filter
                    period = validated_requirements.get('rental_period') or validated_requirements.get('budget_unit')
                    # Import Property model locally to avoid circular imports
                    from core.models import Property

                    # Build a queryset of properties within budget but not already in matched_properties
                    existing_ids = set()
                    for item in matched_properties:
                        try:
                            pid = getattr(item.get('property'), 'id', None)
                            if pid:
                                existing_ids.add(pid)
                        except Exception:
                            continue

                    # Apply a lower-bound slack so we append properties within 20% below the budget
                    try:
                        budget_val = float(budget_max)
                    except Exception:
                        budget_val = budget_max

                    # Slack fraction: default to 0.2 (20% below budget)
                    try:
                        slack = float(validated_requirements.get('append_lower_slack', 0.2))
                        if slack < 0:
                            slack = 0.2
                    except Exception:
                        slack = 0.2

                    lower_bound = max(0.0, budget_val * (1.0 - slack)) if isinstance(budget_val, (int, float)) else None

                    if period == 'day':
                        if lower_bound is not None:
                            budget_qs = Property.objects.filter(is_active=True, price_per_day__gte=lower_bound, price_per_day__lte=budget_val)
                        else:
                            budget_qs = Property.objects.filter(is_active=True, price_per_day__lte=budget_val)
                    elif period == 'week':
                        if lower_bound is not None:
                            budget_qs = Property.objects.filter(is_active=True, price_per_week__gte=lower_bound, price_per_week__lte=budget_val)
                        else:
                            budget_qs = Property.objects.filter(is_active=True, price_per_week__lte=budget_val)
                    else:
                        if lower_bound is not None:
                            budget_qs = Property.objects.filter(is_active=True, price_per_month__gte=lower_bound, price_per_month__lte=budget_val)
                        else:
                            budget_qs = Property.objects.filter(is_active=True, price_per_month__lte=budget_val)

                    # Exclude already included properties
                    if existing_ids:
                        budget_qs = budget_qs.exclude(id__in=list(existing_ids))

                    # Limit how many budget-only properties we append to avoid huge context_data
                    budget_candidates = list(budget_qs.select_related('provider')[:5])
                    if budget_candidates:
                        # Convert them into the same match format and process
                        budget_matches = [{'property': p, 'score': 0, 'match_reasons': ['Below budget']} for p in budget_candidates]
                        budget_props_list = self._process_search_results(budget_matches, validated_requirements)
                        if budget_props_list:
                            # Mark these as budget_fallback for clarity
                            for bp in budget_props_list:
                                bp.setdefault('match_reasons', []).insert(0, 'Below budget')
                            properties_list.extend(budget_props_list)
                            logger.info(f"Appended {len(budget_props_list)} budget properties for {conversation.cell_number}")
            except Exception as e:
                logger.warning(f"Failed to append below-budget properties: {e}")

            # Update conversation state with comprehensive search data
            try:
                # Validate data before saving
                if not isinstance(properties_list, list):
                    logger.error(f"Properties list is not a list for {conversation.cell_number}")
                    return "Error: Invalid search results format. Please try again."

                if len(properties_list) > 50:  # Reasonable limit
                    logger.warning(f"Too many properties ({len(properties_list)}) for {conversation.cell_number}, limiting to 50")
                    properties_list = properties_list[:50]

                conversation.context_data.update({
                    'search_results': properties_list,
                    'search_metadata': search_metadata,
                    'search_requirements': validated_requirements,
                    # initialize pagination cursor
                    'current_property_page': 0,
                    'total_matches': len(properties_list)
                })
                conversation.current_step = 'property_listings'

                # Validate context_data size (JSON field limit)
                import json
                context_json = json.dumps(conversation.context_data)
                if len(context_json) > 1000000:  # 1MB limit for JSON field
                    logger.error(f"Context data too large for {conversation.cell_number}: {len(context_json)} bytes")
                    return "Error: Search results too large. Please try with more specific requirements."

                conversation.save()
                logger.info(f"Conversation state updated successfully for {conversation.cell_number}")
            except Exception as e:
                logger.error(f"Error updating conversation state for {conversation.cell_number}: {str(e)}", exc_info=True)
                return "Error updating conversation state. Please try again."

            logger.info(f"Property search completed for {conversation.cell_number}: {len(properties_list)} matches")

            # Format and return property listing
            try:
                return self._format_enhanced_property_listing(properties_list, validated_requirements, conversation)
            except Exception as e:
                logger.error(f"Error formatting property listing for {conversation.cell_number}: {str(e)}", exc_info=True)
                return "Error formatting results. Please try again."

        except Exception as e:
            logger.error(f"Error in property search for {conversation.cell_number}: {str(e)}", exc_info=True)
            return "Error searching for properties. Please try again."

    def _relax_search_criteria(self, requirements: Dict) -> Dict:
        """Relax search criteria if no matches found"""
        try:
            relaxed = requirements.copy()

            # Remove very specific constraints
            if relaxed.get('budget_max'):
                # Increase budget range by 20%
                relaxed['budget_max'] = relaxed['budget_max'] * 1.2

            # If no amenities specified, don't filter by amenities
            if not relaxed.get('amenities'):
                relaxed['amenities'] = []

            # If location is too specific, broaden it
            if relaxed.get('location_context') and len(relaxed['location_context']) < 3:
                relaxed['location_context'] = None

            return relaxed

        except Exception as e:
            logger.error(f"Error relaxing search criteria: {str(e)}")
            return requirements

    def _get_no_properties_message(self, requirements: Dict, cell_number: str = None) -> str:
        """Generate recommendation summary when no properties found
        
        Notifies both token-paid and non-token users with recommendations.
        No payment instructions for this notification.
        """
        try:
            # If there are generally no properties available in the database,
            # return a clear, user-friendly message.
            try:
                from core.models import Property
                if not Property.objects.filter(is_active=True).exists():
                    return "No available Accommodation at the moment."
            except Exception as e:
                logger.warning(f"Failed checking global property availability: {e}")

            # Check if user has a valid token
            has_valid_token = False
            if cell_number:
                try:
                    logger.info(f"Token status for {cell_number}: has_valid_token={has_valid_token}")
                except Exception as e:
                    logger.warning(f"Failed to check token status for {cell_number}: {e}")

            # Import recommendation service from MCP integration
            from ..mcp.integration import get_mcp_integration
            mcp_integration = get_mcp_integration()

            # Generate recommendation summary based on token status
            recommendation = None
            if mcp_integration and mcp_integration.recommendation_service:
                # Generate recommendation summary using MCP for both token and non-token users
                recommendation = mcp_integration.recommendation_service.generate_recommendation_summary(requirements)
            else:
                # Fallback when MCP integration is not available
                recommendation = self._get_fallback_recommendation_message(requirements)

            # Add appropriate notification based on token status
            if has_valid_token:
                # Token user - show recommendation without payment instructions
                notification_header = "*No Properties Found*\n\n"
                notification_footer = "\n\n_Please try refining your search criteria or contact support for assistance._"
            else:
                # Non-token user - show recommendation without payment instructions
                notification_header = "*No Properties Found*\n\n"
                notification_footer = "\n\n_Please try refining your search criteria or contact support for assistance._"

            # Combine header, recommendation, and footer
            return notification_header + (recommendation or "") + notification_footer

        except Exception as e:
            logger.error(f"Error generating recommendation message: {str(e)}")
            return "No properties found matching your requirements. Please try different criteria or contact support."

    def _process_search_results(self, matched_properties: List, requirements: Dict) -> List:
        """Process and enhance search results with additional context"""
        try:
            properties_list = []

            for i, match in enumerate(matched_properties):
                try:
                    property = match['property']
                    logger.info(f"Processing property {i+1}: {property.name if hasattr(property, 'name') else 'Unknown'}")

                    # Validate required property attributes
                    if not hasattr(property, 'id') or not property.id:
                        logger.warning(f"Property {i+1} missing ID, skipping")
                        continue

                    if not hasattr(property, 'name') or not property.name:
                        logger.warning(f"Property {i+1} missing name, skipping")
                        continue

                    enhanced_property = {
                        'id': str(property.id),
                        'name': property.name,
                        'rating': float(getattr(property, 'rating', 0.0) or 0.0),
                        'price_per_month': float(property.price_per_month) if property.price_per_month else 0.0,
                        'price_per_week': float(property.price_per_week) if property.price_per_week else 0.0,
                        'price_per_day': float(property.price_per_day) if property.price_per_day else 0.0,
                        # 'heads_per_room': property.heads_per_room if property.heads_per_room else 1,
                        'distance_from_campus': float(property.distance_from_campus) if property.distance_from_campus else 0.0,
                        'amenities': property.amenities or [],
                        'available_rooms': property.available_rooms if property.available_rooms else 0,
                        'available_1h_rooms': getattr(property, 'available_1h_rooms', 0) or 0,
                        'available_2h_rooms': getattr(property, 'available_2h_rooms', 0) or 0,
                        'available_3h_rooms': getattr(property, 'available_3h_rooms', 0) or 0,
                        'available_4h_rooms': getattr(property, 'available_4h_rooms', 0) or 0,
                        'campus_name': property.campus_name or 'Unknown Campus',
                        'match_score': match.get('score', 0),
                        'match_reasons': self._get_match_reasons(match, requirements)
                    }

                    # Compute total available heads across all room types
                    try:
                        a1 = int(enhanced_property['available_1h_rooms'])
                        a2 = int(enhanced_property['available_2h_rooms'])
                        a3 = int(enhanced_property['available_3h_rooms'])
                        a4 = int(enhanced_property['available_4h_rooms'])
                        total_heads = (a1) + (a2) + (a3) + (a4)
                    except Exception:
                        total_heads = 0
                    enhanced_property['total_available_heads'] = total_heads

                    # Add price per head calculation
                    # if enhanced_property['heads_per_room'] and enhanced_property['heads_per_room'] > 0:
                    #     enhanced_property['price_per_head'] = round(
                    #         enhanced_property['price_per_month'], 2
                    #     )

                    properties_list.append(enhanced_property)
                    logger.info(f"Successfully processed property {i+1}: {enhanced_property['name']}")

                except Exception as e:
                    logger.error(f"Error processing individual property {i+1}: {str(e)}", exc_info=True)
                    continue

            logger.info(f"Successfully processed {len(properties_list)} out of {len(matched_properties)} properties")
            return properties_list

        except Exception as e:
            logger.error(f"Error processing search results: {str(e)}", exc_info=True)
            return []

    def _get_match_reasons(self, match: Dict, requirements: Dict) -> List[str]:
        """Get reasons why a property matched the requirements"""
        try:
            reasons = []
            property = match.get('property')

            if not property:
                logger.warning("No property found in match data")
                return reasons

            # Validate property attributes before accessing them
            # if not hasattr(property, 'heads_per_room'):
            #     logger.warning("Property missing heads_per_room attribute")
                return reasons

            if not hasattr(property, 'price_per_month'):
                logger.warning("Property missing price_per_month attribute")
                return reasons

            if not hasattr(property, 'campus_name'):
                logger.warning("Property missing campus_name attribute")
                return reasons

            # Check various matching criteria
            # if requirements.get('heads') and property.heads_per_room == requirements['heads']:
                reasons.append("Perfect head count match")

            if requirements.get('budget_max') and property.price_per_month <= requirements['budget_max']:
                reasons.append("Within budget")

            if requirements.get('amenities'):
                property_amenities = set(property.amenities or [])
                requested_amenities = set(requirements['amenities'])
                matching_amenities = property_amenities.intersection(requested_amenities)
                if matching_amenities:
                    reasons.append(f"Has {', '.join(list(matching_amenities)[:2])}")

            if requirements.get('location_context'):
                if (property.campus_name and
                    requirements['location_context'].lower() in property.campus_name.lower()):
                    reasons.append("Location match")

            return reasons[:2]  # Limit to top 2 reasons

        except Exception as e:
            logger.error(f"Error getting match reasons: {str(e)}", exc_info=True)
            return []

    def _format_enhanced_property_listing(self, properties: List[Dict], requirements: Dict, conversation=None) -> str:
        """Format enhanced property listings with NLP-derived insights"""
        try:
            if not properties:
                # Delegate to the shared "no properties" handler which also checks
                # for global availability and MCP recommendations.
                cell_number = conversation.cell_number if conversation else None
                return self._get_no_properties_message(requirements, cell_number)

            if not isinstance(properties, list):
                logger.error(f"Properties is not a list: {type(properties)}")
                return " Error formatting results. Please try again."

            # Add search summary
            confidence = requirements.get('confidence_score', 0) if isinstance(requirements, dict) else 0
            message = f"""*PROPERTY LISTINGS* 🏡
*Properties Found:* {len(properties)}\n"""

            if confidence > 0:
                confidence_emoji = "🟢" if confidence > 0.7 else "🟡" if confidence > 0.4 else "🟠"
                message += f"*Match confidence*: ({int(confidence * 100)}%) {confidence_emoji}\n\n"
            else:
                message += ":\n\n"

            # Determine current page (prefer conversation context if available so 'show-more' works)
            if conversation is not None:
                try:
                    current_page = int(conversation.context_data.get('current_property_page', 0) or 0)
                except Exception:
                    current_page = 0
            else:
                if isinstance(requirements, dict):
                    try:
                        current_page = int(requirements.get('current_property_page', 0) or 0)
                    except Exception:
                        current_page = 0
                else:
                    current_page = 0

            # Sort properties according to user preference: Price, Distance, Wifi amenity
            try:
                # Choose price field according to rental_period if provided
                period = requirements.get('rental_period') if isinstance(requirements, dict) else None
                # Check if inverted sort is requested (top-down: highest price first, furthest first, wifi last)
                invert_sort = bool(requirements.get('invert_sort', False)) if isinstance(requirements, dict) else False

                def _sort_price(p):
                    # Determine the price to use for sorting
                    if period == 'day':
                        sp = p.get('price_per_day', 0) or 0
                    elif period == 'week':
                        sp = p.get('price_per_week', 0) or 0
                    else:
                        sp = p.get('price_per_month', 0) or 0
                    # If no price available, push to the end
                    price = float(sp) if isinstance(sp, (int, float)) and sp > 0 else float('inf')
                    # For inverted sort, negate finite prices but keep inf at end
                    return -price if invert_sort and price != float('inf') else price

                def _sort_distance(p):
                    distance = float(p.get('distance_from_campus', float('inf')) if p.get('distance_from_campus') is not None else float('inf'))
                    return -distance if invert_sort else distance

                def _has_wifi(p):
                    amenities = p.get('amenities') or []
                    wifi_flag = 1 if any((a or '').lower() == 'wifi' or 'wifi' in (a or '').lower() for a in amenities) else 0
                    # For normal sort: -wifi_flag so wifi=1 sorts first
                    # For inverted sort: wifi_flag so wifi=1 sorts last
                    return wifi_flag if invert_sort else -wifi_flag

                def _sort_rating(p):
                    # Higher rating should come first; default 0 for unrated
                    rating = float(p.get('rating', 0.0) or 0.0)
                    # For inverted sort, lowest rating first
                    return rating if invert_sort else -rating

                # Sort by rating, price, distance, wifi (direction depends on invert_sort)
                properties.sort(key=lambda p: (
                    _sort_rating(p),
                    _sort_price(p),
                    _sort_distance(p),
                    _has_wifi(p)
                ))
            except Exception as e:
                logger.warning(f"Sorting properties failed, continuing without custom sort: {e}")

            start_idx = current_page * 5
            end_idx = start_idx + 5

            # Get current page's properties
            current_properties = properties[start_idx:end_idx]

            for i, prop in enumerate(current_properties, 1):
                try:
                    if not isinstance(prop, dict):
                        logger.warning(f"Property {i} is not a dict: {type(prop)}")
                        continue

                    # Validate required property fields
                    if 'name' not in prop:
                        logger.warning(f"Property {i} missing name field")
                        continue

                    emoji_number = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"][i-1]

                    # Display property name in UPPER CASE as requested
                    prop_name = prop.get('name', '')
                    message += f"{emoji_number}. *{prop_name.upper()}*\n"

                    # Show all pricing categories explicitly (monthly, weekly, daily)
                    month_price = prop.get('price_per_month', 0) or 0
                    week_price = prop.get('price_per_week', 0) or 0
                    day_price = prop.get('price_per_day', 0) or 0

                    # Monthly rate
                    if isinstance(month_price, (int, float)) and month_price > 0:
                        message += f"• Monthly price: ${month_price:.2f}\n"
                    else:
                        message += "• Monthly price: N/A\n"

                    # Weekly rate
                    if isinstance(week_price, (int, float)) and week_price > 0:
                        message += f"• Weekly price: ${week_price:.2f}\n"
                    else:
                        message += "• Weekly price: N/A\n"

                    # Daily rate
                    if isinstance(day_price, (int, float)) and day_price > 0:
                        message += f"• Daily price: ${day_price:.2f}\n"
                    else:
                        message += "• Daily price: N/A\n"

                    # Detailed availability by heads-per-room
                    a1 = prop.get('available_1h_rooms', 0) or 0
                    a2 = prop.get('available_2h_rooms', 0) or 0
                    a3 = prop.get('available_3h_rooms', 0) or 0
                    a4 = prop.get('available_4h_rooms', 0) or 0
                    message += f"• 1H/R: {int(a1)} available\n" if isinstance(a1, (int, float)) and a1 > 0 else "1H/R: N/A\n"
                    message += f"• 2H/R: {int(a2)} available\n" if isinstance(a2, (int, float)) and a2 > 0 else "2H/R: N/A\n"
                    message += f"• 3H/R: {int(a3)} available\n" if isinstance(a3, (int, float)) and a3 > 0 else "3H/R: N/A\n"
                    message += f"• 4H/R: {int(a4)} available\n" if isinstance(a4, (int, float)) and a4 > 0 else "4H/R: N/A\n"

                    # Total available heads line
                    total_heads = prop.get('total_available_heads', 0) or 0
                    if isinstance(total_heads, (int, float)) and total_heads > 0:
                        message += f"Total Available Heads: {int(total_heads)} or N/A\n"
                    else:
                        message += "Total Available Heads: N/A\n"

               

                    # # Also include a compact prices summary when available
                    # prices_parts = []
                    # if month_price > 0:
                    #     prices_parts.append(f"${month_price:.2f}/month")
                    # if week_price > 0:
                    #     prices_parts.append(f"${week_price:.2f}/week")
                    # if day_price > 0:
                    #     prices_parts.append(f"${day_price:.2f}/day")

                    # if prices_parts:
                    #     message += f"Prices: {' | '.join(prices_parts)}\n"

                    # # Add price per head if available
                    # if 'price_per_head' in prop:
                    #     price_per_head = prop['price_per_head']
                    #     if isinstance(price_per_head, (int, float)):
                    #         message += f"Price/head: (${price_per_head}/head)"

                    # message += "\n"

                    # # Safe access to other fields
                    # heads = prop.get('heads_per_room', 1)
                    # if isinstance(heads, (int, float)):
                    #     message += f"h/p: {int(heads)} heads per room\n"

                    distance = prop.get('distance_from_campus', 0)
                    if isinstance(distance, (int, float)):
                        message += f"Distance: *{distance}km* from campus\n"

                    # Show top amenities
                    amenities = prop.get('amenities', [])
                    if amenities and isinstance(amenities, list):
                        safe_amenities = amenities[:3]
                        message += f"Amenities: {', '.join(safe_amenities)}\n"
                        
                    
                    # available_rooms = prop.get('available_rooms', 0)
                    # if isinstance(available_rooms, (int, float)):
                    #     message += f"Available Rooms: {int(available_rooms)}\n"

                    # Show match reasons if available
                    match_reasons = prop.get('match_reasons', [])
                    if match_reasons and isinstance(match_reasons, list) and len(match_reasons) > 0:
                        message += f"{match_reasons[0]}: ✅\n\n"

                    
                except Exception as e:
                    logger.error(f"Error formatting property {i}: {str(e)}", exc_info=True)
                    continue
            # Add property count info and pagination status if applicable
            total_properties = len(properties)
            
            frontend_url = os.getenv('NEXT_PUBLIC_FRONTEND_URL')
            if total_properties > 5:
                message += f"\n*Showing properties {start_idx + 1}-{min(end_idx, total_properties)} of {total_properties}*\n"

            # Add helpful footer
            message += f"""\n\n_1. Reply with 'option-(number)' to proceed for booking (e.g. 'option-1')_
_2. Send an abort message to cancel your enquiry and start a different search._
• _By selecting a property listing, you agree to the terms and usage of the service_
• _Send 'Jeff' message for more info about the service, Privacy Policy and Terms & Conditions of service or visit {frontend_url}_
"""


            # Add show-more instructions if there are more properties to show
            if end_idx < total_properties:
                message += "\n_3. Send 'show-more' to view more properties_"

            return message

        except Exception as e:
            logger.error(f"Error in format_enhanced_property_listing: {str(e)}", exc_info=True)
            return "Error formatting property listings. Please try again."

    def show_property_listings(self, conversation) -> str:
        """Show property listings from conversation context data"""
        try:
            # Get search results from conversation context
            search_results = conversation.context_data.get('search_results', [])
            search_metadata = conversation.context_data.get('search_metadata', {})
            search_requirements = conversation.context_data.get('search_requirements', {})

            if not search_results:
                logger.warning(f"No search results found in conversation context for {conversation.cell_number}")
                # Get requirements from context
                search_requirements = conversation.context_data.get('search_requirements', {})
                # Import recommendation service from MCP integration
                from ..mcp.integration import get_mcp_integration
                mcp_integration = get_mcp_integration()
                if mcp_integration and mcp_integration.recommendation_service:
                    return mcp_integration.recommendation_service.generate_recommendation_summary(search_requirements)
                else:
                    # Fallback when MCP integration is not available
                    return self._get_fallback_recommendation_message(search_requirements)

            # Get latest requirements from conversation context to ensure sorting preferences are applied
            updated_requirements = conversation.context_data.get('search_requirements', {})
            
            # Format and return the property listings using the existing formatter with updated requirements
            return self._format_enhanced_property_listing(search_results, updated_requirements, conversation)

        except Exception as e:
            logger.error(f"Error showing property listings for {conversation.cell_number}: {str(e)}", exc_info=True)
            return "Error displaying property listings. Please try again."


    def _get_fallback_recommendation_message(self, requirements: Dict) -> str:
        """Get fallback recommendation message when MCP integration is not available"""
        try:
            message = "No properties found matching your exact requirements.\n\n"

            # Provide basic suggestions based on requirements
            suggestions = []

            if requirements.get('budget_max'):
                suggestions.append(f"Consider adjusting your budget (currently ${requirements['budget_max']})")

            if requirements.get('heads'):
                suggestions.append(f"Try different room sharing options for {requirements['heads']} people")

            if requirements.get('amenities'):
                suggestions.append("Consider properties with fewer amenities to increase options")

            if not suggestions:
                suggestions = [
                    "Try expanding your location search",
                    "Consider adjusting your budget range",
                    "Look for properties with different amenities"
                ]

            message += "Suggestions:\n"
            for suggestion in suggestions[:3]:
                message += f"- {suggestion}\n"

            message += "\nPlease refine your requirements or contact support for assistance."

            return message

        except Exception as e:
            logger.error(f"Error generating fallback recommendation: {str(e)}")
            return ("No properties found matching your requirements. "
                    "Please try adjusting your criteria such as budget, location, or amenities. "
                    "Contact support for personalized assistance.")


# Global instance
property_search_handler = PropertySearchHandler()
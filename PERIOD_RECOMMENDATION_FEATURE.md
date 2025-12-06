# Period Recommendation and Weekly/Daily Rental Search Feature

## Overview
This feature implements two key functionalities:
1. **Period Recommendation**: When a user provides an accommodation search message without specifying a rental period (daily/weekly/monthly), the system recommends periods while still allowing the search to proceed with a sensible default.
2. **Weekly/Daily Period Support**: Enable full support for weekly and daily rental period searches, not just monthly rentals.

## Changes Made

### 1. NLP Processor Enhancement (`nlp_processor.py`)

**File**: `backend/core/services/conversation/nlp_processor.py`

**Change**: Modified the `extract_requirements()` method to handle missing rental periods gracefully:

```python
# Before: Blocked search if period not specified
if not processed_requirements.get('rental_period'):
    processed_requirements['needs_rental_period_clarification'] = True
    processed_requirements['rental_period_clarification_message'] = clarification_msg
    # Search would be blocked here

# After: Generate recommendation but allow search to continue
if not processed_requirements.get('rental_period'):
    processed_requirements['needs_period_recommendation'] = True
    processed_requirements['period_recommendation_message'] = clarification_msg
    # Auto-select monthly as default for initial search
    processed_requirements['rental_period'] = 'month'
    # Mark that this was auto-selected
    processed_requirements['rental_period_auto_selected'] = True
```

**New Flags Added**:
- `needs_period_recommendation`: Boolean flag indicating period recommendation should be shown
- `period_recommendation_message`: User-friendly message suggesting period options
- `rental_period_auto_selected`: Boolean flag indicating period was auto-selected (not user-specified)

### 2. Step Handlers Update (`step_handlers.py`)

**File**: `backend/core/services/conversation/step_handlers.py`

**Change**: Modified the inquiry step handler to show recommendations alongside search results:

```python
# Before: Would only proceed if period was specified
if requirements.get('needs_rental_period_clarification'):
    return requirements['rental_period_clarification_message']

# After: Show recommendation AND search results
if requirements.get('needs_period_recommendation'):
    response_parts.append(f"{requirements.get('period_recommendation_message', '')}\n\n")
    
# Proceed with property search regardless
conversation.current_step = 'property_listings'
conversation.save()
search_result = self.property_search.proceed_to_property_search(conversation, requirements)

# Combine recommendation message with search results
if response_parts:
    return response_parts[0] + search_result
return search_result
```

## How It Works

### User Flow Without Period Specified

1. **User sends message**: "I need accommodation for 2 people near campus with wifi, budget is $200"
2. **System extracts requirements**: Heads=2, Budget=200, Amenities=[wifi], Location=campus, Period=None
3. **NLP Processor detects missing period**:
   - Generates recommendation message
   - Sets `rental_period = 'month'` as default
   - Sets `rental_period_auto_selected = True`
4. **Step Handler proceeds to search**:
   - Shows recommendation message
   - Executes property search with 'month' period
   - Displays search results with prices for all periods
5. **User sees**: Recommendation message + Property listings with daily/weekly/monthly prices

### User Flow With Period Specified

1. **User sends message**: "I need a place for the week, budget is $100/week"
2. **System extracts requirements**: Period='week' detected
3. **NLP Processor skips recommendation** (period already specified)
4. **Step Handler proceeds directly to search**:
   - No recommendation message shown
   - Searches using 'week' period
   - Filters properties by `price_per_week <= 100`
5. **User sees**: Property listings filtered for weekly rental, prices highlighted in weekly format

## Technical Details

### Period Extraction
The `RentalPeriodExtractor` class in `rental_period_extractor.py` identifies:
- **Daily**: Keywords like "daily", "per day", "/day", "nightly", "per night"
- **Weekly**: Keywords like "weekly", "per week", "/week"
- **Monthly**: Keywords like "monthly", "per month", "/month" (default if ambiguous)

### Property Search Filtering
The `PropertyMatcher` class (`property_matcher.py`) already supports period-based filtering:

```python
period = requirements.get('rental_period') or requirements.get('budget_unit')
if period == 'day':
    queryset = queryset.filter(price_per_day__lte=budget_max)
elif period == 'week':
    queryset = queryset.filter(price_per_week__lte=budget_max)
else:
    queryset = queryset.filter(price_per_month__lte=budget_max)
```

### Property Display
The `PropertySearchHandler` class displays all three prices:
- Monthly price
- Weekly price  
- Daily price

This allows users to see all rental options regardless of the search period.

## User Experience Improvements

### Before Implementation
- ❌ Users without explicit period mention get blocked
- ❌ Daily/weekly rentals cannot be searched
- ❌ Only monthly rentals are searchable
- ❌ User frustration due to blocking errors

### After Implementation
- ✅ Users see recommendations but get results immediately
- ✅ Daily rentals can be searched and displayed
- ✅ Weekly rentals can be searched and displayed
- ✅ Monthly rentals remain the default fallback
- ✅ All three price formats shown for maximum flexibility
- ✅ Smoother user experience with helpful guidance

## Examples

### Example 1: No Period Specified (Daily Properties)
**Input**: "I need a place for 1 night near campus"
**System Response**:
```
Please specify your preferred rental period:
• Daily rental (short stays)
• Weekly rental (medium stays)
• Monthly rental (long-term stays)

Example: 'Looking for accommodation for the whole semester for $100 a month'

PROPERTY LISTINGS 🏡
Properties Found: 3
Match confidence: (67%) 🟡

1️⃣ COZY APARTMENT
• Monthly price: $500.00
• Weekly price: $150.00
• Daily price: $25.00
• Distance: 0.5km from campus
• Amenities: wifi, security
```

### Example 2: Daily Period Specified (Daily Search)
**Input**: "Looking for daily rental for $30 per day"
**System Response**:
```
PROPERTY LISTINGS 🏡
Properties Found: 5
Match confidence: (85%) 🟢

1️⃣ STUDENT LODGE
• Monthly price: $600.00
• Weekly price: $180.00
• Daily price: $30.00
• Distance: 1.0km from campus
• Amenities: wifi, cleaning
```

### Example 3: Weekly Period Specified (Weekly Search)
**Input**: "Need accommodation for 3 weeks, budget is $200/week"
**System Response**:
```
PROPERTY LISTINGS 🏡
Properties Found: 4
Match confidence: (75%) 🟡

1️⃣ MODERN HOSTEL
• Monthly price: $750.00
• Weekly price: $200.00
• Daily price: $35.00
• Distance: 0.8km from campus
• Amenities: wifi, security, gym
```

## Testing

Run the test suite to verify functionality:

```bash
python manage.py test core.tests.test_period_recommendation
```

Test coverage includes:
- ✓ Period recommendation shown when period not specified
- ✓ No recommendation when period already specified
- ✓ Daily period extraction from messages
- ✓ Weekly period extraction from messages
- ✓ Monthly period extraction from messages
- ✓ Daily rental search execution
- ✓ Weekly rental search execution
- ✓ Monthly rental search execution

## Configuration

No additional configuration required. The feature uses existing infrastructure:
- `rental_period_extractor.py`: Period detection
- `property_matcher.py`: Period-based filtering
- `property_search.py`: Period-aware display

## Backward Compatibility

✅ All existing functionality is preserved:
- Monthly rentals continue to work as the default
- Existing searches with explicit periods work unchanged
- Property display format remains compatible
- All existing APIs and workflows remain functional

## Future Enhancements

Possible future improvements:
1. Machine learning to intelligently suggest period based on message context
2. Personalized period recommendations based on user history
3. Allow users to compare all three periods side-by-side
4. Advanced filtering by minimum/maximum stay duration
5. Seasonal pricing adjustments for different periods

# UX Writing Style Guide

This document outlines the UX writing guidelines for WhatsApp messages in the Jeff platform.

## Tone Rules

### Core Principles
- **Friendly**: Warm, approachable, not robotic
- **Simple English**: Clear, concise, avoid jargon
- **Student-Friendly**: Relatable to NUST students, but not childish
- **Local Context Aware**: References to Bulawayo, NUST, local areas

### Examples

**Good**:
> "Hi there! Welcome to Bulawayo Rooms Finder. I help you find safe, affordable rooms — especially near NUST 🎓."

**Bad**:
> "Greetings. This is the JEFF automated accommodation search system. Please input your accommodation requirements."

---

## Message Length Limits

### Rules
- **Maximum length**: 300 characters per message bubble
- **Maximum sentences**: 2 sentences per bubble
- **Split long messages**: Use `ux_formatter.split_long_message()` for content exceeding limits

### Examples

**Good** (under 300 chars):
> "Here are matching rooms I found 🔍
> 
> 📍 Riverside (3km from NUST)
> 💵 $55 / month
> 🏠 Single room, WiFi, Borehole
> 
> Reply VIEW 1 to unlock details."

**Bad** (too long):
> "Here are matching rooms I found. Property 1 is located in Riverside, 3km from NUST campus. It costs $55 per month. It's a single room with WiFi and borehole water. The property has parking available and is close to shopping centers. The landlord is responsive and the area is safe. Reply VIEW 1 to unlock details and see the full address and contact information."

---

## Emoji Usage Rules

### Guidelines
- **Limit**: 1-2 emojis per message maximum
- **Purpose**: Enhance clarity, not decoration
- **Consistency**: Use emoji mapping from `ux_formatter.EMOJI_MAP`

### Emoji Mapping

| Type | Emoji | Usage |
|------|-------|-------|
| Location | 📍 | Property locations, addresses |
| Money | 💵 | Prices, budgets, payments |
| Viewing | 📅 | Booking viewings, scheduling |
| Confirmation | ✔ | Confirmations, approvals |
| Alert | ⚠ | Warnings, important notices |
| Room | 🏠 | Properties, accommodation |
| WiFi | 📶 | Internet, connectivity |
| Safe | 🛡 | Safety information |
| Phone | 📱 | Contact information |
| Search | 🔍 | Searching, finding |
| Token | 💰 | Payment, tokens |
| Student | 🎓 | Student-related content |
| Help | ❓ | Help, assistance |
| Back | 🔙 | Go back, return |
| Save | ⭐ | Save for later |
| Yes | ✔ | Positive response |
| No | ❌ | Negative response |
| Cancel | 🙅 | Cancel, abort |

### Examples

**Good** (1-2 emojis):
> "📍 Riverside (3km from NUST)
> 💵 $55 / month"

**Bad** (too many emojis):
> "📍🏠💵📶🛡 Riverside (3km from NUST) 💵 $55 / month 🏠 Single room 📶 WiFi 🛡 Safe area"

---

## Error Message Templates

### Format
All error messages should be:
- Friendly and non-technical
- Actionable (tell user what to do next)
- Use UX formatter: `ux_formatter.format_error_message(error_type)`

### Error Types

| Error Type | Message |
|------------|---------|
| `invalid_input` | "Oops 😅 I didn't get that. Try choosing one of the options below." |
| `no_properties` | "Sorry, I couldn't find any rooms matching your requirements. Try adjusting your budget or location." |
| `payment_failed` | "Payment didn't go through. Please try again or contact support if the problem continues." |
| `token_expired` | "Your token has expired. Please buy a new token to continue searching." |
| `no_token` | "You need a token to view full property details. Would you like to buy one?" |
| `database_error` | "Try again shortly, we're fixing something." |
| `provider_timeout` | "The landlord hasn't responded yet. I'll notify you when they do." |

### Examples

**Good**:
> "Oops 😅 I didn't get that. Try choosing one of the options below."

**Bad**:
> "Error: Invalid input format. Expected format: option-{number}. Received: {user_input}"

---

## Quick Reply Formatting Standards

### Format
```
{Main message}

QUICK REPLIES:
• Option 1
• Option 2
• Option 3
```

### Guidelines
- Use bullet points (•) for quick replies
- Limit to 3-5 options maximum
- Use emojis sparingly (1 per option if needed)
- Keep option text short (under 20 characters)

### Examples

**Good**:
```
What would you like to do today?

QUICK REPLIES:
• 🔍 Search rooms
• 💰 Buy token
• 🎒 Student rooms near NUST
• 🏘 General Bulawayo rooms
• ❓ Help
```

**Bad**:
```
What would you like to do today? Here are your options: You can search for rooms, buy a token, look for student rooms near NUST, search for general Bulawayo rooms, or get help. Just reply with one of these options.
```

---

## Memory/Reference Usage Guidelines

### When to Use
- Reference previous choices when user returns after inactivity
- Gently remind user of their preferences
- Use stored context from `conversation.context_data`

### Format
- Start with acknowledgment: "You were checking..."
- Reference specific details: location, budget
- Offer continuation: "Would you like to continue?"

### Examples

**Good**:
> "👋 Welcome back!
> 
> You were checking rooms near Riverside.
> 
> Would you like to continue?"

**Bad**:
> "Hi again. Continue?"

---

## Property Preview Formatting

### Structure
1. **Key info first**: Location and distance
2. **Short description**: Price and room type
3. **Clear next action**: "Reply VIEW {index} to unlock details"

### Example
```
📍 Riverside (3km from NUST)

💵 $55 / month

🏠 Single room, WiFi, Borehole

Reply VIEW 1 to unlock details.
```

---

## Full Property Details Formatting

### Structure
1. Property name
2. Price
3. Location and distance
4. Address
5. Amenities (top 5)
6. Availability
7. Match score (if available)
8. Match reasons (if available)
9. CTA: "Would you like me to contact the landlord for you?"

### Example
```
🏠 Single Room — Riverside

💵 $55 / month

📍 3.2km from NUST gate
123 Main Street, Riverside

📶 WiFi, Parking, Borehole, Security

Available rooms: 2/5

Match score: 42/50
Why it matches: Budget fit | Close to campus

Would you like me to contact the landlord for you?
```

---

## Payment Instructions Formatting

### Structure
1. Explain why token is needed
2. Ask if user wants to buy
3. Mention supported payment methods
4. Quick reply options

### Example
```
To view full details + contact the landlord, you'll need 1 view token.

Would you like to buy a token now?

(Paynow — EcoCash, USD, ZWL supported)

QUICK REPLIES:
• ✔ Buy token
• ❌ Not now
```

---

## Booking Confirmation Formatting

### Structure
1. Confirmation message
2. Booking number
3. Next steps (viewing booking options)

### Example
```
✔ The landlord confirmed availability!

Would you like their phone number or to schedule a viewing?

QUICK REPLIES:
• 📱 Phone number
• 📅 Book viewing
• 🙅 Cancel
```

---

## Help Message Formatting

### Structure
1. Help menu with topics
2. Quick reply options
3. Keep under 300 characters

### Example
```
Here's what I can help with ❓

QUICK REPLIES:
• 💰 How tokens work
• Refund policy
• 🔍 Searching tips
• 🛡 Safety reminders
• Contact support
```

---

## Clarity Rules

### Do's
- ✅ Use "you" instead of "u"
- ✅ Use full words, not abbreviations
- ✅ Break long information into multiple messages
- ✅ Use bullet points for lists
- ✅ Provide clear next actions

### Don'ts
- ❌ Don't use "u", "ur", "2" (use "you", "your", "to")
- ❌ Don't use technical jargon
- ❌ Don't create long paragraphs
- ❌ Don't use excessive emojis
- ❌ Don't leave user without clear next step

---

## Message Splitting

When messages exceed 300 characters, split into multiple bubbles:

**Before** (too long):
> "Here are matching rooms I found. Property 1 is located in Riverside, 3km from NUST campus. It costs $55 per month. It's a single room with WiFi and borehole water. The property has parking available and is close to shopping centers. Reply VIEW 1 to unlock details."

**After** (split):
> "Here are matching rooms I found 🔍
> 
> 📍 Riverside (3km from NUST)
> 💵 $55 / month
> 🏠 Single room, WiFi, Borehole
> 
> Reply VIEW 1 to unlock details."

---

## Implementation

All formatting should use `backend/core/services/conversation/ux_formatter.py`:

- `format_property_preview()` - Property previews
- `format_full_property_details()` - Full property details
- `format_error_message()` - Error messages
- `format_with_quick_replies()` - Quick reply formatting
- `split_long_message()` - Message splitting
- `format_with_memory()` - Memory references

---

## Testing Checklist

- [ ] All messages under 300 characters (or split)
- [ ] Maximum 2 sentences per bubble
- [ ] 1-2 emojis per message maximum
- [ ] Clear next actions provided
- [ ] Friendly, non-technical language
- [ ] Quick replies formatted correctly
- [ ] Error messages use templates
- [ ] Memory references are gentle and helpful


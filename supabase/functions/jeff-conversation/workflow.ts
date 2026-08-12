export type JeffStep = 'inquiry' | 'property_listings' | 'property_selected' | 'collecting_name' | 'booking_request' | 'awaiting_provider' | 'awaiting_payment' | 'confirmed'

export function classifyIntent(message: string): 'greeting' | 'help' | 'restart' | 'payment' | 'property' | 'unknown' {
  const m = message.trim().toLowerCase()
  if (/^(hi|hello|hey|good morning|good afternoon|good evening)\b/.test(m)) return 'greeting'
  if (/\b(help|how do i|what can you do)\b/.test(m)) return 'help'
  if (/\b(restart|start over|reset)\b/.test(m)) return 'restart'
  if (/\b(pay|payment|token|purchase)\b/.test(m)) return 'payment'
  if (/\b(room|rooms|accommodation|house|hostel|lodge|apartment|rent|stay|campus)\b/.test(m)) return 'property'
  return 'unknown'
}

export function parseRequirements(message: string) {
  const m = message.toLowerCase()
  const heads = Number(m.match(/\b([1-4])\s*(?:head|heads|person|people|student|students)\b/)?.[1] ?? '') || null
  const budgetMatch = m.match(/(?:\$|usd\s*)(\d+(?:\.\d+)?)/i) ?? m.match(/\b(?:under|below|budget(?:\s+of)?)\s*(?:\$|usd\s*)?(\d+(?:\.\d+)?)/i)
  const budget_max = budgetMatch ? Number(budgetMatch[1]) : null
  const rental_period = /\bday|daily\b/.test(m) ? 'day' : /\bweek|weekly\b/.test(m) ? 'week' : 'month'
  const distance_preference = /\bnear|close|walking distance\b/.test(m) ? 'near' : /\bfar|further\b/.test(m) ? 'far' : null
  const amenities = ['wifi', 'parking', 'kitchen', 'security', 'dstv'].filter((a) => m.includes(a))
  return { heads, budget_max, rental_period, amenities, distance_preference }
}

export function renderProperties(rows: any[]) {
  if (!rows.length) return 'I could not find a suitable available property with those requirements. You can try a higher budget, different amenities, or a wider area.'
  return rows.map((p, i) => {
    const price = p.price_per_month ?? p.price_per_week ?? p.price_per_day
    const reasons = Array.isArray(p.match_reasons) && p.match_reasons.length ? ` — ${p.match_reasons.slice(0, 3).join(', ')}` : ''
    return `${i + 1}. ${p.name} — ${price ?? 'price on request'}${reasons}`
  }).join('\n') + '\n\nReply with a number to select a property.'
}

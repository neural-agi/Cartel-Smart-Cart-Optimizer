# Decision: Homepage Wireframe v1 (Frozen)

## Desktop Layout

```
┌────────────────────────────────────────────────────────────┐
│ Navbar                                                     │
│ Logo | Search | Notifications | Profile                    │
└────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────┐
│ Search Bar                                                 │
│ "Search groceries..."                                      │
└────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────┐
│ Frequently Bought                                          │
│ [Milk] [Bread] [Butter] [Rice] [+ More]                    │
└────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────┐
│ Categories                                                 │
│ Dairy | Fruits | Vegetables | Snacks | Drinks | Personal   │
└────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────┐
│ Products                                                   │
│ ┌──────────────┐ ┌──────────────┐                          │
│ │ ProductCard  │ │ ProductCard  │                          │
│ └──────────────┘ └──────────────┘                          │
│ ┌──────────────┐ ┌──────────────┐                          │
│ │ ProductCard  │ │ ProductCard  │                          │
│ └──────────────┘ └──────────────┘                          │
└────────────────────────────────────────────────────────────┘

                          ▼

                 Floating Cart Button

                 🛒 8 Items • ₹642
```

## Mobile Layout

```
Navbar
  ↓
Search
  ↓
Frequently Bought
  ↓
Categories
  ↓
Products (Stacked)
  ↓
Floating Cart
```

---

## Rules (Locked In, Don't Fuck With This)

- **Search is always visible** — no hiding it, king. Users need to find shit fast.
- **Frequently Bought appears only if the user has purchase history** — don't show empty state drama.
- **Categories remain above the product grid** — this is the law.
- **Product cards are the primary browsing method** — they're the stars, everything else is supporting cast.
- **Floating Cart is always accessible after at least one item is added** — accessibility matters, periodt.
- **No dashboard widgets** — we're not making a fucking analytics dashboard.
- **No analytics on the homepage** — stop trying to be Pinterest, bro.
- **No optimization results on the homepage** — keep it simple, stupid. Well, *you* keep it simple.
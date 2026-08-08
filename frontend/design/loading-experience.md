# Cartel Loading Experience

**Status:** Frozen v1  
**Scope:** Frontend UX / Motion / Transition State

## Purpose

The loading experience is a deliberate part of the Cartel product, not a generic spinner.

It exists to make the optimization step feel:
- intentional,
- informative,
- fast,
- and visually distinctive.

The loading state should reinforce that Cartel is calculating the cheapest way to buy a full grocery cart across multiple platforms.

## User Flow

```text
Optimize Cart
    ↓
Loading Overlay Appears
    ↓
Animated Cart Moves
    ↓
Platforms Are Scanned
    ↓
Savings Are Calculated
    ↓
Random Grocery Fact Appears
    ↓
Optimization Completes
    ↓
Results Page
```

## Timing

The loading experience should remain short enough to feel responsive and long enough to feel meaningful.

Target timing:

- **0.0s** - overlay fades in
- **0.3s** - cart animation begins
- **0.8s** - platform scanning starts
- **1.2s** - grocery fact changes
- **1.8s** - savings counter animates
- **2.4s** - optimization completes
- **2.7s** - transition to results page

The exact duration may vary slightly depending on backend response time, but the loading UI should be designed around a roughly 2-3 second experience in the common case.

## Visual Structure

The loading screen should present a focused, centered layout:

- Dark translucent overlay
- Central loading card
- Animated grocery cart
- Progress indicator
- Grocery fact text
- Savings counter or rupee animation
- Optional subtle platform scanning cues

The loading view should feel polished but not busy.

## Motion Rules

- Motion should be smooth and purposeful.
- Use subtle easing rather than abrupt movement.
- The cart animation should feel continuous.
- Savings animation should feel celebratory without becoming distracting.
- The transition to the results page should feel immediate once optimization completes.

## Messaging

The loading text should communicate progress clearly.

Examples:

- Comparing Blinkit...
- Comparing Zepto...
- Comparing Instamart...
- Applying memberships...
- Finding the cheapest combination...
- Calculating savings...

The wording should avoid sounding like a generic technical spinner.

## Random Grocery Facts

The loading state may surface short grocery-related facts while optimization is in progress.

These facts should be:
- short,
- readable at a glance,
- relevant to grocery shopping,
- and not misleading.

Examples of fact types:
- grocery spending patterns
- delivery fee behavior
- price differences across platforms
- savings from cart-level comparison
- shopping frequency insights

The fact should change often enough to feel dynamic, but not so fast that it becomes unreadable.

## Savings Display

If a savings amount is known during the loading phase, it may be shown as a live or animated rupee counter.

The savings display should:
- feel quantifiable,
- build anticipation,
- and connect the loading state to the final result.

Examples:
- ₹58 saved
- Saving more than the baseline cart
- Comparing against the highest-cost platform

## Accessibility

The loading experience must remain understandable without relying only on motion.

It should include:
- readable text,
- sufficient color contrast,
- clear progress messaging,
- and a non-motion fallback where needed.

## Implementation Boundaries

The loading experience is a frontend transition state only.

It must not:
- compute optimization results,
- determine product allocation,
- decide platform selection,
- or contain business logic.

All optimization logic belongs in the backend.

## Acceptance Criteria

The loading experience is considered ready when:

- it appears during optimization,
- it communicates that work is in progress,
- it feels intentional rather than empty,
- it transitions cleanly to the results page,
- and it matches the Cartel visual language.

## Frozen Decisions

- Loading duration target: approximately 2-3 seconds in the common case
- Visual tone: dark, polished, confident, lightweight
- Core elements: animated cart, progress messaging, fact text, savings cue
- Scope: frontend-only transition state

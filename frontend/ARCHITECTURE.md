# Frontend Architecture

## Dependency Flow

app
↓
features
↓
components
↓
store
↓
services
↓
backend

## Rules

- Components must never perform API calls.
- Business logic belongs in features.
- Services are the only layer allowed to communicate with the backend.
- Zustand stores manage client-side state only.
- Shared UI belongs in components/.
- Feature-specific composition belongs in features/.
- Backend owns all optimization, pricing, and business logic.
# VOOGLII Frontend Foundation

This directory contains the independent web frontend foundation for the VOOGLII Platform. It is intentionally isolated from the current Python backend and Telegram runtime so the web product can evolve without introducing coupling at the foundation stage.

## Stack

- Next.js with App Router
- React
- TypeScript in strict mode
- Tailwind CSS
- ESLint
- Prettier

## Run

1. Install dependencies:

```bash
npm install
```

2. Start local development:

```bash
npm run dev
```

3. Quality checks:

```bash
npm run lint
npm run type-check
npm run build
```

## Directory Structure

```text
frontend/
  app/                  # Route entries and page composition
  components/           # Reserved for future route-level composition components
  layouts/              # Global layout shells
  features/             # Feature-scoped screens and assemblies
  widgets/              # Reusable higher-level product blocks
  shared/               # Shared UI, mock data, libs, and tokens
  styles/               # Global styles and theme rules
  hooks/                # Shared React hooks
  services/             # Data access adapters and mock services
  types/                # Shared TypeScript contracts
  utils/                # Pure helpers
  assets/               # Future local assets
  public/               # Public web assets
```

## Architecture Principles

- The frontend is backend-independent at this stage.
- All screens read from a mock data layer, not from live APIs.
- Design tokens define the visual language first.
- Screens are composed from shared components and workspace widgets.
- Business logic should remain outside presentational components.
- Future backend integration should happen through `services/` and stable typed contracts.

## Naming Conventions

- Use `PascalCase` for React components.
- Use `kebab-case` for route directories.
- Use `camelCase` for variables, services, and helpers.
- Keep route files thin and move composition into `features/` or `widgets/`.
- Put shared primitives in `shared/components/`.

## Component Rules

- Every UI component should consume the shared design system.
- New components should remain mock-compatible until backend contracts are approved.
- Reusable components should avoid embedding workspace-specific assumptions.
- Variant-driven styling is preferred over one-off ad hoc classes.
- AI-facing components should preserve space for confidence, explanation, and source attribution.

## Current Scope

This sprint includes:

- global platform shell;
- sidebar and header navigation;
- responsive workspace layout;
- shared component library;
- mock data layer;
- Command Center skeleton;
- placeholder routes for all primary workspaces.

This sprint does not include:

- Python backend integration;
- real APIs or database calls;
- Telegram integration;
- live AI or finance engines;
- production authentication flows.

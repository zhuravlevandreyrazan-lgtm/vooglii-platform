# Financial Core 2.0

## Purpose

Financial Core 2.0 centralizes all customer-facing financial calculations into one object:

- `UnifiedFinancialSnapshot`

Every financial screen must render from this object instead of calculating its own totals.

## Pipeline

The intended pipeline is:

1. Raw DB rows
2. Period normalization
3. User filtering
4. Source aggregation
5. Cost matching
6. Expense classification
7. Reconciliation
8. Confidence calculation
9. Unified snapshot
10. Customer renderers

## Snapshot Responsibilities

The snapshot owns:

- all money totals
- all profit totals
- all ratios
- finance confidence
- customer-safe warnings
- explainability via `source_map`

## Confidence Layer

- `HIGH` -> final values may be shown
- `MEDIUM` -> show preliminary operating estimate only
- `LOW` / `UNKNOWN` -> hide final profit and show safe waiting text

## Reconciliation Rules

- positive residual -> `unknown_wb_expenses`
- negative residual -> `reconciliation_delta`
- `reconciliation_delta` is not an expense
- pending WB-side components must not look final while finance is waiting

## Cost Matching

Cost should be derived in the core, not in renderers.

Matching priority currently documented for RC4:

- `nm_id`
- `supplierArticle`
- `barcode`
- `techSize`
- fallback product naming

If costs exist but period sales are not matched yet, customer UX should explain that the cost dictionary is filled but period calculation is still waiting.

## Release Gate

The release process must verify:

- one snapshot drives every main financial screen
- source map is filled for key fields
- consistency tests pass
- period regression tests pass
- diagnose scripts explain the numbers for May, June, and July 2026

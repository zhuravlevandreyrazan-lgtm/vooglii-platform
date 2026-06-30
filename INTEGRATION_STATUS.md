# Integration Status

| Endpoint | Frontend module | Backend status | Frontend mode | Fallback remaining | Performance status | Next action |
| --- | --- | --- | --- | --- | --- | --- |
| `/api/command-center` | Command Center | live/cache aggregator | degraded-safe | yes | fast after cache warm-up | keep executive fast mode on cached workspace snapshots |
| `/api/executive` | Executive | live/cache alias | degraded-safe | yes | fast after cache warm-up | preserve alias and monitor cache quality |
| `/api/business` | Business | live | strict live | fallback only on error | ok | none |
| `/api/finance` | Finance | live | strict live | fallback only on error | ok | none |
| `/api/advertising` | Advertising | live | strict live | fallback only on error | ok | none |
| `/api/products` | Products | live | strict live | fallback only on error | ok | none |
| `/api/inventory` | Inventory | live | strict live | fallback only on error | ok | none |
| `/api/advisor` | Advisor | live/cache fast mode | degraded-safe | yes | fast | improve recommendation depth from cached sources if needed |
| `/api/reports` | Reports | live/cache fast mode | degraded-safe | yes | fast | keep catalog/export metadata lightweight |
| `/api/system` | System | live fast diagnostics | degraded-safe | no frontend fallback currently required | fast | continue exposing runtime dashboard fields |
| `/api/status` | Shared diagnostics | live fast diagnostics | infrastructure only | n/a | ok | use as runtime dashboard endpoint |
| `/api/version` | Shared diagnostics | live | infrastructure only | n/a | ok | none |
| `/api/health` | Shared diagnostics | live | infrastructure only | n/a | ok | none |

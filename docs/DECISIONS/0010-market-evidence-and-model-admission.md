# Decision 0010 — Market evidence and next modeled opportunity

Status: Implemented decision
Date: 2026-09-11

## Decision

Add the existing CoinGecko connector to the discovery worker as a market-quote provider. Persist quote provenance, timestamps, freshness, and an explicit “quote only” explanation. Do not use a token spot quote as earnings, utilization, or ROI evidence.

Keep `akash-provider` as the highest-priority research candidate, but do not add a new financial strategy yet. The current evidence confirms the provider mechanism and exposes the variables needed by a future model, but it does not establish an individual provider's utilization, recurring hardware/energy cost, lease fill, or realizable reward flow.

## Evidence review

- Akash documents provider earnings as dependent on compute leases, pricing, capacity, uptime, demand, hardware, and operating costs. The official calculator also requires utilization and resource-price inputs.
- Aethir documents a task-weighted daily reward formula and uptime conditions, but individual task/license data and the current acquisition basis are not sufficient for a reproducible strategy here.
- Hivemapper documents reward categories and quality/region dependence, but not a stable individual mapping rate that can be valued as a strategy.
- Grass has a live market quote, but the catalog opportunity remains points/reward-route limited; a quote does not create a lawful realizable earnings route.

## Admission outcome

No new `MODELED` opportunity is admitted in this pass. This is an intentional evidence gate, not a provider failure. Akash remains eligible for guide content and research queue priority. Promotion requires a reproducible observation set for entry/operating costs, contribution or utilization, reward quantity, and executable/realizable exit value.

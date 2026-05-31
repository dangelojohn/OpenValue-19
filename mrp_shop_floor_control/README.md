# MRP Shop Floor Control (Odoo 19.0 CE)

Forward/backward manufacturing-order scheduling, work-order sequencing with
milestones, work-center capacity load analysis, and shop-floor work-order
start/confirmation wizards.

This is a **rebuild and refactor of the original Odoo 16 module for Odoo
19.0 Community Edition**. The functional behaviour of the original was kept,
the Odoo 16 → 19 API breakages were fixed, and the bugs found in review were
corrected.

## Features

- **Pivot planning** on the Manufacturing Order: forward (from a start date)
  or backward (from an end date) using the warehouse working calendar, the
  BoM `produce_delay` and the BoM security lead time (`days_to_prepare_mo`).
- **Floating times** per manufacturing warehouse (release / before / after
  production), seeded automatically on install.
- **Work-order scheduling engine** with parallel and sequential operations,
  **milestones**, and a **mid-point (re)scheduling** wizard.
- **Work-center capacity load** model + pivot/graph reporting and an
  interactive **Plotly capacity chart** on the work center form.
- **Capacity check** wizard (load vs. available capacity per week).
- **Start / Confirmation** wizards for a classic time-and-quantity shop-floor
  declaration flow.

## Requirements

- Odoo **19.0** Community Edition (`mrp` installed).
- No external Python dependency. Plotly is bundled client-side
  (`static/lib/plotly/plotly.min.js`) and the chart is rendered by an OWL
  field widget — the old server-side `plotly` Python package is no longer
  needed.

## Install

Copy the `mrp_shop_floor_control` folder into your Odoo addons path, update
the apps list, and install. The post-init hook creates a Floating Times
record for every manufacturing warehouse.

## Key Odoo 16 → 19 changes applied

| Area | Odoo 16 | Odoo 19 (this module) |
|------|---------|------------------------|
| MO / WO planned dates | `date_planned_start` / `date_planned_finished` | `date_start` / `date_finished` (module keeps its own `*_wo` layer) |
| WO finished lot | `finished_lot_id` (m2o) | `finished_lot_ids` (m2m, via `Command`) |
| Produce / lead time | `product.produce_delay`, `company.manufacturing_lead` | `bom.produce_delay`, `bom.days_to_prepare_mo` |
| Field `states=` | used | removed (view-level `readonly=`/`invisible=`) |
| View `attrs`/`states` | used | replaced by attribute expressions |
| `<tree>` | used | `<list>` |
| `post_init_hook(cr, registry)` | old signature | `post_init_hook(env)` |
| `read_group` | used | `_read_group(domain, groupby, aggregates)` |
| Backorder hook | `_generate_backorder_productions` override | dropped (gone in v19; durations recomputed via `@api.depends`) |
| Plotly chart | `web.AbstractField` JS + server-side `plotly.offline` | OWL field widget + client-side `Plotly.react` on JSON |

## Bug fixes folded in from the code review

- Capacity load is now a **dedicated `mrp.workcenter.load` model** instead of
  inheriting (and polluting) the core `mrp.workcenter.capacity` model.
- No `create()`/`write()` inside `@api.constrains`; load is (re)built from the
  scheduling methods, and validation constraints only validate.
- No `write()` inside compute methods; actual dates are assigned directly.
- Per-record accumulators in all aggregate computes (no cross-record bleed).
- `_check_unique` (work center name/code) loops over the recordset and is
  company-scoped.
- Consistent **ISO-8601 week** keys (`%G-%V`) for capacity bucketing.
- `action_generate_serial` works (its `_reopen_form` helper was restored).
- Confirmation `date_end` compute has no side effects.
- Floating-times warehouse domain uses a real boolean.
- Capacity check is **button/method driven**, not an onchange with side
  effects.
- Removed debug `print()`s and import-time `_()` field labels.

## Parallel operations & milestones

Operations that should run in parallel must share the same routing-operation
**sequence**. Because Odoo 19 forces unique work-order `sequence` values
(`_resequence_workorders`), this module uses its own stored **`sfc_sequence`**
(derived from the routing operation) for all milestone / parallel / scheduling
logic, so parallel grouping survives standard planning.

## Verification status

Python byte-compiles, and all XML/CSV are well-formed and were authored
against the Odoo 19.0 `mrp` source (view IDs, anchors and model APIs verified
against branch `19.0`). **Install and runtime testing on a live Odoo 19.0
database is still recommended** before production use — in particular the
work-order start/finish gating and the embedded work-order list interactions,
which depend on the installed manufacturing apps (e.g. `mrp_workorder`,
`mrp_subcontracting`).

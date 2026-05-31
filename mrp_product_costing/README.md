# MRP Product Costing (Odoo 19.0 CE)

Standard / planned / actual manufacturing cost analysis, material / direct /
overhead **variance postings**, and an **economical closure** that books the
industrial cost of each manufacturing order. Depends on `mrp_shop_floor_control`
(the v19 rebuild).

This is a **rebuild and refactor of the Odoo 16 module for Odoo 19.0 CE**,
implementing the v16→v19 migration checklist *plus* the forced breakers the
checklist did not list. Authored against the Odoo 19.0 source; Python
byte-compiles and all XML parses, but **install + posting tests on a live v19
database are still required** (see Verification).

## Forced v19 changes applied

| # | Change | Where |
|---|--------|-------|
| 1 | **`product.type == 'product'` is gone** (now `consu`/`service` + `is_storable`). Material/by-product variance filters → `is_storable` | `mrp_economical_closure._material_costs_variance_postings` |
| 2 | **`group_operator=` → `aggregator=`** (renamed in v18) on all 16 avg fields | `mrp_production.py`, `mrp_economical_closure.py` |
| 3 | **Stock valuation hooks rebuilt.** `_prepare_account_move_vals` / `_prepare_account_move_line` / `_generate_analytic_lines_data` no longer exist → now override `_create_account_move` (MO link on header) and `_prepare_analytic_line_values` (MO + category on analytic) | `stock_move.py` |
| 4 | **`mrp.production.analytic_account_id` no longer exists.** WO direct-cost analytic now uses the work-center analytic account via `analytic_distribution` | `mrp_workorder.py` |
| 5 | **`valuation_in_account_id` / `valuation_out_account_id` removed** from `stock.location` → single **`valuation_account_id`** | closure + workorder postings |
| 6 | **`mo_analytic_account_line_id` → `mo_analytic_account_line_ids`** (m2m) and `move.analytic_account_line_id` → `analytic_account_line_ids`; `button_mark_done` rewritten, gated on `done` | `mrp_economical_closure.button_mark_done` |
| 7 | **`product._compute_bom_price` is gone.** Custom operation costing re-homed onto `mrp.routing.workcenter._compute_cost` (feeds the v19 BoM Structure report); full rollup preserved as `product._sfc_compute_bom_price` | `mrp_routing_workcenter.py`, `product.py` |
| 8 | **`_generate_backorder_productions` → `_split_productions`** (planned-cost snapshot re-applied on split) | `mrp_production.py` |
| 9 | **Analytic hooks plural/private**: override `_prepare_analytic_lines` (plural); `account.analytic.line.category` selection extended with `manufacturing_order` (base only ships `other`); analytic account written via `plan_id._column_name()` | `account_move.py`, closure |
| 10 | Views: `<tree>`→`<list>`, `attrs`/`states` → `invisible`/`required`/`readonly` expressions, `column_invisible`, list `view_mode` | all view files |

## Bug fixes (from the review checklist, all confirmed in source)

- **Overhead double-count** — per-work-order amounts are now reset and posted
  per work order; record totals accumulate separately. (`_wc_ovh_analytic_postings`)
- **Unposted draft entries** — direct-cost entries now `action_post()` once per
  work order regardless of which cost components exist. (`mrp_workorder._direct_cost_postings`)
- **Cross-record accumulator leaks** — every accumulator resets inside the
  per-record loop, in all cost computes and all postings.
- **Computed fields unassigned on some paths** — planned costs are now a
  **snapshot** written at `action_confirm` / `_split_productions` (plain stored
  fields), eliminating the `state`-only narrow dependency and the ORM-strictness
  "did not assign" risk; actual by-product amount assigns on all paths.
- **Non-idempotent closure** — `button_closure` raises if already closed, runs a
  **configuration pre-check** (journal, variance accounts, production valuation
  account) to fail before any posting, and sets `closure_state = True` (boolean,
  not the `'True'` string).
- **Division-by-zero** — guards on `time_efficiency`, `capacity`,
  `product_uom_qty`, `bom.product_qty`; `_get_qty_produced` floors at 1.0.
- **Compute-method name mismatches** — removed (planned costs no longer a
  compute; `std_byproduct_amount` computed by `_compute_standard_costs`; the
  phantom `calculate_standard_by_product_amount` reference is gone).
- **Missing `manufacture_order_id`** on a variance header — structurally fixed:
  the three variance methods share one `_post_variance_entry` helper that always
  stamps the MO.
- Cleanups: `calculate_*` computes renamed to `_compute_*`; `default="0.0"` →
  `0.0`; journal/ref strings wrapped in `_()`; dead `ReportBomStructure` block
  removed (re-homed per #7).

## Design note (unchanged behaviour — confirm intent)

In the BoM standard-cost rollup, fixed setup/teardown is charged per unit
(`costfixed * product_qty` then `/ product_qty`) rather than amortised across
the batch — preserved as-is from the original. Confirm this matches your
standard-cost definition.

## Two items to confirm live on the stack

- **#7 BoM cost**: the custom operation cost is injected via
  `mrp.routing.workcenter._compute_cost` and surfaces in the **BoM Structure
  report**. v19 has no product-level "compute standard price from BoM" button;
  if you relied on that flow, wire `product._sfc_compute_bom_price` to your cost
  update trigger.
- **#6 `button_mark_done` analytic cleanup**: it unlinks the native valuation /
  work-order analytic lines so this module's standard-costing analytic is
  authoritative. Confirm this is still the desired interaction with v19's native
  `mrp_account` analytic posting.

## Verification (do these first on the stack)

1. **MO back-reference (the silent one)** — after a closure, filter
   `account.analytic.line` on `manufacture_order_id` and on `category =
   manufacturing_order`. Empty ⇒ an analytic hook didn't bind. First acceptance test.
2. **Material variance ≠ 0** — confirm the `is_storable` filter actually selects
   storable components (this was silently zero under the old `type == 'product'`).
3. **Idempotency** — `button_closure` twice ⇒ second raises, no duplicate entries.
4. **Posting completeness** — a WO with variable but no fixed cost ⇒ a *posted*
   entry.
5. **Overhead correctness** — MO with ≥2 WOs ⇒ posted overhead equals
   `ovh_var_direct_cost + ovh_fixed_direct_cost`, no double-count.
6. **Config guard** — closing with a missing variance account raises a clean
   `UserError` before any move is created.
7. **GL balance** — every generated `account.move` is balanced and posted.

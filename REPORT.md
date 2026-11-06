# Report

Status: geometry, pricing, lead time, API and worker work. The complexity score is not done, and the
pricing is fitted to a single data point (see Pricing formula).

## Parsing the CAD file

- OpenCascade through `OCP`, the Python binding to the B-rep kernel CAD tools use. A B-rep describes
  a part as exact surfaces, edges and faces, not a mesh.
- `geometry/loader.py` reads the `.step`/`.stp` file with `STEPControl_Reader` and collects every solid.
  The kernel converts lengths to mm; the original unit (for example inch) is kept as a label.
- Validity uses `BRepCheck_Analyzer`, which catches open shells and self-intersections. Failures raise
  `GeometryError` with a stable code. Files with several solids are merged, with a warning.
- The CLI and the API worker run the same code.

## Calculating geometry

- Bounding box: tight axis-aligned box, sides sorted length >= width >= height, in mm.
- Volume (cm3) and surface area (cm2): exact kernel mass and surface properties.
- Stock volume: bounding box grown by 3 mm per side, what a shop would cut from bar or plate.
- Face and edge counts: unique faces and edges. SA:V ratio and material removal ratio (`1 - part / stock`).
- Sample gear: 23.37 x 22.56 x 12.32 mm and 1.95 cm3, matching the competitor's measurements.

## Detecting complexity

- **Holes:** cylinder faces are grouped by shared axis and radius (CAD often splits one hole in two).
  A group is a hole if a probe point 0.01 mm outside the wall is inside the solid (this separates holes
  from bosses) and its arcs cover at least 270 degrees (this drops fillets and slot ends). Coaxial
  counterbores count as one. Limit: two blind holes drilled from opposite sides on one axis merge.
- **Setups** (clampings on a 3-axis machine): the main axis is the thinnest direction. Each side of it
  with a flat face pointing along it counts as one, plus one per other axis with hole openings; at least 1.
  Angled faces and holes are ignored.
- **Thin walls:** a pair of roughly parallel faces closer than 3 mm, found by rays cast inward from
  sample points on each face. Pairs sharing a face count once, and wedge tips (gear teeth) are ignored.
  Gear: 1; bracket: 0. The count can vary with sampling density (the gear is 1 at most densities).
- **Complexity score: not implemented** (`null`). It is not used in the price.

## Pricing formula

Constants are in `pricing/config.py`; `price()` is pure and rounds to cents only at the end.

```
price_per_unit = material_per_unit + machine_per_unit + setup_per_unit
price_order    = price_per_unit x quantity
```

**Material** (6061: 2.7 g/cm3, $5.00/kg)
```
stock_volume_cm3  = (length + 6) x (width + 6) x (height + 6) / 1000     # 3 mm per side
stock_mass_kg     = stock_volume_cm3 x 2.7 / 1000
material_order    = max(stock_mass_kg x 5.00 x quantity, 10.00)          # $10 minimum per order
material_per_unit = material_order / quantity
```

**Machine time** (per part, $100/hour)
```
removed_volume_cm3 = stock_volume_cm3 - part_volume_cm3
mrr                = 50 - (50 - 20) x min(thin_walls, 8) / 8             # cm3 per minute
cycle_min          = removed_volume_cm3 / mrr  +  holes x 2.0  +  edges x 0.05
machine_per_unit   = cycle_min / 60 x 100
```

**Setup** (one-time per order)
```
setup_hours    = (0.10 + 0.19 x log2(faces)) + 0.10 x setups     # programming + fixturing
setup_per_unit = setup_hours x 100 / quantity
```

| Constant | Value | Basis |
|---|---|---|
| Density, price, machine rate | 2.7 g/cm3, $5.00/kg, $100/h | Given in the challenge |
| Stock allowance, minimum material | 3 mm per side, $10 per order | Assumption (minimum stock purchase, saw cuts) |
| MRR (material removal rate) | 50 cm3/min, down to 20 at 8 thin walls | Assumption, not measured |
| Minutes per hole | 2.0 | Assumption: flat, ignores depth |
| Minutes per edge | 0.05 (3 s) | Assumption: the machine slows where the tool path turns |
| Programming base, fixturing per setup | 0.10 h, 0.10 h | Assumption |
| Programming per log2(face) | 0.19 h | **Fitted** to the gear quote |

**Reasoning**
- Stock volume, not part volume: a shop buys and cuts raw stock, so removed material is paid for.
- Setup is one-time and divided by quantity. Nothing else changes with quantity, so the unit price
  falls with volume while the order total rises. No discount tiers (they would double count).
- Loading and re-clamping are inside the fixturing hours, so there is no handling term.
- Thin walls flex under the cutter, so the shop takes lighter cuts and the MRR drops.
- The edge count includes CAD seam lines on cylinders, so it overstates direction changes.
- Not priced: finishing (parts are as machined, standard tolerance), the complexity score, SA:V.

**Worked example: sample gear, quantity 1**
```
material = $10.00        (0.0415 kg of stock is $0.21, below the minimum)
mrr      = 50 - 30 x 1/8 = 46.25;  cycle = 13.41/46.25 + 1 x 2 + 284 x 0.05 = 16.49 min
machine  = 16.49 / 60 x 100 = $27.48
setup    = (0.10 + 0.19 x log2(99)) + 2 x 0.10 = 1.56 h = $155.96
price    = 10.00 + 27.48 + 155.96 = $193.44
```

**Calibration.** Competitors quote the gear at about $190-196 at quantity 1. The 0.19 h per log2(face)
(was 0.08) puts it in that band: one parameter fitted to one data point, so quantity 1 is a fit, not a
check. There are no competitor numbers for quantity 10 or 100, so the split between setup and cutting
time is unverified. The bracket is about $168 at quantity 1. `pricing_version` is `v2-draft`.

| Qty | Per unit | Order |
|---|---|---|
| 1 | $193.44 | $193.44 |
| 10 | $44.08 | $440.79 |
| 100 | $29.25 | $2,925.04 |

## Lead time formula

- `lead time = 5 + ceil(total machine hours / 8) + complexity buffer`, in business days, where
  total machine hours = setup hours + cycle hours x quantity.
- The 5-day minimum covers queue, material, QA and shipping prep, between the competitor's Standard
  (4 days) and Economy (7 days). The buffer is 0 until the complexity score exists.
- Sample gear: 6 days at quantity 1 and 10, 9 days at quantity 100.

## Assumptions

- One part per file; several solids are merged. 3-axis machining on a Haas-class machine.
- $100/hour is the fully loaded rate, with no separate margin line.
- No threads, inserts, coatings or inspection reports; standard tolerance.
- Quotes are processed by a worker: the API returns `202` with a `queued` quote and the client polls.
  The queue is the MongoDB `quotes` collection (polled about once a second, jobs claimed atomically).
  Bull with Redis was rejected: it adds Redis and a Node process, FastAPI cannot enqueue Bull jobs, and
  quote status would live in two places. The cost is up to a second of polling latency.

## Future improvements

- Implement the complexity score (edge density, SA:V, face density), which also activates the
  lead-time buffer.
- Check the price against competitor quotes at quantity 10 and 100 and refit the setup versus
  cutting-time split.
- Replace the per-edge time with total edge length divided by a contour feed rate. A count misleads:
  the gear's 284 edges total 693 mm, the bracket's 45 edges total 1,266 mm.
- Price holes by depth (depth / feed, plus peck cycles) instead of a flat 2 min. The hole axes are
  already found, so the part size along each axis bounds the depth.
- Recognize pockets, slots, threads and undercuts; estimate setups with angled faces and holes.
- Round stock up to standard bar and plate sizes.
- 3D preview with detected features, geometry cache by file hash, expedite/standard/economy tiers,
  and an async job pool instead of database polling.

# Production Scope Contract

Version: `1.0.0`

Use this file as the stable source of truth for `production_scope.json`.

## Required Shape

```json
{
  "main": {
    "enabled": true,
    "ratios": ["1:1", "4:5"],
    "count_by_ratio": {
      "1:1": 7,
      "4:5": 7
    }
  },
  "aplus": {
    "enabled": true,
    "type": "Premium",
    "module_count": 7,
    "desktop_image_count": 10,
    "mobile_image_count": 0,
    "carousel_assignment_status": "DEFERRED_TO_LAYOUT_MATRIX"
  }
}
```

Ask only for missing fields:

- Main images, A+, or both.
- Main-image count for a single ratio, or separate counts for `1:1` and `4:5` when both are requested.
- Main-image ratio: `1:1`, `4:5`, or both.
- Basic A+ or Premium A+.
- Basic A+ standalone image count.
- Premium A+ module count.
- Premium A+ desktop image count and mobile image count.
- Premium A+ carousel module ids and slide counts only when page-display logic already exists; otherwise defer the mapping to the layout matrix.

## Rules

- Never assume a normal number of main images or A+ modules.
- A single requested main-image ratio uses `main.count`.
- When both `1:1` and `4:5` are requested, omit ambiguous `main.count` and require `main.count_by_ratio` with a positive count for each ratio.
- Basic A+ uses `image_count`, not `count`.
- Basic A+ remains fixed at `960x600` and supports at most 7 standalone images.
- Premium A+ `module_count` is the number of Amazon modules, maximum 7.
- Premium A+ `desktop_image_count` includes carousel slides.
- Premium A+ `mobile_image_count` is `0` unless mobile outputs are explicitly requested.
- `carousel_assignment_status: DEFERRED_TO_LAYOUT_MATRIX` allows scope confirmation to record truthful aggregate totals before page-display logic exists; omit `carousel_modules` in this state.
- A deferred desktop total must be at least `module_count` and at most `module_count * 5`; mobile count must be `0` or equal the desktop total.
- After the page-display/layout matrix is designed, set `carousel_assignment_status: RESOLVED` and write exact `carousel_modules` before prompt writing.
- `carousel_modules` records only resolved carousel modules and slide counts.
- Carousel `module_id` values must be unique and within `1..module_count`; each slide count must be `1..5`.
- Expected Premium image count equals `module_count + sum(slides - 1)`. Desktop count must match it; mobile count must be `0` or match it.
- Premium A+ scope uses fixed static modules and optional carousel modules.
- Express every Premium A+ idea through module count, desktop/mobile image count, and optional carousel module slide counts.

## Resolved Premium A+ Example

```json
{
  "aplus": {
    "enabled": true,
    "type": "Premium",
    "module_count": 7,
    "desktop_image_count": 10,
    "mobile_image_count": 0,
    "carousel_assignment_status": "RESOLVED",
    "carousel_modules": [
      {
        "module_id": 7,
        "slides": 4
      }
    ]
  }
}
```

The resolved example demonstrates the schema only. Actual carousel placement must come from the approved page-display logic.

## Basic A+ Example

```json
{
  "aplus": {
    "enabled": true,
    "type": "Basic",
    "image_count": 7
  }
}
```

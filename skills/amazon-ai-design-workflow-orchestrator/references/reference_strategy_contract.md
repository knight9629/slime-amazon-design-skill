# Reference Strategy Contract

Version: `1.0.0`

Use this file as the stable source of truth for `reference_strategy.json`.

## Required Shape

```json
{
  "strategy": "DIRECT_SOURCE",
  "reason": "Clean, complete and trustworthy source views",
  "selected_sources": ["path/to/front.jpg", "path/to/rear.jpg"],
  "source_hashes": {
    "path/to/front.jpg": "<optional sha256>",
    "path/to/rear.jpg": "<optional sha256>"
  }
}
```

## Strategy Choices

- `DIRECT_SOURCE`: real photos are clean and trustworthy enough to serve as authority while generating the required white-background references.
- `MINIMAL_LIBRARY`: source photos need a small corrected reference set because direct use is likely to cause drift.

## Stable Validation Rules

- `selected_sources` must contain at least one real product photo.
- Each selected source must point to an existing image file: `.jpg`, `.jpeg`, `.png`, or `.webp`.
- Relative paths resolve from the folder containing `reference_strategy.json`.
- `source_hashes` is optional, but when present the stable state script verifies SHA-256 hashes.
- Use `DIRECT_SOURCE` only when product silhouette, proportions, color/material, angle, controls, ports, labels, and high-risk details are visible and not distorted by clutter, occlusion, reflections, perspective, or poor resolution.
- Even with `DIRECT_SOURCE`, still generate at least three white-background references, run QC, and get user approval.
- Use `MINIMAL_LIBRARY` when the product is structurally complex, backgrounds obscure the outline, key details are hidden, source angles conflict, or direct use is likely to cause drift.

# Slot Manifest Contract

Version: `1.0.0`

Use this stable contract when sequential count-based filenames cannot represent the requested production set, especially Premium A+ carousel slides.

## Required Shape

```json
{
  "version": 1,
  "slots": [
    {
      "slot_id": "APD01S02",
      "group": "premium_aplus_desktop",
      "raw_file": "aplus_premium_desktop_01_s02_raw.png",
      "output_file": "aplus_premium_desktop_01_s02_1464x600.png",
      "size": [1464, 600]
    }
  ]
}
```

## Rules

- `slot_id` must be unique and use an uppercase production id such as `M01`, `MP01`, `APB01`, `APD01S02`, or `APM01S02`.
- `group` must be one of `main`, `main_portrait`, `basic_aplus`, `premium_aplus_desktop`, or `premium_aplus_mobile`.
- `raw_file` and `output_file` must be plain file names without directories or `..` traversal. Raw files use a supported image extension; outputs use `.png`.
- `raw_file` must exist directly under `raw_generated/`.
- `size` contains two positive integers. `main` must be `1:1`, `main_portrait` must be `4:5`, Basic A+ is fixed at `970x600`, Premium desktop at `1464x600`, and Premium mobile at `600x450`.
- Basic A+ supports at most 5 `basic_aplus` slots.
- `BOUNDED_RATIO_EXPORT`: the raw image must be within 1% of its target aspect ratio; the script resizes it to the exact target size and records any non-identical ratio in `dimension_corrections` with the slot id. It never crops or pads, and a larger ratio error needs image2 rework.
- Output file names must be unique within each group.
- Do not combine `--slot-manifest` with count-based arguments.
- A passing run writes `preview/production_manifest.json` with SHA-256 records. Missing, malformed, or over-limit-ratio slots write only `preview/partial_production_manifest.json`.

## Command

macOS / Linux:

```bash
PYTHONUTF8=1 python3 '<skill-dir>/scripts/postprocess_images.py' \
  --base-dir '<style-output-folder>' \
  --slot-manifest '<style-output-folder>/slot_manifest.json'
```

Windows PowerShell:

```powershell
$env:PYTHONUTF8='1'
& '<python.exe>' '<skill-dir>\scripts\postprocess_images.py' --base-dir '<style-output-folder>' --slot-manifest '<style-output-folder>\slot_manifest.json'
```

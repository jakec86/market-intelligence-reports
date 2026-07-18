---
name: eCarOne VPM Sheet Formatting Standard
description: Exact cell formatting spec for the VPM Performance tab — apply to every new data row on insert
type: feedback
originSessionId: 34920e94-8e55-4dcc-b245-3c7afa0f9b00
---
Apply this formatting to each new month row (B:K) in the eCarOne VPM Results sheet (gid 247007646) after inserting it. Use `batchUpdate` with `repeatCell` requests rather than `copyPaste` from the prior row (which can inherit inconsistencies).

**Why:** Manual inspection after April 2026 run revealed that `copyPaste` from March produced slightly wrong padding, vertical alignment, font size, and text color. The canonical spec comes from rows 2–7 (Oct–Feb).

## Data cell spec (applies to B2:K for all data rows)

| Property | Value |
|---|---|
| Font | Poppins, size 10 |
| Text color | Dark gray — RGB(0.2627, 0.2627, 0.2627) |
| Background | White — RGB(1, 1, 1) |
| Vertical alignment | MIDDLE |
| Wrap strategy | CLIP |
| Padding | top:2, right:8, bottom:2, left:8 |
| Grid lines | Hidden (sheet-level: `hideGridlines: True`) |

## Per-column specs

| Column | Horizontal alignment | Number format |
|--------|---------------------|---------------|
| B (Month) | RIGHT | default (text) |
| C–H (counts) | CENTER | `#,##0` (NUMBER, no decimals) |
| I (VPM % of total) | CENTER | `0%` (PERCENT, no decimals — NOT `0.0%`) |
| J (VPM Incremental Imp Lift) | CENTER | `0%` (PERCENT, no decimals) |
| K (VPM Incremental Leads Lift) | CENTER | `0%` (PERCENT, no decimals) |

## Borders (all data cells)

All four sides: `DOTTED`, black RGB(0,0,0). Exception: column B left border is `SOLID` white (creates visual left edge).

## How to apply

After inserting the new row, issue a `batchUpdate` `repeatCell` for each column range:

```python
def _cell_fmt(h_align, num_fmt_type=None, num_fmt_pattern=None):
    fmt = {
        "textFormat": {"fontFamily": "Poppins", "fontSize": 10,
                       "foregroundColor": {"red": 0.2627451, "green": 0.2627451, "blue": 0.2627451}},
        "backgroundColor": {"red": 1, "green": 1, "blue": 1},
        "horizontalAlignment": h_align,
        "verticalAlignment": "MIDDLE",
        "wrapStrategy": "CLIP",
        "padding": {"top": 2, "right": 8, "bottom": 2, "left": 8},
        "borders": {
            "top":    {"style": "DOTTED", "color": {"red": 0, "green": 0, "blue": 0}},
            "bottom": {"style": "DOTTED", "color": {"red": 0, "green": 0, "blue": 0}},
            "left":   {"style": "DOTTED", "color": {"red": 0, "green": 0, "blue": 0}},
            "right":  {"style": "DOTTED", "color": {"red": 0, "green": 0, "blue": 0}},
        },
    }
    if num_fmt_type:
        fmt["numberFormat"] = {"type": num_fmt_type, "pattern": num_fmt_pattern}
    return fmt
```

Apply per range for the new row (e.g. row index 8 = row 9):
- `B{row}` → RIGHT, no number format
- `C{row}:H{row}` → CENTER, NUMBER `#,##0`
- `I{row}:K{row}` → CENTER, PERCENT `0%`

## Common mistakes to avoid

- Do NOT use `0.0%` for percentage columns — correct pattern is `0%`
- Do NOT use `copyPaste` from the prior row — March and later rows have slightly degraded formatting (wrong padding, BOTTOM vertical alignment, size 11 artifacts)
- Do NOT apply Poppins via the toolbar font picker mid-workflow — always set via API to avoid size drift

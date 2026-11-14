# Schematics

Use this lane for a method, a mechanism, or a pipeline. One claim, three to five stages, left to right.

```json
{
  "width_mm": 178,
  "height_mm": 72,
  "stages": [
    {"label": "Acquire", "role": "data"},
    {"label": "Segment", "role": "model"},
    {"label": "Verify", "role": "check"},
    {"label": "Report", "role": "success"}
  ],
  "feedback": {"from": 2, "to": 1, "label": "reject"}
}
```

```python
from pubfig.schematic import build_schematic
build_schematic(spec, "figures/fig1_method.svg")
```

Roles: `data`, `model`, `process`, `check`, `success`, `fail`, `baseline`, `neutral`. They map into the frozen palette. Two stages that share a role share a color. That is intentional.

## Drawing rules

- Short parallel phrases: Acquire, Segment, Verify, Report. Not "Data collection stage" next to "We then verify".
- The novel stage is the one with the strongest role color. Context stays neutral.
- Solid arrow: the main path. Dashed arrow: feedback, rejection, or an optional control. One feedback corridor, above the row, labeled.
- A color rail may mark the role. It does not replace the label. No icon hunt, no brand marks, no emoji.
- Do not draw a circular arrow and call it learning. If the claim is that a state updates, label the state, the operator, and the gate.
- No gradients, shadows, or embedded photos. Text stays text.
- More than five stages means two figures.

Regenerate the SVG from the spec when the topology changes. Edit the SVG text only for a one-word label fix.

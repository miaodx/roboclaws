# Superseded Cleanup Profile Notes

Status: superseded by the evidence-lane model.

Current public commands use:

```text
evidence_lane decides what the agent sees.
camera_labeler only applies to evidence_lane=camera-grounded-labels.
```

Current evidence lanes:

- `world-public-labels`
- `camera-grounded-labels`
- `camera-raw-fpv`

`smoke` is a verification preset/private runner mode, not a public evidence
lane.

Use current docs instead:

- `README.md` for runnable examples.
- `just/README.md` for public command grammar.
- `docs/human/molmospaces-settings.md` for current MolmoSpaces settings.
- `docs/human/agent-task-command-taxonomy.md` for launch-axis vocabulary.

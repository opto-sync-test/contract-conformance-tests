# TJSV external peer-authority conformance

Tracking: DEN-3959 / ORESoftware/ores-cli#196.

`main.tsp` and `authored.schema.json` are independent human-authored first-class authorities. Neither is generated from, repaired from, ranked below, or allowed to overwrite the other. CI pins canonical TJSV, transpiles TypeSpec to a disposable JSON Schema B witness, compares that witness against the independently authored Draft 2020-12 JSON Schema, runs differential probes, emits Contract IR, and verifies current evidence.

The workflow also mutates only a scratch copy of each lane in turn. TypeSpec-only drift and JSON-Schema-only drift must both be refused. Those negative copies are test evidence, never authorities.

# Retry behavior

The operation makes no more than three total attempts. An attempt includes the
initial request. A successful attempt stops the sequence immediately.

`retry.schema.json` owns the exact configuration shape and bound.

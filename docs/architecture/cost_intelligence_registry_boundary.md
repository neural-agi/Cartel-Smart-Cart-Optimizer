# Cost Intelligence Registry Boundary

The Checkout Observation Registry is the upstream acquisition boundary for Cost Intelligence.
It validates and canonicalizes immutable `CheckoutObservation` values and provides deterministic
registration and retrieval behavior.

`CostIntelligencePipelineService` consumes a `CheckoutObservation` value and does not perform
registry I/O. The `DeterministicCostContextBuilder` applies the same observation canonicalization
boundary before deriving `CostContext.context_id`. This keeps the pipeline synchronous and
side-effect free while ensuring that context identity does not depend on observation ordering.

The registry owns storage and registration lifecycle. The Cost Intelligence pipeline owns only
composition of already materialized immutable observations and downstream evaluation results.

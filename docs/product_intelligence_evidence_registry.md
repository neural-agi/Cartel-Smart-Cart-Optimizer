# Product Intelligence Evidence Registry

## Purpose

The Evidence Registry is the first concrete product-intelligence component. Its job is to preserve provenance before any candidate generation, matching, review, or canonical assertion logic is introduced.

The registry is intentionally filesystem-based and content-addressed. It is not a database abstraction and it does not interpret product identity, pack semantics, or commercial meaning.

This means the architecture is:

- append-only at the evidence-record level: stored evidence records are never overwritten in place
- deduplicated at the content level: identical registration requests resolve to the same deterministic record identity

That is the desired property for Cartel's current evidence layer. The system should not create duplicate physical records for the same provenance payload, but it must also never mutate an existing record to fit later interpretation.

## Evidence Lifecycle

1. A raw artifact reference arrives from extraction or another evidence-producing stage.
2. The registry receives a typed registration request containing platform, source artifact reference, parser version, capture timestamp, and optional capture context.
3. The registry computes a deterministic evidence identifier from the request payload.
4. The registry writes an immutable record directory to disk.
5. The registry materializes an `EvidenceBundle` for downstream consumers.
6. Later stages can reassemble the same bundle from the stored record without rewriting provenance.

Append-only behavior means the registry does not mutate prior evidence records when new captures arrive. A different capture timestamp or source artifact reference produces a different record. An identical registration request resolves to the same record identity and reuses the existing stored bundle rather than writing a divergent duplicate.

## Storage Layout

Evidence is stored under the existing `data` directory in a product-intelligence subtree:

```text
data/
  product_intelligence/
    evidence/
      <platform>/
        <deterministic_evidence_id>/
          record.json
          bundle.json
```

### `record.json`

The registration record stores:

- platform
- source artifact reference
- parser version
- capture timestamp
- capture context reference
- deterministic evidence id
- creation timestamp

### `bundle.json`

The assembled bundle stores:

- platform
- source artifact reference
- capture timestamp
- parser version
- capture context reference
- durable evidence references

The bundle is the handoff object for future candidate generation, review, and assertion stages.

## Bundle Structure

The bundle is intentionally narrow:

- `platform` identifies the acquisition source.
- `source_artifact_reference` identifies the raw captured artifact.
- `capture_timestamp` preserves when the artifact was observed.
- `parser_version` preserves the extraction version.
- `capture_context_reference` preserves the location/session context when available.
- `evidence_references` provides durable pointers for downstream stages.

The bundle does not contain product identity, candidate sets, match scores, or review outcomes.

The typed registry request includes `platform` and `capture_timestamp` because those are not implementation details. They are part of the provenance contract itself. Without them, the registry could not deterministically derive a stable record path, reconstruct an evidence bundle, or preserve the context needed by later review and reprocessing stages.

## Architectural Interpretation

The correct architectural description for the current implementation is:

**content-addressed, append-only evidence storage**

Not:

- mutable evidence storage
- event-log append-only storage that produces a fresh record for every identical request

The distinction matters because Cartel's evidence layer is meant to preserve provenance and support future reprocessing, not to create a historical change log for repeated identical captures.

## Future Integration Points

The Evidence Registry is designed to support later stages without redesign:

- Candidate generation can consume the bundle as immutable provenance input.
- Matching can use the evidence references and parser/version metadata to reason about uncertainty.
- Review workflows can display the original record and the assembled bundle for auditability.
- Assertion updates can link canonical decisions back to the durable evidence record.
- Reprocessing can read the stored record and rebuild bundles after parser or policy changes.

## Uncertainty Notes

The approved architecture defines that evidence must survive every stage, but it does not prescribe a storage backend. This implementation chooses the filesystem for now because it is simple, deterministic, and sufficient for provenance retention before databases or distributed storage are introduced.

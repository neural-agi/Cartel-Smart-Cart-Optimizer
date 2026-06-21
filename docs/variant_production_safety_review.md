# Variant Production Safety Review

## Purpose

This review checks how the current governance set behaves under realistic failure and adversarial conditions.

## Safety Outcomes

| Stress case | Governed result | Matcher behavior |
| --- | --- | --- |
| Incomplete candidate pool | `partial` or `unknown` coverage | `unresolved`; rejection blocked |
| Contradictory lineage | `stale-conflicting` or `invalid` freshness | `conflicting` or `unresolved` depending on direct contradiction |
| Stale catalog snapshot | `stale-compatible` / `stale-unresolved` | usable only when compatibility is preserved; otherwise `unresolved` or `conflicting` |
| Missing coverage declaration | `unknown` coverage | `unresolved`; rejection blocked |
| Missing freshness declaration | `missing` freshness | `unresolved`; no silent promotion |
| Malformed normalization output | `invalid` or `unresolved` pack evidence | `unresolved` unless direct contradiction is proven, then `conflicting` |
| Duplicated candidates | candidate pool remains deterministic after identity comparison | `mapped`, `ambiguous`, or `unresolved` depending on pack evidence; duplicates do not authorize rejection |
| Duplicated lineage records | `invalid` lineage / `contradictory` freshness | `unresolved` or `conflicting` depending on whether the contradiction hits pack identity |
| Category migration | lineage revision / supersession | `stale-compatible`, `stale-unresolved`, or `stale-conflicting` depending on pack identity preservation |
| Pack restructuring event | lineage revision / supersession | `stale-compatible` only if exact pack identity remains preserved; otherwise `stale-conflicting` |

## Failure Scenarios In Detail

### Incomplete Candidate Pools

Behavior:

- candidate-set failure collapses to `unresolved`
- `rejected` is not allowed without validated `representative` coverage

### Contradictory Lineage

Behavior:

- freshness cannot be trusted
- if the contradiction directly hits pack identity, the matcher returns `conflicting`
- otherwise the matcher returns `unresolved` and escalates the lineage record

### Stale Catalog Snapshots

Behavior:

- stale but compatible snapshots can still support matching
- stale and unresolved snapshots cannot force a variant decision
- stale and conflicting snapshots produce `conflicting`

### Missing Coverage Or Freshness

Behavior:

- missing coverage -> `unknown` / `unresolved`
- missing freshness -> `missing` / `unresolved`
- neither may be treated as a green light for rejection

### Malformed Normalization Output

Behavior:

- if the normalized quantity cannot be trusted, the matcher does not pretend certainty
- direct contradiction may still produce `conflicting`
- otherwise the result is `unresolved`

### Duplicated Candidates

Behavior:

- exact duplicates are neutral
- contradictory duplicates invalidate the candidate set and block rejection
- duplicates never increase coverage trust

### Duplicated Lineage Records

Behavior:

- exact duplicates are neutral only if they are byte-identical or hash-identical
- conflicting duplicates invalidate freshness trust
- no duplicate lineage record may silently become authoritative

### Category Migrations

Behavior:

- category migration is a lineage event, not a matcher shortcut
- if the pack identity remains stable, stale-compatible may be possible
- if the pack identity changed, stale-conflicting applies

### Pack Restructuring Events

Behavior:

- pack restructuring must be expressed as lineage evidence
- the matcher may not infer equivalence from total content alone
- if exact pack identity breaks, the result is not mapped

## Production Safety Conclusion

The current governance set fails closed.

When inputs are incomplete, contradictory, or missing, the matcher is forced into `unresolved` or `conflicting` rather than guessing.

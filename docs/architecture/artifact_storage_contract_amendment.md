# Artifact Storage Contract Amendment

Status: Frozen contract amendment

Applies to:

- `docs/architecture/real_data_ingestion_rfc.md`
- `docs/architecture/scrape_job_lifecycle_rfc.md`
- `docs/architecture/scrape_job_contract_amendment.md`

This amendment freezes only artifact-storage behavior required for the raw artifact store implementation slice. It does not alter scraper, worker, scheduler, queue, Playwright, parser, normalization, API, retry, replay, or downstream pipeline contracts.

## 1. Artifact Payload

An artifact payload is the exact byte sequence captured by acquisition and stored for later retrieval.

### Payload Representation

The canonical in-memory payload representation is `bytes`.

Artifact storage must not require payloads to be valid UTF-8 text. HTML, JSON, screenshots, compressed responses, binary diagnostics, and future capture formats are all represented as bytes at the storage boundary.

Text payloads may be encoded by the producer before storage, but the artifact store receives and returns bytes only.

### Metadata Separation

Payload bytes are stored separately from artifact metadata.

Artifact metadata remains represented by immutable contracts such as `RawArtifactReference` and the `StorageReference` defined in this amendment. The artifact store must not infer metadata from payload contents.

### Immutable Fields

The artifact payload is immutable after successful storage.

The following fields are immutable storage inputs:

- `artifact_id`
- `payload`
- `content_digest`
- `content_type`
- `storage_reference`, once produced

### Identity Participation

Artifact domain identity is externally assigned by the artifact-producing boundary and represented by `RawArtifactReference.artifact_id`.

Payload bytes do not define artifact identity inside the artifact store.

The artifact store must verify payload integrity against the supplied `content_digest`, but it must not create a new artifact identity from payload bytes.

Changing payload bytes for the same `artifact_id` is not an update. It is a storage conflict.

## 2. StorageReference

`StorageReference` is an immutable logical reference to a stored artifact payload.

It is not a filesystem path. It is not a URI. It is not an object-store key exposed as a public path. It is an opaque storage identifier whose internal resolution belongs only to the active artifact store implementation.

### Schema

| Field | Type | Required | Identity | Immutable | Producer | Consumer |
|---|---|---:|---:|---:|---|---|
| `storage_reference_id` | non-empty string | yes | yes | yes | artifact store | artifact store, replay, audit |
| `artifact_id` | non-empty string | yes | yes | yes | artifact store from `RawArtifactReference` | artifact store, replay, audit |
| `store_namespace` | non-empty string | yes | yes | yes | artifact store configuration | artifact store |
| `storage_backend` | non-empty string | yes | no | yes | artifact store implementation | audit, diagnostics |
| `content_digest` | non-empty string | yes | yes | yes | artifact producer | artifact store, replay |
| `content_type` | non-empty string | yes | no | yes | artifact producer | artifact store, parser |

### Field Semantics

`storage_reference_id` is deterministic and derived from:

- `store_namespace`
- `artifact_id`
- `content_digest`

`storage_backend` identifies the storage implementation family, such as `local_filesystem`, but does not participate in storage reference identity. This keeps the same artifact logically stable across future backend migrations.

`content_type` is descriptive metadata used by consumers. It does not participate in `storage_reference_id`.

### Replaceability

All consumers outside the artifact store must treat `StorageReference` as opaque. They may persist, compare, and pass it through, but they must not parse it to recover filesystem paths, object keys, or implementation-specific layout.

## 3. Filesystem Layout

The local filesystem implementation resolves `StorageReference` to a deterministic path under a configured root directory.

### Root

The root directory is an implementation configuration input. It is operational metadata and never participates in artifact identity or storage reference identity.

The root directory must be absolute after configuration validation.

### Directory Hierarchy

The filesystem layout is:

```text
<root>/
  artifacts/
    <artifact_id_prefix_2>/
      <artifact_id>/
        payload.bin
        reference.json
```

`artifact_id_prefix_2` is the first two characters of `artifact_id`.

The implementation must reject artifact identifiers shorter than two characters.

### Filename Derivation

Payload filename is always `payload.bin`.

Reference metadata filename is always `reference.json`.

Filenames are not derived from:

- timestamps
- worker identifiers
- platform names
- capture types
- random values
- content type extensions
- queue position
- retry count

### Extension Handling

The local filesystem layout does not derive file extensions from `content_type`.

Content type is preserved in metadata and returned through `StorageReference` or artifact retrieval results. It does not influence path construction.

## 4. ArtifactStore Interface

The public artifact store contract exposes exactly these operations:

- `store`
- `retrieve`
- `exists`

The public contract does not expose `delete` or `list`.

Deletion and listing are intentionally outside this amendment because retention, redaction, indexing, and operator browsing are not part of the raw artifact store slice.

### `store`

`store` accepts an immutable artifact reference and payload bytes.

It returns a `StorageReference`.

Deterministic behavior:

- identical `artifact_id`, `content_digest`, store namespace, and payload bytes produce the same `StorageReference`;
- successful storage writes the payload and reference metadata exactly once;
- storage never mutates the supplied artifact reference or payload object.

Overwrite semantics:

- overwriting an existing artifact is forbidden;
- duplicate storage is governed by Section 5.

Failure semantics:

- invalid artifact reference or invalid payload raises `ArtifactStorageFailure`;
- existing artifact conflicts raise `ArtifactAlreadyExists`;
- filesystem or backend failures raise `ArtifactStorageFailure`;
- partial writes must not be reported as successful.

### `retrieve`

`retrieve` accepts a `StorageReference`.

It returns immutable payload bytes.

Deterministic behavior:

- retrieving the same valid reference from unchanged storage returns identical bytes;
- retrieval must verify the stored payload against `content_digest`;
- retrieval must not mutate storage metadata.

Failure semantics:

- missing artifact raises `ArtifactNotFound`;
- malformed or unresolvable reference raises `InvalidStorageReference`;
- digest mismatch raises `CorruptArtifact`;
- backend read failures raise `ArtifactStorageFailure`.

### `exists`

`exists` accepts a `StorageReference`.

It returns `True` only when the referenced payload and reference metadata are present and structurally readable.

Deterministic behavior:

- `exists` must not create, repair, mutate, or validate payload content beyond structural readability;
- a malformed reference raises `InvalidStorageReference` rather than returning `False`.

Failure semantics:

- missing payload or missing reference metadata returns `False`;
- malformed reference raises `InvalidStorageReference`;
- backend access failure raises `ArtifactStorageFailure`.

## 5. Duplicate Storage

Duplicate storage is deterministic and fail-closed.

If an artifact with the same `artifact_id` already exists:

- if the existing stored payload digest equals the supplied `content_digest`, `store` returns the existing `StorageReference`;
- if the existing stored payload digest differs from the supplied `content_digest`, `store` raises `ArtifactAlreadyExists`;
- if existing metadata is present but unreadable or inconsistent with the payload, `store` raises `CorruptArtifact`;
- the store must never overwrite the existing payload.

This makes repeated execution idempotent for identical artifacts while preserving immutability for conflicting artifacts.

## 6. Retrieval

Retrieval is read-only and integrity-checked.

### Missing Artifact

If no artifact exists at the deterministic location for the supplied `StorageReference`, retrieval raises `ArtifactNotFound`.

### Malformed StorageReference

A storage reference is malformed when:

- any required field is missing;
- any required string is empty;
- `storage_reference_id` does not equal the deterministic identity derived from `store_namespace`, `artifact_id`, and `content_digest`;
- the reference cannot be resolved by the current artifact store without parsing implementation-specific data from public fields.

Malformed references raise `InvalidStorageReference`.

### Payload Verification

Retrieval must compute the digest of stored payload bytes and compare it to `StorageReference.content_digest`.

### Content Digest Verification

The canonical digest format is a non-empty string generated by the artifact-producing boundary. The storage layer treats the digest string as authoritative metadata and verifies exact equality against the digest algorithm declared by implementation contract.

For the local filesystem slice, the digest algorithm is `sha256` and `content_digest` is the lowercase hexadecimal SHA-256 digest of the payload bytes.

### Corruption Handling

If the stored payload exists but its computed digest differs from `StorageReference.content_digest`, retrieval raises `CorruptArtifact`.

If payload exists but reference metadata is missing, malformed, or inconsistent with the payload, retrieval raises `CorruptArtifact`.

## 7. Atomicity

Artifact storage must be atomic at the logical artifact level.

### Temporary Files

Implementations may write to temporary files in the same storage root before publishing the final payload and reference metadata.

Temporary file names are implementation details and must not appear in `StorageReference`.

Temporary file names must not participate in artifact identity.

### Rename Semantics

Publishing a payload must use an atomic replace or atomic rename primitive when available on the storage backend.

The final visible state must be one of:

- artifact not stored;
- artifact fully stored with payload and reference metadata.

### Partial Writes

Partial writes must not be reported as successful.

If a partial write is detected during a later store, retrieve, or exists operation, the operation raises `CorruptArtifact` or `ArtifactStorageFailure` according to whether corruption is attributable to stored artifact state or backend access failure.

### Crash Recovery Expectations

This amendment does not require automated cleanup of temporary files.

After a crash, visible final artifact paths must remain immutable. A later identical `store` call may complete storage only if no final artifact payload exists. If a final payload exists and metadata is inconsistent, the store must fail closed with `CorruptArtifact`.

## 8. Exceptions

The canonical storage exception hierarchy is:

- `ArtifactStorageError`
- `ArtifactNotFound`
- `ArtifactAlreadyExists`
- `ArtifactStorageFailure`
- `CorruptArtifact`
- `InvalidStorageReference`

`ArtifactStorageError` is the base storage exception.

`ArtifactNotFound` means the requested artifact is not present at the resolved storage location.

`ArtifactAlreadyExists` means the artifact identity already exists with conflicting immutable content or metadata.

`ArtifactStorageFailure` means the storage backend could not complete a requested operation for reasons not captured by a more specific storage exception.

`CorruptArtifact` means stored payload or metadata exists but fails integrity or consistency checks.

`InvalidStorageReference` means the supplied storage reference is structurally invalid, unresolved, or inconsistent with deterministic reference identity.

Filesystem, OS, and backend-specific exceptions must not leak through the public artifact store interface.

## 9. Identity

Artifact storage distinguishes domain identity, operational metadata, and filesystem location.

### Domain Identity

Domain artifact identity is represented by `RawArtifactReference.artifact_id`.

The artifact store consumes this identity. It does not generate or reinterpret it.

### Payload Integrity

Payload integrity is represented by `content_digest`.

`content_digest` participates in `StorageReference.storage_reference_id` because it identifies the immutable stored payload for an artifact identity. It does not replace `artifact_id`.

### Storage Reference Identity

`StorageReference.storage_reference_id` is derived from:

- `store_namespace`
- `artifact_id`
- `content_digest`

It excludes:

- filesystem root
- filesystem path
- timestamps
- worker identifiers
- platform
- capture type
- attempt number
- retry count
- queue position
- runtime ordering

### Replay Reference Relationship

Replay references continue to refer to `RawArtifactReference` identity as frozen by the scrape job contract amendment.

Storage references are retrieval handles for payload bytes. They may be preserved for replay, but they do not alter replay identity unless explicitly embedded in a future replay contract amendment.

### Scrape Job Relationship

`RawArtifactReference.job_id` and `RawArtifactReference.attempt_id` remain domain provenance fields for the artifact.

Filesystem location must not be derived from job state, attempt state, retry count, worker id, or lifecycle timestamp.

### Filesystem Location

Filesystem path is an implementation detail derived from `artifact_id` under the configured root.

Consumers must never treat filesystem path as artifact identity or storage reference identity.

## 10. Contract Freeze

The following storage behaviors are now frozen:

- artifact payloads are stored and retrieved as bytes;
- payload metadata remains separate from payload bytes;
- artifact identity is externally assigned and represented by `RawArtifactReference.artifact_id`;
- payload bytes do not generate artifact identity inside the artifact store;
- `StorageReference` is an immutable opaque logical storage reference, not a filesystem path or URI;
- `StorageReference.storage_reference_id` is derived only from `store_namespace`, `artifact_id`, and `content_digest`;
- local filesystem storage uses `<root>/artifacts/<artifact_id_prefix_2>/<artifact_id>/payload.bin` and `<root>/artifacts/<artifact_id_prefix_2>/<artifact_id>/reference.json`;
- filenames do not depend on content type, timestamps, workers, platform, capture type, randomness, queue position, or retry count;
- the artifact store public interface contains only `store`, `retrieve`, and `exists`;
- delete and list are not part of the raw artifact store contract;
- duplicate identical storage is idempotent and returns the existing `StorageReference`;
- duplicate conflicting storage raises `ArtifactAlreadyExists`;
- retrieval verifies payload digest and raises `CorruptArtifact` on mismatch;
- malformed references raise `InvalidStorageReference`;
- missing artifacts raise `ArtifactNotFound`;
- backend-specific exceptions are wrapped in canonical storage exceptions;
- logical artifact writes must be atomic: externally visible state is either absent or fully stored;
- temporary files are implementation details and never participate in identity;
- filesystem paths are never exposed through the public artifact store contract.

Implementation Slice 2 may begin immediately after this amendment without inventing artifact-storage policy.

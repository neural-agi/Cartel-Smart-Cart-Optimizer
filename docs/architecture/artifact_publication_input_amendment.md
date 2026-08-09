# Artifact Publication Input Contract Amendment

Status: Frozen contract amendment

Applies to:

- `docs/architecture/artifact_storage_contract_amendment.md`
- `docs/architecture/local_ingestion_worker_contract_amendment.md`

This amendment resolves only the circularity between the pre-storage
`RawArtifactReference` input and the `storage_reference` produced by
`ArtifactStore.store()`. It does not change artifact identity, filesystem
semantics, retrieval, existence checks, duplicate handling, or storage
replaceability.

## 1. Current Contradiction

The existing Slice 2 interface accepts:

```text
store(RawArtifactReference, payload) -> StorageReference
```

But `RawArtifactReference.storage_reference` is required and non-empty, while
the storage contract defines the storage reference as the value produced by the
artifact store. A worker cannot construct a complete immutable artifact
reference before storage without inventing a sentinel.

The pre-storage and post-storage contracts are therefore separated below.

## 2. ArtifactPublicationRequest

`ArtifactPublicationRequest` is a new immutable storage-input value object. It
contains only information required before storage:

| Field | Type | Required | Identity | Producer |
|---|---|---:|---:|---|
| `artifact_id` | non-empty string | yes | yes | acquisition boundary / worker identity builder |
| `content_digest` | non-empty SHA-256 string | yes | yes | acquisition boundary / worker |
| `content_type` | non-empty string | yes | no | acquisition adapter |

The payload remains a separate `bytes` argument to `store`.

The request does not contain:

- `storage_reference`;
- filesystem paths;
- job or attempt metadata;
- timestamps;
- worker or queue metadata.

`artifact_id` is supplied by the caller. `ArtifactStore` never generates it.
`content_digest` is computed by the caller from the exact payload bytes using
SHA-256. The store recomputes and verifies the digest; disagreement is a
storage failure. The store does not alter the request or payload.

## 3. ArtifactStore.store()

The frozen public operation becomes:

```text
store(request: ArtifactPublicationRequest, payload: bytes) -> StorageReference
```

The operation:

1. validates the request and payload type;
2. recomputes the payload SHA-256 digest;
3. rejects a digest mismatch;
4. resolves the deterministic storage reference from namespace, artifact ID,
   and content digest;
5. stores the immutable payload and metadata atomically;
6. returns the opaque `StorageReference` only after successful publication.

The existing `retrieve` and `exists` operations are unchanged. No filesystem
path or backend-specific location is returned.

## 4. StorageReference

`StorageReference` remains the immutable value object produced by storage.
Its existing fields and identity rules remain unchanged:

- `storage_reference_id` is derived from store namespace, artifact ID, and
  content digest;
- `artifact_id` and `content_digest` are preserved;
- `content_type` remains descriptive metadata;
- storage backend does not participate in storage-reference identity;
- the value is opaque to callers.

The store owns creation of `StorageReference`. It does not own artifact identity.

## 5. Completed RawArtifactReference

`RawArtifactReference` remains immutable and is created only after storage
returns successfully.

The worker constructs it from:

- job ID and attempt ID from the existing contracts;
- platform and capture type from the job;
- content digest from `ArtifactPublicationRequest`;
- content type and source reference from acquisition;
- capture timestamp from acquisition;
- `storage_reference` from the returned `StorageReference` opaque identifier.

The completed reference is the first `RawArtifactReference` published to parser,
replay, audit, or downstream consumers. No pre-storage `RawArtifactReference`
exists.

## 6. Identity and Idempotency

Artifact identity remains externally assigned and is deterministic from the
existing amended rule:

```text
artifact_id = SHA256(job_id, attempt_id, capture_type, content_digest)
```

`storage_reference` does not participate in artifact identity. It is a result of
publishing the already-identified artifact.

The existing duplicate rules remain unchanged:

- same artifact ID and same digest: idempotent success returning the same
  `StorageReference`;
- same artifact ID and different digest: `ArtifactAlreadyExists`;
- digest mismatch between request and payload: `ArtifactStorageFailure`;
- incomplete or corrupt stored state: existing corruption exception.

Separating the input request does not weaken conflict detection because the
store still keys storage by artifact identity and verifies content integrity.

## 7. Failure Semantics

If storage fails:

- no completed `RawArtifactReference` is emitted;
- no parser bridge invocation occurs;
- the worker records the existing storage failure category and lifecycle
  semantics;
- any partial physical write remains subject to the existing atomicity and
  corruption rules and is never reported as successful.

Acquisition metadata and the computed artifact identity may be retained in a
failure record, but they do not become a published artifact reference until
storage succeeds.

## 8. Compatibility Implications for Slice 2

This is a contract-boundary correction, not a storage behavior redesign.

The existing Slice 2 implementation's path layout, namespace behavior, digest
verification, duplicate handling, retrieval, existence checks, and exception
semantics remain unchanged. Its storage-facing input type must be adapted from
the incomplete `RawArtifactReference` shape to `ArtifactPublicationRequest`.

Existing callers that already possess a completed `RawArtifactReference` may
derive an `ArtifactPublicationRequest` from its artifact ID, content digest, and
content type before storage. They must not rely on its pre-existing
`storage_reference` value as an input identity.

## 9. Slice 4 Implications

The local worker now performs:

```text
AcquisitionResult
  -> content digest
  -> artifact ID
  -> ArtifactPublicationRequest
  -> ArtifactStore.store(request, payload)
  -> StorageReference
  -> completed RawArtifactReference
  -> BlinkitParserBridge
```

The worker never fabricates a storage reference and never asks the store to
generate an artifact ID.

## 10. Open Contract Decisions

None. The pre-storage input, storage output, completed artifact reference,
identity ownership, idempotency, and failure boundary are frozen by this
amendment.

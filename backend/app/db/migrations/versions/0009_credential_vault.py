"""add blocked restriction metadata and credential vault

Revision ID: 0009_credential_vault
Revises: 0008_retailer_connections
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0009_credential_vault"
down_revision = "0008_retailer_connections"
branch_labels = None
depends_on = None


_RESTRICTION_SOURCE_IN = (
    "blocked_source IN ('retailer', 'cartel_operator', 'user', 'legal', 'system')"
)
_RESTRICTION_CATEGORY_IN = (
    "blocked_category IN ('account_suspended', 'terms_violation', "
    "'fraud_review', 'legal_hold', 'user_request', 'unknown')"
)
_SECRET_TYPE_IN = (
    "secret_type IN ('oauth_access_token', 'oauth_refresh_token', "
    "'browser_session_credential', 'retailer_authorization_artifact')"
)
_SECRET_STATUS_IN = "status IN ('ACTIVE', 'SUPERSEDED', 'REVOKED', 'DELETED')"
_KEY_VERSION_SHAPE = r"^[a-z0-9][a-z0-9._-]{0,63}$"


def upgrade() -> None:
    # ------------------------------------------------------------------
    # Explicit BLOCKED restriction provenance on retailer_connections.
    # ------------------------------------------------------------------
    op.add_column(
        "retailer_connections",
        sa.Column("blocked_at", sa.DateTime(timezone=True)),
    )
    op.add_column(
        "retailer_connections",
        sa.Column("blocked_source", sa.String(32)),
    )
    op.add_column(
        "retailer_connections",
        sa.Column("blocked_category", sa.String(64)),
    )
    op.create_check_constraint(
        "ck_retailer_connections_blocked_metadata",
        "retailer_connections",
        "status != 'BLOCKED' OR (blocked_at IS NOT NULL "
        "AND blocked_source IS NOT NULL AND blocked_category IS NOT NULL)",
    )
    op.create_check_constraint(
        "ck_retailer_connections_blocked_source",
        "retailer_connections",
        f"blocked_source IS NULL OR {_RESTRICTION_SOURCE_IN}",
    )
    op.create_check_constraint(
        "ck_retailer_connections_blocked_category",
        "retailer_connections",
        f"blocked_category IS NULL OR {_RESTRICTION_CATEGORY_IN}",
    )

    # Composite uniqueness makes owner/connection/retailer binding enforceable
    # by the credential vault's composite foreign key.
    op.create_unique_constraint(
        "uq_retailer_connections_id_user",
        "retailer_connections",
        ["id", "user_id"],
    )
    op.create_unique_constraint(
        "uq_retailer_connections_id_user_retailer",
        "retailer_connections",
        ["id", "user_id", "retailer_id"],
    )

    # ------------------------------------------------------------------
    # Credential vault: one row per encrypted secret version.
    # ------------------------------------------------------------------
    op.create_table(
        "credential_secrets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("reference", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("connection_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("retailer_id", sa.String(32), nullable=False),
        sa.Column("secret_type", sa.String(64), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="ACTIVE"),
        sa.Column("algorithm", sa.String(32), nullable=False, server_default="AES_256_GCM"),
        sa.Column("key_version", sa.String(64), nullable=False),
        sa.Column("nonce", sa.LargeBinary()),
        sa.Column("ciphertext", sa.LargeBinary()),
        sa.Column(
            "rotated_from_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("credential_secrets.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("superseded_at", sa.DateTime(timezone=True)),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(
            ["connection_id", "user_id", "retailer_id"],
            [
                "retailer_connections.id",
                "retailer_connections.user_id",
                "retailer_connections.retailer_id",
            ],
            name="fk_credential_secrets_connection_owner_retailer",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "reference",
            "version",
            name="uq_credential_secrets_reference_version",
        ),
        sa.CheckConstraint(
            "version >= 1",
            name="ck_credential_secrets_version_positive",
        ),
        sa.CheckConstraint(_SECRET_STATUS_IN, name="ck_credential_secrets_status"),
        sa.CheckConstraint(_SECRET_TYPE_IN, name="ck_credential_secrets_type"),
        sa.CheckConstraint(
            "algorithm = 'AES_256_GCM'",
            name="ck_credential_secrets_algorithm",
        ),
        sa.CheckConstraint(
            f"key_version ~ '{_KEY_VERSION_SHAPE}'",
            name="ck_credential_secrets_key_version_shape",
        ),
        sa.CheckConstraint(
            "nonce IS NULL OR octet_length(nonce) = 12",
            name="ck_credential_secrets_nonce_length",
        ),
        sa.CheckConstraint(
            "ciphertext IS NULL OR octet_length(ciphertext) >= 16",
            name="ck_credential_secrets_ciphertext_length",
        ),
        sa.CheckConstraint(
            "status != 'ACTIVE' OR (nonce IS NOT NULL AND ciphertext IS NOT NULL)",
            name="ck_credential_secrets_active_material",
        ),
        sa.CheckConstraint(
            "status != 'REVOKED' OR revoked_at IS NOT NULL",
            name="ck_credential_secrets_revoked_at",
        ),
        sa.CheckConstraint(
            "status != 'DELETED' OR deleted_at IS NOT NULL",
            name="ck_credential_secrets_deleted_at",
        ),
        sa.CheckConstraint(
            "status != 'DELETED' OR (nonce IS NULL AND ciphertext IS NULL)",
            name="ck_credential_secrets_deleted_shredded",
        ),
    )
    op.create_index(
        "ix_credential_secrets_user_connection",
        "credential_secrets",
        ["user_id", "connection_id"],
    )
    op.create_index(
        "ix_credential_secrets_user_retailer",
        "credential_secrets",
        ["user_id", "retailer_id"],
    )
    op.create_index(
        "ix_credential_secrets_reference_owner",
        "credential_secrets",
        ["reference", "user_id", "connection_id", "retailer_id"],
    )
    # At most one ACTIVE version per opaque reference. Rotation supersedes the
    # previous version in the same transaction.
    op.create_index(
        "uq_credential_secrets_active_reference",
        "credential_secrets",
        ["reference"],
        unique=True,
        postgresql_where=sa.text("status = 'ACTIVE'"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_credential_secrets_active_reference",
        table_name="credential_secrets",
    )
    op.drop_index(
        "ix_credential_secrets_reference_owner",
        table_name="credential_secrets",
    )
    op.drop_index(
        "ix_credential_secrets_user_retailer",
        table_name="credential_secrets",
    )
    op.drop_index(
        "ix_credential_secrets_user_connection",
        table_name="credential_secrets",
    )
    op.drop_table("credential_secrets")

    op.drop_constraint(
        "uq_retailer_connections_id_user_retailer",
        "retailer_connections",
        type_="unique",
    )
    op.drop_constraint(
        "uq_retailer_connections_id_user",
        "retailer_connections",
        type_="unique",
    )
    op.drop_constraint(
        "ck_retailer_connections_blocked_category",
        "retailer_connections",
        type_="check",
    )
    op.drop_constraint(
        "ck_retailer_connections_blocked_source",
        "retailer_connections",
        type_="check",
    )
    op.drop_constraint(
        "ck_retailer_connections_blocked_metadata",
        "retailer_connections",
        type_="check",
    )
    op.drop_column("retailer_connections", "blocked_category")
    op.drop_column("retailer_connections", "blocked_source")
    op.drop_column("retailer_connections", "blocked_at")

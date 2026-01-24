"""normalize model id prefixes

Revision ID: j0k1l2m3n4o5
Revises: i9j0k1l2m3n4
Create Date: 2026-01-25 00:00:00.000000

"""
from typing import Sequence, Union
import json

from alembic import op
import sqlalchemy as sa


revision: str = 'j0k1l2m3n4o5'
down_revision: Union[str, None] = 'i9j0k1l2m3n4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def normalize_model_ids(providers: list[dict]) -> tuple[list[dict], bool]:
    modified = False
    for provider in providers:
        if not isinstance(provider, dict):
            continue
        provider_type = provider.get("provider_type")
        models = provider.get("models", [])
        if not isinstance(models, list):
            continue

        prefix = None
        if provider_type == "openrouter":
            prefix = "openrouter/"
        elif provider_type == "openai":
            prefix = "openai/"

        if prefix:
            for model in models:
                if not isinstance(model, dict):
                    continue
                model_id = model.get("model_id", "")
                if model_id and not model_id.startswith(prefix):
                    model["model_id"] = f"{prefix}{model_id}"
                    modified = True

    return providers, modified


def upgrade() -> None:
    from app.core.security import decrypt_value, encrypt_value

    conn = op.get_bind()

    rows = conn.execute(
        sa.text(
            "SELECT id, custom_providers FROM user_settings WHERE custom_providers IS NOT NULL"
        )
    ).fetchall()

    for row in rows:
        value = row.custom_providers
        if value is None:
            continue

        if isinstance(value, str):
            try:
                decrypted = decrypt_value(value)
            except Exception:
                decrypted = value
        else:
            decrypted = value

        providers: list[dict] = []
        if isinstance(decrypted, str):
            try:
                parsed = json.loads(decrypted)
                if isinstance(parsed, list):
                    providers = parsed
            except json.JSONDecodeError:
                continue
        elif isinstance(decrypted, list):
            providers = decrypted
        else:
            continue

        providers, was_modified = normalize_model_ids(providers)

        if was_modified:
            serialized = json.dumps(providers, separators=(",", ":"), ensure_ascii=True)
            encrypted = encrypt_value(serialized)
            conn.execute(
                sa.text(
                    "UPDATE user_settings SET custom_providers = :providers WHERE id = :id"
                ),
                {"providers": encrypted, "id": row.id},
            )


def downgrade() -> None:
    pass

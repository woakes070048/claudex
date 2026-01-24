"""remove codex_auth_json and rename codex provider to openai

Revision ID: e5f6g7h8i9j1
Revises: de5c3ae2e066
Create Date: 2026-01-21 12:00:00.000000

"""

import json
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e5f6g7h8i9j1"
down_revision: Union[str, None] = "de5c3ae2e066"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _parse_providers(value: object, decrypt_value) -> list[dict]:
    if value is None:
        return []
    if isinstance(value, str):
        try:
            decrypted = decrypt_value(value)
        except Exception:
            decrypted = value
    else:
        decrypted = value

    if isinstance(decrypted, str):
        try:
            parsed = json.loads(decrypted)
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            return []
    elif isinstance(decrypted, list):
        return decrypted
    return []


def _get_openai_provider_template(auth_token: str) -> dict:
    return {
        "id": "openai-default",
        "name": "OpenAI",
        "provider_type": "openai",
        "base_url": None,
        "auth_token": auth_token,
        "enabled": True,
        "models": [
            {"model_id": "openai/gpt-5.2-codex", "name": "GPT-5.2 Codex", "enabled": True},
            {"model_id": "openai/gpt-5.2", "name": "GPT-5.2", "enabled": True},
        ],
    }


def _rename_codex_to_openai(providers: list[dict]) -> bool:
    updated = False
    for provider in providers:
        if provider.get("provider_type") == "codex":
            provider["provider_type"] = "openai"
            updated = True

        if provider.get("id") == "codex-default":
            provider["id"] = "openai-default"
            provider["name"] = "OpenAI"
            updated = True

        if "models" in provider:
            for model in provider["models"]:
                model_id = model.get("model_id", "")
                if model_id.startswith("codex/"):
                    model["model_id"] = "openai/" + model_id[6:]
                    updated = True

    return updated


def _add_openrouter_prefix(providers: list[dict]) -> bool:
    updated = False
    for provider in providers:
        if provider.get("provider_type") != "openrouter":
            continue

        if "models" not in provider:
            continue

        for model in provider["models"]:
            model_id = model.get("model_id", "")
            if model_id and not model_id.startswith("openrouter/"):
                model["model_id"] = f"openrouter/{model_id}"
                updated = True

    return updated


def _clean_openai_model_suffixes(providers: list[dict]) -> bool:
    updated = False
    suffixes_to_remove = [":low", ":medium", ":high", ":xhigh"]
    models_to_remove = ["openai/o3"]

    for provider in providers:
        if provider.get("provider_type") != "openai":
            continue

        if "models" not in provider:
            continue

        seen_model_ids: set[str] = set()
        cleaned_models: list[dict] = []

        for model in provider["models"]:
            model_id = model.get("model_id", "")

            if model_id in models_to_remove:
                updated = True
                continue

            clean_id = model_id
            for suffix in suffixes_to_remove:
                if clean_id.endswith(suffix):
                    clean_id = clean_id[: -len(suffix)]
                    updated = True
                    break

            if clean_id in seen_model_ids:
                updated = True
                continue

            seen_model_ids.add(clean_id)
            model["model_id"] = clean_id

            if "(" in model.get("name", ""):
                base_name = model["name"].split(" (")[0]
                model["name"] = base_name
                updated = True

            cleaned_models.append(model)

        provider["models"] = cleaned_models

    return updated


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    user_settings_columns = [c["name"] for c in inspector.get_columns("user_settings")]

    has_codex_column = "codex_auth_json" in user_settings_columns
    has_providers_column = "custom_providers" in user_settings_columns

    if not has_providers_column:
        return

    from app.core.security import decrypt_value, encrypt_value

    if has_codex_column:
        rows = conn.execute(
            sa.text(
                "SELECT id, codex_auth_json, custom_providers FROM user_settings "
                "WHERE codex_auth_json IS NOT NULL OR custom_providers IS NOT NULL"
            )
        ).fetchall()
    else:
        rows = conn.execute(
            sa.text(
                "SELECT id, custom_providers FROM user_settings WHERE custom_providers IS NOT NULL"
            )
        ).fetchall()

    for row in rows:
        codex_auth_json = getattr(row, "codex_auth_json", None) if has_codex_column else None
        providers = _parse_providers(row.custom_providers, decrypt_value)

        updated = False

        if codex_auth_json and (
            not isinstance(codex_auth_json, str) or codex_auth_json.strip()
        ):
            if isinstance(codex_auth_json, str):
                try:
                    codex_auth_json = decrypt_value(codex_auth_json)
                except Exception:
                    pass

            target_provider = None
            for provider in providers:
                if not isinstance(provider, dict):
                    continue
                provider_type = provider.get("provider_type")
                if provider_type in ("openai", "codex"):
                    target_provider = provider
                    break

            if target_provider:
                if not target_provider.get("auth_token"):
                    target_provider["auth_token"] = codex_auth_json
                    updated = True
            else:
                providers.append(_get_openai_provider_template(codex_auth_json))
                updated = True

        if _rename_codex_to_openai(providers):
            updated = True

        if _clean_openai_model_suffixes(providers):
            updated = True

        if _add_openrouter_prefix(providers):
            updated = True

        if updated:
            serialized = json.dumps(providers, separators=(",", ":"), ensure_ascii=True)
            encrypted = encrypt_value(serialized)
            encrypted_json = json.dumps(encrypted)
            conn.execute(
                sa.text(
                    "UPDATE user_settings SET custom_providers = CAST(:value AS JSON) WHERE id = :id"
                ),
                {"value": encrypted_json, "id": row.id},
            )

    if has_codex_column:
        op.drop_column("user_settings", "codex_auth_json")


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    user_settings_columns = [c["name"] for c in inspector.get_columns("user_settings")]

    if "codex_auth_json" not in user_settings_columns:
        op.add_column(
            "user_settings", sa.Column("codex_auth_json", sa.String(), nullable=True)
        )

    if "custom_providers" not in user_settings_columns:
        return

    rows = conn.execute(
        sa.text(
            "SELECT id, custom_providers FROM user_settings WHERE custom_providers IS NOT NULL"
        )
    ).fetchall()

    if not rows:
        return

    from app.core.security import decrypt_value, encrypt_value

    for row in rows:
        providers = _parse_providers(row.custom_providers, decrypt_value)
        if not providers:
            continue

        updated = False
        codex_auth_json = None

        for provider in providers:
            if not isinstance(provider, dict):
                continue

            if provider.get("provider_type") == "openai":
                provider["provider_type"] = "codex"
                updated = True

            if provider.get("id") == "openai-default":
                provider["id"] = "codex-default"
                provider["name"] = "Codex CLI"
                codex_auth_json = provider.get("auth_token")
                updated = True

            if "models" in provider:
                for model in provider["models"]:
                    model_id = model.get("model_id", "")
                    if model_id.startswith("openai/"):
                        model["model_id"] = "codex/" + model_id[7:]
                        updated = True

        if updated:
            serialized = json.dumps(providers, separators=(",", ":"), ensure_ascii=True)
            encrypted = encrypt_value(serialized)
            encrypted_json = json.dumps(encrypted)
            conn.execute(
                sa.text(
                    "UPDATE user_settings SET custom_providers = CAST(:value AS JSON) WHERE id = :id"
                ),
                {"value": encrypted_json, "id": row.id},
            )

        if codex_auth_json:
            if not isinstance(codex_auth_json, str):
                codex_auth_json = json.dumps(codex_auth_json, ensure_ascii=True)
            codex_auth_json = encrypt_value(codex_auth_json)
            conn.execute(
                sa.text(
                    "UPDATE user_settings SET codex_auth_json = :codex_auth_json WHERE id = :id"
                ),
                {"codex_auth_json": codex_auth_json, "id": row.id},
            )

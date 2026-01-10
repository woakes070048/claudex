from collections.abc import AsyncIterator
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.core.user_manager import optional_current_active_user
from app.db.session import SessionLocal, get_db
from app.models.db_models import Chat, User
from app.services.agent import AgentService
from app.services.ai_model import AIModelService
from app.services.chat import ChatService
from app.services.claude_agent import ClaudeAgentService
from app.services.command import CommandService
from app.services.exceptions import UserException
from app.services.message import MessageService
from app.services.refresh_token import RefreshTokenService
from app.services.sandbox import DockerConfig, LocalDockerProvider, SandboxService
from app.services.scheduler import SchedulerService
from app.services.marketplace import MarketplaceService
from app.services.plugin_installer import PluginInstallerService
from app.services.skill import SkillService
from app.services.storage import StorageService
from app.services.user import UserService


def get_ai_model_service() -> AIModelService:
    return AIModelService(session_factory=SessionLocal)


def get_message_service() -> MessageService:
    return MessageService(session_factory=SessionLocal)


def get_user_service() -> UserService:
    return UserService(session_factory=SessionLocal)


def get_refresh_token_service() -> RefreshTokenService:
    return RefreshTokenService(session_factory=SessionLocal)


def get_skill_service() -> SkillService:
    return SkillService()


def get_command_service() -> CommandService:
    return CommandService()


def get_agent_service() -> AgentService:
    return AgentService()


async def get_github_token(
    user: User | None = Depends(optional_current_active_user),
    db: AsyncSession = Depends(get_db),
    user_service: UserService = Depends(get_user_service),
) -> str | None:
    if user is None:
        return None
    try:
        user_settings = await user_service.get_user_settings(user.id, db=db)
        token = user_settings.github_personal_access_token
        return token if token else None
    except UserException:
        return None


async def get_marketplace_service(
    github_token: str | None = Depends(get_github_token),
) -> MarketplaceService:
    return MarketplaceService(github_token=github_token)


async def get_plugin_installer_service(
    github_token: str | None = Depends(get_github_token),
) -> PluginInstallerService:
    return PluginInstallerService(github_token=github_token)


def get_scheduler_service() -> SchedulerService:
    return SchedulerService(session_factory=SessionLocal)


def _create_docker_config() -> DockerConfig:
    from app.core.config import get_settings

    settings = get_settings()
    return DockerConfig(
        image=settings.DOCKER_IMAGE,
        network=settings.DOCKER_NETWORK,
        host=settings.DOCKER_HOST,
        preview_base_url=settings.DOCKER_PREVIEW_BASE_URL,
        sandbox_domain=settings.DOCKER_SANDBOX_DOMAIN,
        traefik_network=settings.DOCKER_TRAEFIK_NETWORK,
    )


async def get_sandbox_service() -> AsyncIterator[SandboxService]:
    provider = LocalDockerProvider(config=_create_docker_config())
    try:
        yield SandboxService(provider)
    finally:
        await provider.cleanup()


async def get_storage_service(
    sandbox_service: SandboxService = Depends(get_sandbox_service),
) -> StorageService:
    return StorageService(sandbox_service)


@dataclass
class SandboxContext:
    sandbox_id: str


async def get_sandbox_context(
    sandbox_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SandboxContext:
    query = select(Chat.sandbox_id).where(
        Chat.sandbox_id == sandbox_id,
        Chat.user_id == current_user.id,
        Chat.deleted_at.is_(None),
    )
    result = await db.execute(query)
    row = result.one_or_none()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Sandbox not found"
        )

    return SandboxContext(
        sandbox_id=row.sandbox_id,
    )


async def get_sandbox_service_for_context(
    context: SandboxContext = Depends(get_sandbox_context),
) -> AsyncIterator[SandboxService]:
    provider = LocalDockerProvider(config=_create_docker_config())
    try:
        yield SandboxService(provider)
    finally:
        await provider.cleanup()


async def get_chat_service(
    file_service: StorageService = Depends(get_storage_service),
    sandbox_service: SandboxService = Depends(get_sandbox_service),
    user_service: UserService = Depends(get_user_service),
) -> AsyncIterator[ChatService]:
    async with ClaudeAgentService(session_factory=SessionLocal) as ai_service:
        yield ChatService(
            file_service,
            sandbox_service,
            ai_service,
            user_service,
            session_factory=SessionLocal,
        )

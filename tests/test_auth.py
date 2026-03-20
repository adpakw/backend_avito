import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.dependencies.auth import get_current_account, get_current_active_account
from app.errors import (
    AccountBlockedError,
    AccountNotFoundError,
    InvalidCredentialsError,
)
from app.main import app
from app.models.account import Account
from app.services.auth_service import AuthService, get_auth_service


@pytest.fixture
def auth_service_override(test_account):
    mock_service = AsyncMock()
    mock_service.authenticate = AsyncMock(return_value=test_account)
    mock_service.create_access_token = MagicMock(return_value="test.jwt.token")

    app.dependency_overrides[get_auth_service] = lambda: mock_service
    yield mock_service
    app.dependency_overrides.pop(get_auth_service, None)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def blocked_account():
    return Account(
        id=2,
        login="blockeduser",
        password="$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",
        is_blocked=True,
        created_at=datetime.now(),
    )


class TestAuthServiceUnit:
    @pytest.mark.asyncio
    async def test_authenticate_success(self, test_account):
        auth_service = AuthService()
        auth_service.account_repo = AsyncMock()
        auth_service.account_repo.authenticate.return_value = test_account

        result = await auth_service.authenticate("testuser", "password")

        assert result == test_account
        auth_service.account_repo.authenticate.assert_called_once_with(
            "testuser", "password"
        )

    @pytest.mark.asyncio
    async def test_authenticate_invalid_credentials(self):
        auth_service = AuthService()
        auth_service.account_repo = AsyncMock()
        auth_service.account_repo.authenticate.return_value = None

        with pytest.raises(InvalidCredentialsError):
            await auth_service.authenticate("wrong", "credentials")

    @pytest.mark.asyncio
    async def test_authenticate_blocked_account(self, blocked_account):
        auth_service = AuthService()
        auth_service.account_repo = AsyncMock()
        auth_service.account_repo.authenticate.return_value = blocked_account

        with pytest.raises(AccountBlockedError):
            await auth_service.authenticate("blockeduser", "password")

    def test_create_access_token(self, test_account):
        auth_service = AuthService()
        token = auth_service.create_access_token(test_account)

        assert token is not None
        assert isinstance(token, str)

        payload = jwt.decode(
            token, auth_service.secret_key, algorithms=[auth_service.algorithm]
        )
        assert payload["sub"] == str(test_account.id)
        assert payload["login"] == test_account.login

    @pytest.mark.asyncio
    async def test_verify_token_success(self, test_account):
        auth_service = AuthService()
        auth_service.account_repo = AsyncMock()
        auth_service.account_repo.get_by_id.return_value = test_account

        token = auth_service.create_access_token(test_account)
        account = await auth_service.verify_token(token)

        assert account.id == test_account.id
        assert account.login == test_account.login

    @pytest.mark.asyncio
    async def test_verify_token_expired(self, test_account):
        auth_service = AuthService()
        auth_service.access_token_expire_minutes = -1
        auth_service.account_repo = AsyncMock()

        token = auth_service.create_access_token(test_account)

        with pytest.raises(InvalidCredentialsError) as exc_info:
            await auth_service.verify_token(token)
        assert "Token expired" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_verify_token_invalid(self):
        auth_service = AuthService()
        auth_service.account_repo = AsyncMock()

        with pytest.raises(InvalidCredentialsError):
            await auth_service.verify_token("invalid.token.here")

    @pytest.mark.asyncio
    async def test_verify_token_account_not_found(self, test_account):
        auth_service = AuthService()
        auth_service.account_repo = AsyncMock()
        auth_service.account_repo.get_by_id.side_effect = AccountNotFoundError()

        token = auth_service.create_access_token(test_account)

        with pytest.raises(InvalidCredentialsError):
            await auth_service.verify_token(token)


class TestAuthDependencies:
    @pytest.mark.asyncio
    async def test_get_current_account_success(self, test_account):
        auth_service = AuthService()
        auth_service.account_repo = AsyncMock()
        auth_service.account_repo.get_by_id.return_value = test_account

        token = auth_service.create_access_token(test_account)
        credentials = MagicMock()
        credentials.credentials = token

        with patch("app.dependencies.auth.security", return_value=credentials):
            with patch(
                "app.dependencies.auth.get_auth_service", return_value=auth_service
            ):
                account = await get_current_account(credentials, auth_service)
                assert account.id == test_account.id
                assert account.login == test_account.login

    @pytest.mark.asyncio
    async def test_get_current_account_invalid_token(self):
        auth_service = AuthService()
        credentials = MagicMock()
        credentials.credentials = "invalid.token"

        with patch("app.dependencies.auth.get_auth_service", return_value=auth_service):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_account(credentials, auth_service)
            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_active_account_success(self, test_account):
        account = await get_current_active_account(test_account)
        assert account == test_account

    @pytest.mark.asyncio
    async def test_get_current_active_account_blocked(self, blocked_account):
        with pytest.raises(HTTPException) as exc_info:
            await get_current_active_account(blocked_account)
        assert exc_info.value.status_code == 403
        assert "blocked" in str(exc_info.value.detail).lower()


class TestAuthAPI:
    @pytest.fixture(autouse=True)
    def setup_method(self):
        self.auth_service_mock = AsyncMock(spec=AuthService)

    def test_login_success(self, client, auth_service_override):
        response = client.post(
            "/auth/login", data={"username": "testuser", "password": "password"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["access_token"] == "test.jwt.token"

    def test_login_invalid_credentials(self, client):
        with patch("app.routes.auth.get_auth_service") as mock_get_auth:
            mock_get_auth.return_value = self.auth_service_mock
            self.auth_service_mock.authenticate.side_effect = InvalidCredentialsError(
                "Invalid login or password"
            )

            response = client.post(
                "/auth/login", data={"username": "wrong", "password": "wrong"}
            )

            assert response.status_code == 401
            data = response.json()
            assert "Invalid login or password" in data["detail"]

    def test_login_blocked_account(self, client):
        mock_service = AsyncMock()
        mock_service.authenticate.side_effect = AccountBlockedError(
            "Account is blocked"
        )
        app.dependency_overrides[get_auth_service] = lambda: mock_service

        try:
            response = client.post(
                "/auth/login", data={"username": "blockeduser", "password": "password"}
            )
            assert response.status_code == 403
        finally:
            app.dependency_overrides.pop(get_auth_service, None)


@pytest.mark.integration
class TestAccountRepositoryIntegration:
    @pytest.mark.asyncio
    async def test_create_and_get_account(self):
        from app.repositories.accounts import AccountRepository

        repo = AccountRepository()

        account = await repo.create("test_integration", "testpass123")
        assert account.login == "test_integration"
        assert account.id > 0
        assert not account.is_blocked

        fetched = await repo.get_by_id(account.id)
        assert fetched.login == account.login
        assert fetched.password == account.password

        fetched_by_login = await repo.get_by_login("test_integration")
        assert fetched_by_login.id == account.id

        await repo.delete(account.id)

    @pytest.mark.asyncio
    async def test_authenticate_account(self):
        from app.repositories.accounts import AccountRepository

        repo = AccountRepository()

        account = await repo.create("auth_test", "securepass")

        authenticated = await repo.authenticate("auth_test", "securepass")
        assert authenticated is not None
        assert authenticated.id == account.id

        failed = await repo.authenticate("auth_test", "wrongpass")
        assert failed is None

        not_found = await repo.authenticate("nonexistent", "securepass")
        assert not_found is None

        await repo.delete(account.id)

    @pytest.mark.asyncio
    async def test_block_account(self):
        from app.errors import AccountBlockedError
        from app.repositories.accounts import AccountRepository

        repo = AccountRepository()
        unique_login = f"block_test_{uuid.uuid4().hex[:8]}"
        account = await repo.create(unique_login, "testpass")

        blocked = await repo.block(account.id, True)
        assert blocked.is_blocked

        with pytest.raises(AccountBlockedError):
            await repo.authenticate(unique_login, "testpass")

        unlocked = await repo.block(account.id, False)
        assert not unlocked.is_blocked

        auth = await repo.authenticate(unique_login, "testpass")
        assert auth is not None

        await repo.delete(account.id)

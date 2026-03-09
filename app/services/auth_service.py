import datetime
import logging
import os
import sys

import jwt
from dotenv import load_dotenv

from app.errors import (
    AccountBlockedError,
    AccountNotFoundError,
    InvalidCredentialsError,
)
from app.models.account import Account
from app.repositories.accounts import AccountRepository

logging.basicConfig(
    level=logging.INFO,
    format="\033[92m%(levelname)s\033[0m:  \t  %(message)s",
    stream=sys.stdout,
)

logger = logging.getLogger("app")
load_dotenv()


class AuthService:
    _instance = None

    def __init__(self):
        self.account_repo = AccountRepository()
        self.secret_key = os.getenv("JWT_SECRET_KEY")
        self.algorithm = "HS256"
        self.access_token_expire_minutes = int(
            os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES")
        )

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def create_access_token(self, account: Account) -> str:
        expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
            minutes=self.access_token_expire_minutes
        )

        to_encode = {
            "sub": str(account.id),
            "login": account.login,
            "exp": expire,
            "iat": datetime.datetime.now(datetime.timezone.utc),
        }

        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    async def authenticate(self, login: str, password: str) -> Account:
        logger.info(f"Authenticating user: {login}")
        
        account = await self.account_repo.authenticate(login, password)
        if not account:
            logger.warning(f"Failed authentication attempt for user: {login}")
            raise InvalidCredentialsError("Invalid login or password")
        
        if account.is_blocked:
            logger.warning(f"Blocked user attempted login: {login}")
            raise AccountBlockedError("Account is blocked")
        
        logger.info(f"User authenticated successfully: {login} (id: {account.id})")
        return account

    async def verify_token(self, token: str) -> Account:
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            account_id = int(payload.get("sub"))

            if not account_id:
                raise InvalidCredentialsError("Invalid token")

            account = await self.account_repo.get_by_id(account_id)

            if account.is_blocked:
                raise AccountBlockedError("Account is blocked")

            return account

        except jwt.ExpiredSignatureError:
            raise InvalidCredentialsError("Token expired")
        except jwt.InvalidTokenError:
            raise InvalidCredentialsError("Invalid token")
        except AccountNotFoundError:
            raise InvalidCredentialsError("Account not found")

    def get_auth_service(self):
        return self


auth_service_client = AuthService()


def get_auth_service():
    return auth_service_client.get_auth_service()

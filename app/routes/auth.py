import logging
import sys

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm

from app.errors import AccountBlockedError, InvalidCredentialsError
from app.models.account import TokenResponse
from app.services.auth_service import AuthService, get_auth_service

logging.basicConfig(
    level=logging.INFO,
    format="\033[92m%(levelname)s\033[0m:  \t  %(message)s",
    stream=sys.stdout,
)

logger = logging.getLogger("app")
router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    auth_service: AuthService = Depends(get_auth_service),
):
    try:
        account = await auth_service.authenticate(
            form_data.username, form_data.password
        )
        token = auth_service.create_access_token(account)

        response.set_cookie(
            key="access_token",
            value=f"Bearer {token}",
            httponly=True,
            max_age=1800,
            expires=1800,
            samesite="lax",
            secure=False,
        )

        logger.info(f"User {account.login} logged in successfully")

        return TokenResponse(access_token=token)

    except InvalidCredentialsError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )
    except AccountBlockedError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )

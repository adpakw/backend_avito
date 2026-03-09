from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.models.account import Account
from app.services.auth_service import AuthService, get_auth_service
from app.errors import InvalidCredentialsError, AccountBlockedError

security = HTTPBearer()


async def get_current_account(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends(get_auth_service),
) -> Account:
    token = credentials.credentials
    
    try:
        account = await auth_service.verify_token(token)
        return account
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


async def get_current_active_account(
    current_account: Account = Depends(get_current_account),
) -> Account:
    if current_account.is_blocked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is blocked",
        )
    return current_account
"""Authentication routes: registration, login, tokens, email and password reset."""

import redis.asyncio as redis
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Request,
    status,
)
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.db import get_db
from src.database.models import User as UserModel
from src.schemas import (
    RequestEmail,
    ResetPasswordRequest,
    TokenModel,
    TokenRefreshRequest,
    User,
    UserCreate,
)
from src.services.auth import (
    Hash,
    create_access_token,
    create_refresh_token,
    create_reset_token,
    get_current_user,
    get_email_from_token,
    get_reset_token_payload,
    password_fingerprint,
    verify_refresh_token,
)
from src.services.cache import get_redis, invalidate_user
from src.services.email import send_reset_password_email, send_verification_email
from src.services.limiter import limiter
from src.services.users import UserService

router = APIRouter(prefix="/auth", tags=["auth"])

# Хеш для вирівнювання часу відповіді, коли користувача не знайдено
DUMMY_HASH = Hash().get_password_hash("dummy-password")


async def _issue_tokens(user: UserModel, user_service: UserService) -> TokenModel:
    access_token = create_access_token(data={"sub": user.username})
    refresh_token = create_refresh_token(data={"sub": user.username})
    await user_service.update_refresh_token(user, refresh_token)
    return TokenModel(access_token=access_token, refresh_token=refresh_token)


@router.post(
    "/register", response_model=User, status_code=status.HTTP_201_CREATED
)
async def register_user(
    body: UserCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Register a new user and send a verification email.

    Raises:
        HTTPException: 409 if the email or username is already taken.
    """
    user_service = UserService(db)

    if await user_service.get_user_by_email(body.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists",
        )
    if await user_service.get_user_by_username(body.username):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this username already exists",
        )

    hashed_password = Hash().get_password_hash(body.password)
    new_user = await user_service.create_user(body, hashed_password)
    background_tasks.add_task(
        send_verification_email, new_user.email, new_user.username
    )
    return new_user


@router.post(
    "/login", response_model=TokenModel, status_code=status.HTTP_201_CREATED
)
async def login_user(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """Log in with username and password and get an access + refresh token pair.

    Raises:
        HTTPException: 401 on wrong credentials or unconfirmed email.
    """
    user_service = UserService(db)
    user = await user_service.get_user_by_username(form_data.username)
    hasher = Hash()
    if user is None:
        hasher.verify_password(form_data.password, DUMMY_HASH)
    if user is None or not hasher.verify_password(
        form_data.password, user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.confirmed:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email address is not confirmed",
        )

    return await _issue_tokens(user, user_service)


@router.post("/refresh_token", response_model=TokenModel)
async def refresh_token(
    body: TokenRefreshRequest, db: AsyncSession = Depends(get_db)
):
    """Exchange a valid refresh token for a new token pair.

    The refresh token is rotated: the old one stops working.

    Raises:
        HTTPException: 401 if the refresh token is invalid, expired or revoked.
    """
    user = await verify_refresh_token(body.refresh_token, db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return await _issue_tokens(user, UserService(db))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    r: redis.Redis = Depends(get_redis),
):
    """Revoke the current user's refresh token and drop them from the cache."""
    # Після commit ORM-об'єкти прострочуються, тож ім'я читаємо заздалегідь
    username = user.username
    user_service = UserService(db)
    db_user = await user_service.get_user_by_username(username)
    if db_user is not None:
        await user_service.update_refresh_token(db_user, None)
    await invalidate_user(r, username)


@router.get("/confirmed_email/{token}")
async def confirmed_email(
    token: str,
    db: AsyncSession = Depends(get_db),
    r: redis.Redis = Depends(get_redis),
):
    """Confirm the user's email using the token from the verification email.

    Raises:
        HTTPException: 422 for an invalid token, 400 if the user does not exist.
    """
    email = get_email_from_token(token)
    user_service = UserService(db)
    user = await user_service.get_user_by_email(email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Verification error"
        )
    if user.confirmed:
        return {"message": "Your email is already confirmed"}
    username = user.username
    await user_service.confirmed_email(email)
    await invalidate_user(r, username)
    return {"message": "Email confirmed"}


@router.post("/request_email", status_code=status.HTTP_201_CREATED)
async def request_email(
    body: RequestEmail,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Resend the verification email."""
    user = await UserService(db).get_user_by_email(body.email)
    if user is not None and user.confirmed:
        return {"message": "Your email is already confirmed"}
    if user is not None:
        background_tasks.add_task(send_verification_email, user.email, user.username)
    return {"message": "Check your email for confirmation"}


@router.post(
    "/request_password_reset",
    status_code=status.HTTP_202_ACCEPTED,
    description="No more than 5 requests per minute",
)
@limiter.limit("5/minute")
async def request_password_reset(
    request: Request,
    body: RequestEmail,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Send a password reset token to the user's email.

    The response is the same whether the email is registered or not, so the
    endpoint cannot be used to discover accounts.
    """
    user = await UserService(db).get_user_by_email(body.email)
    if user is not None:
        token = create_reset_token(user.email, user.hashed_password)
        background_tasks.add_task(
            send_reset_password_email, user.email, user.username, token
        )
    return {"message": "If this email is registered, a reset link has been sent"}


@router.post("/reset_password")
async def reset_password(
    body: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
    r: redis.Redis = Depends(get_redis),
):
    """Set a new password using a reset token.

    The token is single-use and changing the password also revokes the
    refresh token.

    Raises:
        HTTPException: 400 if the token is invalid, expired or already used.
    """
    email, fingerprint = get_reset_token_payload(body.token)
    user_service = UserService(db)
    user = await user_service.get_user_by_email(email)
    if user is None or password_fingerprint(user.hashed_password) != fingerprint:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )
    username = user.username
    await user_service.update_password(
        email, Hash().get_password_hash(body.new_password)
    )
    await invalidate_user(r, username)
    return {"message": "Password has been reset"}

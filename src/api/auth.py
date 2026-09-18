from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.db import get_db
from src.schemas import RequestEmail, Token, User, UserCreate
from src.services.auth import Hash, create_access_token, get_email_from_token
from src.services.email import send_verification_email
from src.services.users import UserService

router = APIRouter(prefix="/auth", tags=["auth"])

# Хеш для вирівнювання часу відповіді, коли користувача не знайдено
DUMMY_HASH = Hash().get_password_hash("dummy-password")


@router.post(
    "/register", response_model=User, status_code=status.HTTP_201_CREATED
)
async def register_user(
    body: UserCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
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


@router.post("/login", response_model=Token, status_code=status.HTTP_201_CREATED)
async def login_user(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    user = await UserService(db).get_user_by_username(form_data.username)
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

    access_token = create_access_token(data={"sub": user.username})
    return Token(access_token=access_token, token_type="bearer")


@router.get("/confirmed_email/{token}")
async def confirmed_email(token: str, db: AsyncSession = Depends(get_db)):
    email = get_email_from_token(token)
    user_service = UserService(db)
    user = await user_service.get_user_by_email(email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Verification error"
        )
    if user.confirmed:
        return {"message": "Your email is already confirmed"}
    await user_service.confirmed_email(email)
    return {"message": "Email confirmed"}


@router.post("/request_email", status_code=status.HTTP_201_CREATED)
async def request_email(
    body: RequestEmail,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    user = await UserService(db).get_user_by_email(body.email)
    if user is not None and user.confirmed:
        return {"message": "Your email is already confirmed"}
    if user is not None:
        background_tasks.add_task(send_verification_email, user.email, user.username)
    return {"message": "Check your email for confirmation"}

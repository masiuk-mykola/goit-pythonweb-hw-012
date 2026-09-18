from cloudinary.exceptions import Error as CloudinaryError
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.conf.config import config
from src.database.db import get_db
from src.database.models import User as UserModel
from src.schemas import User
from src.services.auth import get_current_user
from src.services.limiter import limiter
from src.services.upload_file import UploadFileService
from src.services.users import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "/me", response_model=User, description="No more than 10 requests per minute"
)
@limiter.limit("10/minute")
async def me(request: Request, user: UserModel = Depends(get_current_user)):
    return user


@router.patch("/avatar", response_model=User)
async def update_avatar_user(
    file: UploadFile = File(),
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not (file.content_type or "").startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Avatar must be an image",
        )
    try:
        avatar_url = UploadFileService(
            config.CLD_NAME, config.CLD_API_KEY, config.CLD_API_SECRET
        ).upload_file(file, user.username)
    except CloudinaryError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to upload avatar",
        )

    return await UserService(db).update_avatar_url(user.email, avatar_url)

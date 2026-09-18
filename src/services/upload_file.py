"""Avatar upload to Cloudinary."""

import cloudinary
import cloudinary.uploader
from fastapi import UploadFile


class UploadFileService:
    """Configures Cloudinary and uploads avatars.

    Args:
        cloud_name: Cloudinary cloud name.
        api_key: Cloudinary API key.
        api_secret: Cloudinary API secret.
    """

    def __init__(self, cloud_name: str, api_key: str, api_secret: str):
        cloudinary.config(
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret,
            secure=True,
        )

    @staticmethod
    def upload_file(file: UploadFile, username: str) -> str:
        """Upload an image, overwriting the user's previous avatar.

        Args:
            file: Uploaded image.
            username: Used as the Cloudinary public ID.

        Returns:
            str: URL of a 250x250 cropped version of the image.
        """
        public_id = f"ContactsApp/{username}"
        result = cloudinary.uploader.upload(
            file.file, public_id=public_id, overwrite=True
        )
        return cloudinary.CloudinaryImage(public_id).build_url(
            width=250, height=250, crop="fill", version=result.get("version")
        )

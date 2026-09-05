"""Normalize uploaded images to WebP with a 2048px maximum edge."""

from io import BytesIO
import uuid

from django.core.files.base import ContentFile
from django.db.models.fields.files import ImageFieldFile

from PIL import Image, ImageOps


MAX_IMAGE_EDGE = 2048
WEBP_QUALITY = 82


def normalize_image_field(field_file: ImageFieldFile) -> None:
    """Convert a newly uploaded ImageField value to a WebP file in storage."""
    if not field_file or not field_file.name or field_file._committed:
        return

    source = field_file.file
    source.seek(0)
    with Image.open(source) as image:
        image = ImageOps.exif_transpose(image)
        if image.mode not in ('RGB', 'RGBA'):
            image = image.convert('RGBA' if 'A' in image.getbands() else 'RGB')

        if max(image.size) > MAX_IMAGE_EDGE:
            image.thumbnail((MAX_IMAGE_EDGE, MAX_IMAGE_EDGE), Image.Resampling.LANCZOS)

        output = BytesIO()
        image.save(output, format='WEBP', quality=WEBP_QUALITY, method=6)
        output.seek(0)

    # Let ImageField apply its configured upload_to path before storage.save.
    new_name = field_file.field.generate_filename(
        field_file.instance,
        f'img_{uuid.uuid4().hex}.webp',
    )
    # Avoid overwriting a different upload with the same original filename.
    saved_name = field_file.storage.save(new_name, ContentFile(output.read()))
    field_file.name = saved_name
    field_file._committed = True

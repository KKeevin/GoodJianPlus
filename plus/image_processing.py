"""Normalize uploaded images to WebP with a 2048px maximum edge."""

from io import BytesIO
import uuid
import warnings

from django.core.files.base import ContentFile
from django.db.models import ImageField
from django.db.models.fields.files import ImageFieldFile

from PIL import Image, ImageOps


MAX_IMAGE_EDGE = 2048
WEBP_QUALITY = 82
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_PIXELS = 40_000_000


class ImageUploadError(OSError):
    pass


def can_upload_editor_image(request):
    user = request.user
    return user.is_active and user.is_staff and any(
        user.has_perm(permission) for permission in (
            'plus.add_article', 'plus.change_article',
            'plus.add_product', 'plus.change_product',
        )
    )


def normalize_uploaded_images(sender, instance, raw=False, update_fields=None, **kwargs):
    if raw:
        return
    # Never access relation descriptors on an unsaved model.
    for field in sender._meta.concrete_fields:
        is_attachment = sender._meta.label_lower == 'django_summernote.attachment' and field.name == 'file'
        if not isinstance(field, ImageField) and not is_attachment:
            continue
        if update_fields is not None and field.name not in update_fields:
            continue
        normalize_image_field(getattr(instance, field.attname))


def normalize_image_field(field_file: ImageFieldFile) -> None:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            _normalize_image_field(field_file)
    except (OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise ImageUploadError('圖片無法處理；請使用有效的 JPG、PNG、WebP 等點陣圖片，檔案不超過 10 MB、像素不超過 4000 萬。') from exc


def _normalize_image_field(field_file: ImageFieldFile) -> None:
    """Convert a newly uploaded ImageField value to a WebP file in storage."""
    if not field_file or not field_file.name or field_file._committed:
        return

    source = field_file.file
    if source.size > MAX_UPLOAD_BYTES:
        raise OSError('圖片上限為 10 MB，請先縮小後再上傳。')
    source.seek(0)
    with Image.open(source) as image:
        if image.width * image.height > MAX_PIXELS:
            raise OSError('圖片像素過大，請先縮小後再上傳。')
        # Animated uploads deliberately use the first frame.
        image.seek(0)
        image = ImageOps.exif_transpose(image)
        if image.mode not in ('RGB', 'RGBA'):
            image = image.convert('RGBA' if 'A' in image.getbands() or 'transparency' in image.info else 'RGB')

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
    field_file._file = None
    if hasattr(field_file, '_dimensions_cache'):
        del field_file._dimensions_cache
    field_file._committed = True

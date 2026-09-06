from django.apps import AppConfig


class PlusConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'plus'
    verbose_name = '其他功能'

    def ready(self):
        from plus import checks  # noqa: F401
        from django.db.models.signals import pre_save
        from plus.image_processing import normalize_uploaded_images

        pre_save.connect(
            normalize_uploaded_images,
            dispatch_uid='plus.normalize_uploaded_images',
            weak=False,
        )

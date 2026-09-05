from django.apps import AppConfig


class PlusConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'plus'
    verbose_name = '其他功能'

    def ready(self):
        from django.db.models.signals import pre_save
        from django.db.models.fields.files import ImageFieldFile
        from django.apps import apps
        from plus.image_processing import normalize_image_field

        def normalize_uploaded_images(sender, instance, **kwargs):
            for field in sender._meta.get_fields():
                if not hasattr(field, 'attname') or not isinstance(getattr(instance, field.attname, None), ImageFieldFile):
                    continue
                normalize_image_field(getattr(instance, field.attname))

        pre_save.connect(
            normalize_uploaded_images,
            dispatch_uid='plus.normalize_uploaded_images',
        )

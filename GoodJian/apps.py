from django_summernote.apps import DjangoSummernoteConfig


class SummernoteConfig(DjangoSummernoteConfig):
    # Match the dependency's existing Attachment migration; do not generate
    # an untracked migration inside site-packages when checking this project.
    default_auto_field = 'django.db.models.AutoField'

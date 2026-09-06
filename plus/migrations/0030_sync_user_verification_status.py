from django.db import migrations
from django.db.models import Q


def sync_verification_status(apps, schema_editor):
    """Repair cached account verification flags from their source fields."""
    CustomUser = apps.get_model('plus', 'CustomUser')
    CustomUser.objects.filter(
        Q(phone_verified=True) | Q(email_verified=True)
    ).update(is_verified=True)
    CustomUser.objects.filter(
        phone_verified=False, email_verified=False
    ).update(is_verified=False)


class Migration(migrations.Migration):
    dependencies = [
        ('plus', '0029_refund_evidence'),
    ]

    operations = [
        migrations.RunPython(sync_verification_status, migrations.RunPython.noop),
    ]

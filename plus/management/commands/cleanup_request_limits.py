from django.core.management.base import BaseCommand
from django.utils import timezone
from plus.models.commerce import RequestLimit


class Command(BaseCommand):
    help = '刪除已過期的登入限流計數。'

    def handle(self, *args, **options):
        count, _ = RequestLimit.objects.filter(expires_at__lt=timezone.now()).delete()
        self.stdout.write(str(count))

from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = '建立限定權限的職務群組；不更動會員的群組指派。'

    @transaction.atomic
    def handle(self, *args, **options):
        roles = {
            '商品編輯': {'product', 'productimage', 'category', 'brand'},
            '專欄編輯': {'article', 'articleimage', 'articlecategory'},
            '出貨人員': {'order'},
            '財務對帳': {'paymentreceipt', 'returnrequest'},
        }
        for name, models in roles.items():
            group, _ = Group.objects.get_or_create(name=name)
            actions = ('view', 'change', 'add') if '編輯' in name else ('view', 'change')
            codenames = [f'{action}_{model}' for model in models for action in actions]
            group.permissions.set(Permission.objects.filter(content_type__app_label='plus', codename__in=codenames))
            self.stdout.write(name)

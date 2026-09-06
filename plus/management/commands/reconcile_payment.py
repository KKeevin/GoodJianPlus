from decimal import Decimal, InvalidOperation
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from plus.models import Order
from plus.models.commerce import PaymentReceipt
from plus.services.payments import settle_payment


class Command(BaseCommand):
    help = '可信 SSH 人工對帳：先在金流平台確認成功付款，再記錄實際交易與對帳憑證。此指令不會扣款。'

    def add_arguments(self, parser):
        parser.add_argument('order_number')
        parser.add_argument('--provider', choices=['ecpay', 'linepay'], required=True)
        parser.add_argument('--transaction', required=True)
        parser.add_argument('--amount', required=True)
        parser.add_argument('--reference', required=True, help='金流查詢／人工對帳憑證（不可填卡號等敏感資料）')
        parser.add_argument('--confirmed', action='store_true')

    def handle(self, *args, **options):
        if not options['confirmed'] or not options['reference'].strip():
            raise CommandError('必須先於金流平台確認實際成功付款，填寫憑證並加上 --confirmed。')
        try:
            amount = Decimal(options['amount'])
            if not amount.is_finite() or amount <= 0:
                raise ValueError('金額必須為正數')
            with transaction.atomic():
                order = Order.objects.get(order_number=options['order_number'])
                settled = settle_payment(order.pk, options['provider'], options['transaction'], amount)
                receipt = PaymentReceipt.objects.get(provider=options['provider'], transaction_id=options['transaction'])
                if not receipt.resolution:
                    receipt.resolution = 'SSH 人工對帳：' + options['reference']
                    receipt.save(update_fields=['resolution'])
        except (Order.DoesNotExist, ValidationError, InvalidOperation, ValueError) as exc:
            raise CommandError('訂單／交易／金額不符，未完成對帳。') from exc
        self.stdout.write('付款已入帳。' if settled else '已記錄付款，訂單仍待人工處理，請核對退款，不可直接出貨。')

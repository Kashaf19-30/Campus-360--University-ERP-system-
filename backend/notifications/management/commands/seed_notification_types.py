from django.core.management.base import BaseCommand
from notifications.system_notify import ensure_notification_types


class Command(BaseCommand):
    help = 'Seed standard system notification types'

    def handle(self, *args, **options):
        ensure_notification_types()
        self.stdout.write(self.style.SUCCESS('System notification types ensured.'))

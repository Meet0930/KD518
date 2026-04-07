from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from water.models import BottleFillEntry, ReminderConfig, TurnState
from water.notifications import send_turn_reminder_email


class Command(BaseCommand):
    help = "Send reminder emails if no one has filled the bottle recently."

    def handle(self, *args, **options):
        config = ReminderConfig.get_solo()
        interval = timedelta(hours=config.reminder_interval_hours)

        last_entry = BottleFillEntry.objects.order_by("-filled_at").first()
        now = timezone.now()

        if not last_entry:
            should_remind = True
        else:
            should_remind = now - last_entry.filled_at > interval

        if not should_remind:
            self.stdout.write(self.style.SUCCESS("No reminder needed."))
            return

        turn_state = TurnState.get_solo()
        current_turn = turn_state.current_roommate
        if not current_turn:
            self.stdout.write(self.style.WARNING("No roommates found."))
            return

        sent = send_turn_reminder_email(
            current_turn,
            notify_all=getattr(settings, "TURN_REMINDER_NOTIFY_ALL", False),
        )
        if sent == 0:
            self.stdout.write(self.style.WARNING("No email addresses available."))
            return
        self.stdout.write(self.style.SUCCESS(f"Reminder email(s) sent: {sent}"))


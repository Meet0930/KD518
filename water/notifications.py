from django.conf import settings
from django.core.mail import send_mail

from .models import Roommate


GUJARATI_SUBJECT = "પાણી ભરવાનો વારો યાદ અપાવો"
GUJARATI_BODY = """નમસ્તે,

આજે તમારો પાણી ભરવાનો વારો છે.
કૃપા કરીને પાણી ભરવા જશો.

આભાર."""


def _all_roommate_emails() -> list[str]:
    return list(
        Roommate.objects.exclude(email__isnull=True)
        .exclude(email="")
        .values_list("email", flat=True)
        .distinct()
    )


def send_turn_reminder_email(turn_roommate: Roommate | None, notify_all: bool = False) -> int:
    if turn_roommate is None:
        return 0

    if notify_all:
        recipients = _all_roommate_emails()
    elif turn_roommate.email:
        recipients = [turn_roommate.email]
    else:
        recipients = _all_roommate_emails()

    if not recipients:
        return 0

    send_mail(
        GUJARATI_SUBJECT,
        GUJARATI_BODY,
        settings.DEFAULT_FROM_EMAIL,
        recipients,
        fail_silently=settings.EMAIL_FAIL_SILENTLY,
    )
    return len(recipients)

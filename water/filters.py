from datetime import timedelta

from django.utils import timezone

from .models import BottleFillEntry


def filter_entries(queryset, request):
    roommate_id = request.GET.get("roommate")
    date_filter = request.GET.get("date_filter")
    date_from = request.GET.get("date_from")
    date_to = request.GET.get("date_to")

    if roommate_id:
        queryset = queryset.filter(roommate_id=roommate_id)

    now = timezone.now()
    if date_filter == "today":
        queryset = queryset.filter(filled_at__date=now.date())
    elif date_filter == "yesterday":
        yesterday = now.date() - timedelta(days=1)
        queryset = queryset.filter(filled_at__date=yesterday)
    elif date_filter == "week":
        week_ago = now - timedelta(days=7)
        queryset = queryset.filter(filled_at__gte=week_ago)
    elif date_filter == "custom" and date_from and date_to:
        queryset = queryset.filter(filled_at__date__range=[date_from, date_to])

    return queryset


def get_last_fill_time():
    last = BottleFillEntry.objects.order_by("-filled_at").first()
    return last.filled_at if last else None


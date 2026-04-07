from datetime import timedelta

from django.db.models import Sum
from django.utils import timezone

from .models import BottleFillEntry
from .turns import get_turn_snapshot


def total_bottles_per_roommate():
    return (
        BottleFillEntry.objects.values("roommate__id", "roommate__name")
        .annotate(total_bottles=Sum("quantity"))
        .order_by("-total_bottles")
    )


def daily_stats():
    today = timezone.now().date()
    return (
        BottleFillEntry.objects.filter(filled_at__date=today)
        .values("roommate__name")
        .annotate(total_bottles=Sum("quantity"))
        .order_by("-total_bottles")
    )


def weekly_stats():
    now = timezone.now()
    week_ago = now - timedelta(days=7)
    return (
        BottleFillEntry.objects.filter(filled_at__gte=week_ago)
        .values("roommate__name")
        .annotate(total_bottles=Sum("quantity"))
        .order_by("-total_bottles")
    )


def get_most_active_roommate():
    agg = total_bottles_per_roommate()
    return agg[0] if agg else None


def get_next_roommate_to_fill():
    snapshot = get_turn_snapshot()
    return snapshot.get("next_turn")


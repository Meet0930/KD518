from django.contrib import admin

from .models import Roommate, BottleFillEntry, ReminderConfig, TurnState, PendingTask, SkipTurn


@admin.register(Roommate)
class RoommateAdmin(admin.ModelAdmin):
    list_display = ("turn_position", "name", "email", "user")
    search_fields = ("name", "email", "user__username")
    ordering = ("turn_position", "id")


@admin.register(BottleFillEntry)
class BottleFillEntryAdmin(admin.ModelAdmin):
    list_display = ("roommate", "target_roommate", "quantity", "action_type", "filled_at")
    list_filter = ("roommate", "action_type", "filled_at")
    search_fields = ("roommate__name",)


@admin.register(ReminderConfig)
class ReminderConfigAdmin(admin.ModelAdmin):
    list_display = ("reminder_interval_hours",)


@admin.register(TurnState)
class TurnStateAdmin(admin.ModelAdmin):
    list_display = ("current_roommate", "remaining_bottles", "updated_at")


@admin.register(PendingTask)
class PendingTaskAdmin(admin.ModelAdmin):
    list_display = ("roommate", "remaining_bottles", "is_completed", "updated_at")
    list_filter = ("is_completed",)


@admin.register(SkipTurn)
class SkipTurnAdmin(admin.ModelAdmin):
    list_display = ("roommate", "reason", "is_used", "created_at", "used_at")
    list_filter = ("is_used", "reason")


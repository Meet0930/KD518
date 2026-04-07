from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Roommate(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(blank=True, null=True)
    turn_position = models.PositiveIntegerField(
        default=0,
        help_text="Lower numbers come first in the fixed turn order.",
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Link to a Django user who can log in and record fills.",
    )

    def __str__(self) -> str:
        return self.name

    class Meta:
        ordering = ["turn_position", "id"]


class BottleFillEntry(models.Model):
    ACTION_NORMAL = "normal"
    ACTION_PARTIAL_HELP = "partial_help"
    ACTION_FULL_HELP_SKIP = "full_help_skip"
    ACTION_SKIPPED = "skipped_turn"
    ACTION_CHOICES = [
        (ACTION_NORMAL, "Normal"),
        (ACTION_PARTIAL_HELP, "Partial Help"),
        (ACTION_FULL_HELP_SKIP, "Full Help + Skip"),
        (ACTION_SKIPPED, "Skipped Turn"),
    ]

    roommate = models.ForeignKey(Roommate, on_delete=models.CASCADE, related_name="fills")
    target_roommate = models.ForeignKey(
        Roommate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="received_fills",
        help_text="Whose turn this fill was counted for.",
    )
    quantity = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(2)],
        help_text="Only 1 or 2 bottles are allowed.",
    )
    action_type = models.CharField(max_length=20, choices=ACTION_CHOICES, default=ACTION_NORMAL)
    filled_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.roommate.name} - {self.quantity} bottle(s) at {self.filled_at}"


class ReminderConfig(models.Model):
    reminder_interval_hours = models.PositiveIntegerField(default=4)

    class Meta:
        verbose_name = "Reminder Configuration"
        verbose_name_plural = "Reminder Configuration"

    def __str__(self) -> str:
        return f"Reminders every {self.reminder_interval_hours} hour(s)"

    @classmethod
    def get_solo(cls) -> "ReminderConfig":
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class TurnState(models.Model):
    current_roommate = models.ForeignKey(
        Roommate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="current_turn_states",
    )
    remaining_bottles = models.PositiveSmallIntegerField(
        default=2,
        validators=[MinValueValidator(1), MaxValueValidator(2)],
        help_text="Bottles remaining to complete current roommate's turn.",
    )
    updated_at = models.DateTimeField(auto_now=True)

    @classmethod
    def get_solo(cls) -> "TurnState":
        obj, _ = cls.objects.get_or_create(pk=1, defaults={"remaining_bottles": 2})
        return obj


class PendingTask(models.Model):
    roommate = models.ForeignKey(Roommate, on_delete=models.CASCADE, related_name="pending_tasks")
    remaining_bottles = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(2)],
    )
    is_completed = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        status = "completed" if self.is_completed else "pending"
        return f"{self.roommate.name}: {self.remaining_bottles} bottle(s) {status}"


class SkipTurn(models.Model):
    roommate = models.ForeignKey(Roommate, on_delete=models.CASCADE, related_name="skip_turns")
    is_used = models.BooleanField(default=False)
    reason = models.CharField(max_length=120, default="full_help_skip")
    created_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]


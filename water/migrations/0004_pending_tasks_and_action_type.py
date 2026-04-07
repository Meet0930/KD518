# Generated manually for pending task tracking.

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("water", "0003_turn_based_system"),
    ]

    operations = [
        migrations.AlterField(
            model_name="bottlefillentry",
            name="action_type",
            field=models.CharField(
                choices=[
                    ("normal", "Normal"),
                    ("skipped_turn", "Skipped Turn"),
                    ("extra_partial", "Extra Partial"),
                ],
                default="normal",
                max_length=20,
            ),
        ),
        migrations.CreateModel(
            name="PendingTask",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "remaining_bottles",
                    models.PositiveSmallIntegerField(
                        default=1,
                        validators=[
                            django.core.validators.MinValueValidator(1),
                            django.core.validators.MaxValueValidator(2),
                        ],
                    ),
                ),
                ("is_completed", models.BooleanField(default=False)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "roommate",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="pending_tasks",
                        to="water.roommate",
                    ),
                ),
            ],
            options={"ordering": ["-updated_at"]},
        ),
    ]

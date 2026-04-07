# Generated manually for turn-based system.

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("water", "0002_roommate_user"),
    ]

    operations = [
        migrations.AddField(
            model_name="bottlefillentry",
            name="action_type",
            field=models.CharField(
                choices=[("normal", "Normal"), ("skipped_turn", "Skipped Turn")],
                default="normal",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="bottlefillentry",
            name="quantity",
            field=models.PositiveIntegerField(
                default=1,
                help_text="Only 1 or 2 bottles are allowed.",
                validators=[
                    django.core.validators.MinValueValidator(1),
                    django.core.validators.MaxValueValidator(2),
                ],
            ),
        ),
        migrations.AddField(
            model_name="roommate",
            name="turn_position",
            field=models.PositiveIntegerField(
                default=0,
                help_text="Lower numbers come first in the fixed turn order.",
            ),
        ),
        migrations.CreateModel(
            name="TurnState",
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
                        default=2,
                        help_text="Bottles remaining to complete current roommate's turn.",
                        validators=[
                            django.core.validators.MinValueValidator(1),
                            django.core.validators.MaxValueValidator(2),
                        ],
                    ),
                ),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "current_roommate",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="current_turn_states",
                        to="water.roommate",
                    ),
                ),
            ],
        ),
    ]

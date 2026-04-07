# Generated manually for advanced help/skip rules.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("water", "0004_pending_tasks_and_action_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="bottlefillentry",
            name="target_roommate",
            field=models.ForeignKey(
                blank=True,
                help_text="Whose turn this fill was counted for.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="received_fills",
                to="water.roommate",
            ),
        ),
        migrations.AlterField(
            model_name="bottlefillentry",
            name="action_type",
            field=models.CharField(
                choices=[
                    ("normal", "Normal"),
                    ("partial_help", "Partial Help"),
                    ("full_help_skip", "Full Help + Skip"),
                    ("skipped_turn", "Skipped Turn"),
                ],
                default="normal",
                max_length=20,
            ),
        ),
        migrations.CreateModel(
            name="SkipTurn",
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
                ("is_used", models.BooleanField(default=False)),
                ("reason", models.CharField(default="full_help_skip", max_length=120)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("used_at", models.DateTimeField(blank=True, null=True)),
                (
                    "roommate",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="skip_turns",
                        to="water.roommate",
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]

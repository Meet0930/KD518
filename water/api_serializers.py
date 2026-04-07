from rest_framework import serializers

from .models import Roommate, BottleFillEntry


class RoommateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Roommate
        fields = ["id", "name", "email"]


class BottleFillEntrySerializer(serializers.ModelSerializer):
    roommate = RoommateSerializer(read_only=True)
    roommate_id = serializers.PrimaryKeyRelatedField(
        queryset=Roommate.objects.all(),
        source="roommate",
        write_only=True,
    )

    class Meta:
        model = BottleFillEntry
        fields = ["id", "roommate", "roommate_id", "quantity", "filled_at"]
        read_only_fields = ["filled_at"]


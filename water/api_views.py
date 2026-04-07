from rest_framework import viewsets

from .models import Roommate, BottleFillEntry
from .api_serializers import RoommateSerializer, BottleFillEntrySerializer


class RoommateViewSet(viewsets.ModelViewSet):
    queryset = Roommate.objects.all()
    serializer_class = RoommateSerializer


class BottleFillEntryViewSet(viewsets.ModelViewSet):
    queryset = BottleFillEntry.objects.select_related("roommate").all()
    serializer_class = BottleFillEntrySerializer


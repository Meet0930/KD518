from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from water.api_views import RoommateViewSet, BottleFillEntryViewSet

router = DefaultRouter()
router.register(r"roommates", RoommateViewSet, basename="api-roommates")
router.register(r"fills", BottleFillEntryViewSet, basename="api-fills")


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include(router.urls)),
    path("", include("water.urls", namespace="water")),
]


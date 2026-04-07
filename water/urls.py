from django.urls import path

from .views import (
    DashboardView,
    BottleFillCreateView,
    HistoryView,
    HistoryEntryDeleteView,
    StatsView,
    FilterView,
    RoommateListView,
    RoommateCreateView,
    RoommateUpdateView,
    RoommateDeleteView,
    UserLoginView,
    UserLogoutView,
    AdminLoginView,
    AdminPanelView,
    AdminRoommateListView,
    AdminFillListView,
    AdminFillDeleteView,
    AdminReminderConfigView,
    AdminUserListView,
    AdminUserCreateView,
    AdminUserUpdateView,
    AdminUserDeleteView,
)

app_name = "water"

urlpatterns = [
    path("login/", UserLoginView.as_view(), name="login"),
    path("logout/", UserLogoutView.as_view(), name="logout"),
    path("entry/add/", BottleFillCreateView.as_view(), name="entry_add"),
    path("history/", HistoryView.as_view(), name="history"),
    path("history/<int:pk>/delete/", HistoryEntryDeleteView.as_view(), name="history_entry_delete"),
    path("stats/", StatsView.as_view(), name="stats"),
    path("filter/", FilterView.as_view(), name="filter"),
    path("panel/login/", AdminLoginView.as_view(), name="admin_login"),
    path("panel/", AdminPanelView.as_view(), name="admin_panel"),
    path("panel/roommates/", AdminRoommateListView.as_view(), name="admin_roommates"),
    path("panel/fills/", AdminFillListView.as_view(), name="admin_fills"),
    path("panel/fills/<int:pk>/delete/", AdminFillDeleteView.as_view(), name="admin_fill_delete"),
    path("panel/reminders/", AdminReminderConfigView.as_view(), name="admin_reminders"),
    path("panel/users/", AdminUserListView.as_view(), name="admin_users"),
    path("panel/users/add/", AdminUserCreateView.as_view(), name="admin_user_add"),
    path("panel/users/<int:pk>/edit/", AdminUserUpdateView.as_view(), name="admin_user_edit"),
    path(
        "panel/users/<int:pk>/delete/",
        AdminUserDeleteView.as_view(),
        name="admin_user_delete",
    ),
    path("", DashboardView.as_view(), name="dashboard"),
    path("roommates/", RoommateListView.as_view(), name="roommate_list"),
    path("roommates/add/", RoommateCreateView.as_view(), name="roommate_add"),
    path("roommates/<int:pk>/edit/", RoommateUpdateView.as_view(), name="roommate_edit"),
    path("roommates/<int:pk>/delete/", RoommateDeleteView.as_view(), name="roommate_delete"),
]


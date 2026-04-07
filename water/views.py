from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.contrib.auth.views import LoginView, LogoutView
from django.db.models import Sum
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View

from .models import Roommate, BottleFillEntry, ReminderConfig
from .forms import (
    RoommateForm,
    BottleFillForm,
    ReminderConfigForm,
    AdminUserCreateForm,
    AdminUserUpdateForm,
)
from .filters import filter_entries
from .stats import (
    total_bottles_per_roommate,
    daily_stats,
    weekly_stats,
    get_most_active_roommate,
    get_next_roommate_to_fill,
)
from .turns import get_turn_snapshot, record_turn_fill, rebuild_turn_state_from_entries


def _is_staff(user) -> bool:
    return bool(user and user.is_authenticated and user.is_staff)


class UserLoginView(LoginView):
    """
    Login page for normal users. Admins still use /admin/login/.
    """

    template_name = "water/login.html"

    def get_success_url(self):
        if self.request.user.is_staff:
            return str(reverse_lazy("water:admin_panel"))
        return str(reverse_lazy("water:dashboard"))


class UserLogoutView(LogoutView):
    next_page = reverse_lazy("water:login")


class AdminLoginView(LoginView):
    """
    Frontend admin login (NOT Django /admin/).
    Only staff users are allowed to log in here.
    """

    template_name = "water/admin_login.html"
    authentication_form = AuthenticationForm

    def form_valid(self, form):
        user = form.get_user()
        if not _is_staff(user):
            messages.error(self.request, "This account is not allowed to access the admin panel.")
            return redirect("water:admin_login")
        return super().form_valid(form)

    def get_success_url(self):
        return str(reverse_lazy("water:admin_panel"))


@method_decorator(login_required, name="dispatch")
class DashboardView(View):
    def _get_logged_in_roommate(self, user):
        try:
            return Roommate.objects.get(user=user)
        except Roommate.DoesNotExist:
            return None

    def get(self, request):
        entries = BottleFillEntry.objects.select_related("roommate").order_by("-filled_at")
        entries = filter_entries(entries, request)
        total_quantity = BottleFillEntry.objects.aggregate(total=Sum("quantity")).get("total") or 0
        today_quantity = (
            BottleFillEntry.objects.filter(filled_at__date=timezone.now().date())
            .aggregate(total=Sum("quantity"))
            .get("total")
            or 0
        )

        roommate = self._get_logged_in_roommate(request.user)
        bottle_form = BottleFillForm(roommate=roommate)

        context = {
            "entries": entries,
            "bottle_form": bottle_form,
            "roommates": Roommate.objects.all(),
            "totals": total_bottles_per_roommate(),
            "daily": daily_stats(),
            "weekly": weekly_stats(),
            "most_active": get_most_active_roommate(),
            "next_roommate": get_next_roommate_to_fill(),
            "current_roommate": roommate,
            "total_quantity": total_quantity,
            "today_quantity": today_quantity,
            **get_turn_snapshot(),
        }
        return render(request, "water/dashboard.html", context)

    def post(self, request):
        roommate = self._get_logged_in_roommate(request.user)
        if roommate is None:
            messages.error(
                request,
                "Your account is not linked to a roommate. Please ask the admin to link it.",
            )
            return redirect("water:dashboard")

        bottle_form = BottleFillForm(request.POST, roommate=roommate)
        if bottle_form.is_valid():
            quantity = bottle_form.cleaned_data["quantity"]
            try:
                turn_result = record_turn_fill(actor=roommate, quantity=quantity)
            except ValidationError as exc:
                messages.error(request, str(exc))
                return redirect("water:dashboard")
            messages.success(request, "Bottle fill recorded successfully.")
            for info in turn_result.messages:
                messages.info(request, info)
        else:
            messages.error(request, "There was a problem with your submission.")

        return redirect("water:dashboard")


@method_decorator(user_passes_test(_is_staff), name="dispatch")
class RoommateListView(View):
    def get(self, request):
        roommates = Roommate.objects.all().order_by("id")
        return render(request, "water/roommate_list.html", {"roommates": roommates})


@method_decorator(user_passes_test(_is_staff), name="dispatch")
class RoommateCreateView(View):
    def get(self, request):
        form = RoommateForm()
        return render(request, "water/roommate_form.html", {"form": form})

    def post(self, request):
        form = RoommateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Roommate added.")
            return redirect("water:roommate_list")
        return render(request, "water/roommate_form.html", {"form": form})


@method_decorator(user_passes_test(_is_staff), name="dispatch")
class RoommateUpdateView(View):
    def get(self, request, pk):
        roommate = get_object_or_404(Roommate, pk=pk)
        form = RoommateForm(instance=roommate)
        return render(
            request,
            "water/roommate_form.html",
            {"form": form, "roommate": roommate},
        )

    def post(self, request, pk):
        roommate = get_object_or_404(Roommate, pk=pk)
        form = RoommateForm(request.POST, instance=roommate)
        if form.is_valid():
            form.save()
            messages.success(request, "Roommate updated.")
            return redirect("water:roommate_list")
        return render(
            request,
            "water/roommate_form.html",
            {"form": form, "roommate": roommate},
        )


@method_decorator(user_passes_test(_is_staff), name="dispatch")
class RoommateDeleteView(View):
    def get(self, request, pk):
        roommate = get_object_or_404(Roommate, pk=pk)
        return render(
            request,
            "water/roommate_confirm_delete.html",
            {"roommate": roommate},
        )

    def post(self, request, pk):
        roommate = get_object_or_404(Roommate, pk=pk)
        roommate.delete()
        messages.success(request, "Roommate deleted.")
        return redirect("water:roommate_list")


@method_decorator(login_required, name="dispatch")
class BottleFillCreateView(View):
    def get(self, request):
        roommate = Roommate.objects.filter(user=request.user).first()
        if roommate is None:
            messages.error(
                request,
                "Your account is not linked to a roommate. Please ask the admin to link it.",
            )
            return redirect("water:dashboard")

        form = BottleFillForm(roommate=roommate, request_user=request.user)
        context = {"form": form, "roommate": roommate, **get_turn_snapshot()}
        return render(request, "water/add_entry.html", context)

    def post(self, request):
        roommate = Roommate.objects.filter(user=request.user).first()
        if roommate is None:
            messages.error(
                request,
                "Your account is not linked to a roommate. Please ask the admin to link it.",
            )
            return redirect("water:dashboard")

        form = BottleFillForm(request.POST, roommate=roommate, request_user=request.user)
        if form.is_valid():
            actor = form.cleaned_data["roommate"]
            if not request.user.is_staff and actor.id != roommate.id:
                messages.error(request, "You can only add entry for your own name.")
                return redirect("water:entry_add")
            quantity = form.cleaned_data["quantity"]
            try:
                turn_result = record_turn_fill(actor=actor, quantity=quantity)
            except ValidationError as exc:
                messages.error(request, str(exc))
                return redirect("water:entry_add")
            messages.success(request, "Bottle fill recorded successfully.")
            for info in turn_result.messages:
                messages.info(request, info)
            return redirect("water:history")

        context = {"form": form, "roommate": roommate, **get_turn_snapshot()}
        return render(request, "water/add_entry.html", context)


@method_decorator(login_required, name="dispatch")
class HistoryView(View):
    def get(self, request):
        entries = BottleFillEntry.objects.select_related("roommate", "target_roommate").order_by("-filled_at")
        entries = filter_entries(entries, request)
        context = {
            "entries": entries,
            "roommates": Roommate.objects.all().order_by("name"),
        }
        return render(request, "water/history.html", context)


@method_decorator(login_required, name="dispatch")
class HistoryEntryDeleteView(View):
    def _can_delete(self, request, entry: BottleFillEntry) -> bool:
        if request.user.is_staff:
            return True
        return bool(entry.roommate and entry.roommate.user_id == request.user.id)

    def get(self, request, pk):
        entry = BottleFillEntry.objects.select_related("roommate", "target_roommate").filter(pk=pk).first()
        if not entry:
            messages.error(request, "Entry does not exist.")
            return redirect("water:history")
        if not self._can_delete(request, entry):
            messages.error(request, "You are not allowed to delete this entry.")
            return redirect("water:history")
        return render(request, "water/history_confirm_delete.html", {"entry": entry})

    def post(self, request, pk):
        entry = BottleFillEntry.objects.select_related("roommate").filter(pk=pk).first()
        if not entry:
            messages.error(request, "Entry does not exist.")
            return redirect("water:history")
        if not self._can_delete(request, entry):
            messages.error(request, "You are not allowed to delete this entry.")
            return redirect("water:history")

        entry.delete()
        rebuild_turn_state_from_entries()
        messages.success(request, "Entry deleted successfully.")
        return redirect("water:history")


@method_decorator(login_required, name="dispatch")
class StatsView(View):
    def get(self, request):
        context = {
            "totals": total_bottles_per_roommate(),
            "daily": daily_stats(),
            "weekly": weekly_stats(),
            "most_active": get_most_active_roommate(),
            "next_roommate": get_next_roommate_to_fill(),
        }
        return render(request, "water/stats.html", context)


@method_decorator(login_required, name="dispatch")
class FilterView(View):
    def get(self, request):
        entries = BottleFillEntry.objects.select_related("roommate").order_by("-filled_at")
        entries = filter_entries(entries, request)
        context = {
            "entries": entries,
            "roommates": Roommate.objects.all().order_by("name"),
        }
        return render(request, "water/filter.html", context)


@method_decorator(user_passes_test(_is_staff), name="dispatch")
class AdminPanelView(View):
    def get(self, request):
        context = {
            "roommate_count": Roommate.objects.count(),
            "fill_count": BottleFillEntry.objects.count(),
            "reminder_config": ReminderConfig.get_solo(),
        }
        return render(request, "water/admin_panel.html", context)


@method_decorator(user_passes_test(_is_staff), name="dispatch")
class AdminRoommateListView(View):
    def get(self, request):
        roommates = Roommate.objects.select_related("user").all().order_by("id")
        return render(request, "water/admin_roommates.html", {"roommates": roommates})


@method_decorator(user_passes_test(_is_staff), name="dispatch")
class AdminFillListView(View):
    def get(self, request):
        entries = BottleFillEntry.objects.select_related("roommate").order_by("-filled_at")
        entries = filter_entries(entries, request)
        return render(request, "water/admin_fills.html", {"entries": entries})


@method_decorator(user_passes_test(_is_staff), name="dispatch")
class AdminFillDeleteView(View):
    def get(self, request, pk):
        entry = get_object_or_404(BottleFillEntry, pk=pk)
        return render(request, "water/admin_fill_confirm_delete.html", {"entry": entry})

    def post(self, request, pk):
        entry = get_object_or_404(BottleFillEntry, pk=pk)
        entry.delete()
        messages.success(request, "Bottle entry deleted successfully.")
        return redirect("water:admin_fills")


@method_decorator(user_passes_test(_is_staff), name="dispatch")
class AdminReminderConfigView(View):
    def get(self, request):
        cfg = ReminderConfig.get_solo()
        form = ReminderConfigForm(instance=cfg)
        return render(request, "water/admin_reminder_config.html", {"form": form})

    def post(self, request):
        cfg = ReminderConfig.get_solo()
        form = ReminderConfigForm(request.POST, instance=cfg)
        if form.is_valid():
            form.save()
            messages.success(request, "Reminder settings updated.")
            return redirect("water:admin_panel")
        return render(request, "water/admin_reminder_config.html", {"form": form})


@method_decorator(user_passes_test(_is_staff), name="dispatch")
class AdminUserListView(View):
    def get(self, request):
        users = User.objects.all().order_by("id")
        return render(request, "water/admin_users.html", {"users": users})


@method_decorator(user_passes_test(_is_staff), name="dispatch")
class AdminUserCreateView(View):
    def get(self, request):
        form = AdminUserCreateForm()
        return render(request, "water/admin_user_form.html", {"form": form})

    def post(self, request):
        form = AdminUserCreateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "User created successfully.")
            return redirect("water:admin_users")
        return render(request, "water/admin_user_form.html", {"form": form})


@method_decorator(user_passes_test(_is_staff), name="dispatch")
class AdminUserUpdateView(View):
    def get(self, request, pk):
        user_obj = get_object_or_404(User, pk=pk)
        form = AdminUserUpdateForm(instance=user_obj)
        return render(
            request, "water/admin_user_form.html", {"form": form, "edit_user": user_obj}
        )

    def post(self, request, pk):
        user_obj = get_object_or_404(User, pk=pk)
        form = AdminUserUpdateForm(request.POST, instance=user_obj)
        if form.is_valid():
            form.save()
            messages.success(request, "User updated successfully.")
            return redirect("water:admin_users")
        return render(
            request, "water/admin_user_form.html", {"form": form, "edit_user": user_obj}
        )


@method_decorator(user_passes_test(_is_staff), name="dispatch")
class AdminUserDeleteView(View):
    def get(self, request, pk):
        user_obj = get_object_or_404(User, pk=pk)
        return render(request, "water/admin_user_confirm_delete.html", {"edit_user": user_obj})

    def post(self, request, pk):
        user_obj = get_object_or_404(User, pk=pk)
        if user_obj == request.user:
            messages.error(request, "You cannot delete your own account.")
            return redirect("water:admin_users")
        user_obj.delete()
        messages.success(request, "User deleted successfully.")
        return redirect("water:admin_users")


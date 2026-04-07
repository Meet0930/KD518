from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Roommate, BottleFillEntry, ReminderConfig


class RoommateForm(forms.ModelForm):
    class Meta:
        model = Roommate
        fields = ["name", "email", "user"]


class BottleFillForm(forms.ModelForm):
    roommate = forms.ModelChoiceField(
        queryset=Roommate.objects.none(),
        help_text="Select person name who filled the bottles.",
    )
    quantity = forms.TypedChoiceField(
        choices=[(1, "1 bottle"), (2, "2 bottles")],
        coerce=int,
        help_text="Only 1 or 2 bottles are allowed.",
    )

    class Meta:
        model = BottleFillEntry
        fields = ["roommate", "quantity"]

    def __init__(self, *args, **kwargs):
        # If roommate is set, non-staff users can only submit for themselves.
        self.request_user = kwargs.pop("request_user", None)
        self.roommate = kwargs.pop("roommate", None)
        super().__init__(*args, **kwargs)
        if self.request_user and self.request_user.is_staff:
            self.fields["roommate"].queryset = Roommate.objects.all()
        elif self.roommate is not None:
            self.fields["roommate"].queryset = Roommate.objects.filter(pk=self.roommate.pk)
            self.fields["roommate"].initial = self.roommate
        else:
            self.fields["roommate"].queryset = Roommate.objects.none()

    def save(self, commit: bool = True) -> BottleFillEntry:
        instance = super().save(commit=False)
        if self.roommate is not None and not instance.roommate_id:
            instance.roommate = self.roommate
        if commit:
            instance.save()
        return instance


class ReminderConfigForm(forms.ModelForm):
    class Meta:
        model = ReminderConfig
        fields = ["reminder_interval_hours"]


class AdminUserCreateForm(UserCreationForm):
    email = forms.EmailField(required=False)

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2", "is_staff", "is_active"]


class AdminUserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["username", "email", "is_staff", "is_active"]


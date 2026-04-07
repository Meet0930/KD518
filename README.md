# Roommate Water Bottle Tracker System

A beginner-friendly Django web app to track **who fills the water bottle**, keep **history**, show **stats**, and send **automatic reminders** if no one fills the bottle for a configured time.

## Features

- Authentication (user login/logout)
- Separate **frontend Admin Panel** (staff-only) at `/panel/`
- Django Admin at `/admin/` (full control: users, roommates, entries)
- Roommate management (admin/staff only)
- Bottle fill entries (quantity + auto timestamp)
- History page with filters (date + roommate)
- Dashboard stats (totals, daily, weekly, most active, next roommate)
- Reminder system via cron job (`send_water_reminders`)

## Setup (Windows PowerShell)

Activate your virtual environment first (your project uses `D:\KD518\django\` as the venv):

```powershell
cd D:\KD518
.\django\Scripts\Activate.ps1
```

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Run migrations:

```powershell
python manage.py migrate
```

Start server:

```powershell
python manage.py runserver
```

## Create accounts

### Admin account (for frontend admin panel + Django admin)

Create a superuser:

```powershell
python manage.py createsuperuser --username Admin --email admin@example.com
```

Use password: `Admin@123` (when prompted).

Admin URLs:

- Frontend Admin Panel: `http://127.0.0.1:8000/panel/login/`
- Django Admin: `http://127.0.0.1:8000/admin/`

### Normal user account

Create a regular user (example: `Meet / Meet@123`):

```powershell
python manage.py shell
```

```python
from django.contrib.auth.models import User
User.objects.create_user(username="Meet", password="Meet@123")
exit()
```

Important: the admin must link this user to a roommate (Admin Panel → Roommates → Edit).

## Pages

- User login: `/login/`
- Dashboard: `/`
- Add entry: `/entry/add/`
- History: `/history/`
- Frontend Admin Panel: `/panel/`

## Reminder automation (cron)

This project uses `django-crontab` and a management command:

- `python manage.py send_water_reminders`

To install the cron job:

```powershell
python manage.py crontab add
python manage.py crontab show
```

## Email (SMTP)

By default, emails print to the terminal (console backend). To enable SMTP, set environment variables:

- `DJANGO_EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend`
- `DJANGO_EMAIL_HOST=...`
- `DJANGO_EMAIL_PORT=587`
- `DJANGO_EMAIL_HOST_USER=...`
- `DJANGO_EMAIL_HOST_PASSWORD=...`
- `DJANGO_EMAIL_USE_TLS=1`
- `DJANGO_DEFAULT_FROM_EMAIL=no-reply@yourdomain.com`

Then run:

```powershell
python manage.py send_water_reminders
```


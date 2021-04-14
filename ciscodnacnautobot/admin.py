from django.contrib import admin
from .models import Settings


@admin.register(Settings)
class SettingsAdmin(admin.ModelAdmin):
    list_display = ("hostname", "username", "password", "version", "verify", "status")
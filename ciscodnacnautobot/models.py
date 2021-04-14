from django.db import models
from django.urls import reverse
import uuid
from nautobot.utilities.querysets import RestrictedQuerySet
from nautobot.core.models import BaseModel


class Settings(BaseModel):
    hostname = models.CharField(max_length=2000, unique=True, blank=True, null=True)
    username = models.CharField(max_length=100)
    password = models.CharField(max_length=100)
    version = models.CharField(max_length=10)
    verify = models.BooleanField(default=False)
    status = models.BooleanField(default=True)
    objects = RestrictedQuerySet.as_manager()

    class Meta:
        app_label = "ciscodnacnautobot"
        ordering = ["hostname"]

    def __str__(self):
        return self.hostname

    def get_absolute_url(self):
        return reverse("plugins:ciscodnacnautobot:settings")

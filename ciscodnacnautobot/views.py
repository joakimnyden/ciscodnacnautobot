import platform
from django.conf import settings
from django.http import Http404, HttpResponseServerError, JsonResponse
from django.views.defaults import ERROR_500_TEMPLATE_NAME
from django.template import loader
from django.urls import reverse
from django.shortcuts import get_object_or_404, render, redirect
from django.views.generic import View
from nautobot.utilities.forms import ConfirmationForm
from nautobot.tenancy.models import Tenant
from nautobot.core.views import generic
from .models import Settings
from .forms import SettingsForm
from .tables import SettingsTable
from .ciscodnac.data import Data
from .ciscodnac.nautobot import Nautobot
from .ciscodnac.utilities import System


class SettingsView(generic.ObjectListView):
    """
    Cisco DNA Center Settings
    """
    
    queryset = Settings.objects.all()
    table = SettingsTable
    template_name = "ciscodnacnautobot/settings.html"


class SettingsEdit(generic.ObjectEditView):
    """
    Add/Edit Cisco DNA Center Settings
    """

    queryset = Settings.objects.all()
    model_form = SettingsForm
    template_name = "ciscodnacnautobot/settings_edit.html"


class SettingsDelete(generic.ObjectDeleteView):
    """
    Delete Cisco DNA Center Settings
    """

    queryset = Settings.objects.all()


class SettingsDeleteBulk(generic.BulkDeleteView):
    """
    Delete multiple Cisco DNA Center Settings
    """

    queryset = Settings.objects.all()
    table = SettingsTable


class StatusView(View):
    """
    Plugin Status Dashboard
    """

    def get(self, request):
        # Check that Nautobot tag exists for Cisco DNA Center
        Nautobot.Sync.tags(task="system")

        # Check that Cisco DNA Center Settings exists
        if Settings.objects.filter().exists() is False:
            return redirect("/plugins/ciscodnacnautobot/settings/")

        data = Data.status()
        return render(
            request,
            "ciscodnacnautobot/status.html",
            {
                "dnac": data["dnac"],
                "nautobot": request.build_absolute_uri("/"),
                "nautobot_sites": data["nautobot"]["sites"],
                "nautobot_devices": data["nautobot"]["devices"],
                "nautobot_tenants": data["nautobot"]["tenants"],
            },
        )


class SyncFull(View):
    """
    Sync Cisco DNA Center
    """

    def get(self, request, **kwargs):
        # Check that we have Cisco DNA Center settings
        if Settings.objects.filter().exists() is False:
            return redirect("/plugins/ciscodnacnautobot/settings/")

        # Check if RQ workers are running
        if System.RQ.status() is False:
            template = loader.get_template(ERROR_500_TEMPLATE_NAME)
            error_msg = """
            Addtional Workers not running for Background Tasks.
            Verify that rqworker is running.
            """
            return HttpResponseServerError(
                template.render(
                    {
                        "error": error_msg,
                        "exception": "ciscodnacnautobot plugin - RQ",
                        "nautobot_version": settings.VERSION,
                        "python_version": platform.python_version(),
                    }
                )
            )

        # Run Sync as Background Job in RQ
        data = Data.sync_full(**kwargs)
        if "id" in kwargs:
            if data is None:
                raise Http404()
            return render(
                request,
                "ciscodnacnautobot/sync_full.html",
                {
                    "data": data,
                },
            )
        return render(
            request,
            "ciscodnacnautobot/loading_job.html",
            {
                "data": data,
            },
        )


class SyncFullFailed(View):
    """
    Display failed RQ Job
    """

    def get(self, request, id):
        data = Data.job_status(id)
        return render(
            request,
            "ciscodnacnautobot/sync_full_failed.html",
            {
                "data": data,
            },
        )


class JobStatus(View):
    """
    Check RQ Job Status
    """

    def get(self, request, id):
        data = Data.job_status(id)
        if data is None:
            raise Http404()
        return JsonResponse(data)


class DeviceView(View):
    """
    Cisco DNA Center Devices
    """

    def get(self, request, **kwargs):
        data = Data.devices(**kwargs)
        return render(
            request,
            "ciscodnacnautobot/devices.html",
            {
                "data": data,
            },
        )


class SyncDevices(View):
    """
    Sync Cisco DNA Center Devices
    """

    def get(self, request, **kwargs):
        data = Data.sync_devices(**kwargs)
        return render(
            request,
            "ciscodnacnautobot/sync_devices.html",
            {
                "data": data,
            },
        )


class SitesView(View):
    """
    Cisco DNA Center Sites
    """

    def get(self, request, **kwargs):
        data = Data.sites(**kwargs)
        return render(
            request,
            "ciscodnacnautobot/sites.html",
            {
                "data": data,
            },
        )


class SyncSites(View):
    """
    Sync Cisco DNA Center Sites
    """

    def get(self, request, **kwargs):
        data = Data.sync_sites(**kwargs)
        return render(
            request,
            "ciscodnacnautobot/sync_sites.html",
            {
                "data": data,
            },
        )


class PurgeTenant(View):
    """
    Purge Nautobot Tenants related to Cisco DNA Center
    """

    def get(self, request, **kwargs):

        # Verify that the Tenant exists in Nautobot
        tenant = get_object_or_404(Tenant, pk=kwargs["pk"], tags=System.PluginTag.get())

        # Confirm deletion
        form = ConfirmationForm(initial=request.GET)
        return render(
            request,
            "generic/object_delete.html",
            {
                "obj": tenant,
                "form": form,
                "return_url": reverse("plugins:ciscodnacnautobot:purge_tenant", args=(kwargs["pk"],)),
            },
        )

    def post(self, request, **kwargs):

        # Delete Tenant in Nautobot
        data = Data.purge_tenant(**kwargs)
        return render(
            request,
            "ciscodnacnautobot/purge_tenant.html",
            {
                "data": data,
            },
        )

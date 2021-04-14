from . import CiscoDNAC
from cacheops import cache, CacheMiss
from nautobot.dcim.models import Site, Device
from nautobot.tenancy.models import Tenant
from nautobot.extras.models import Status 
from django_rq import get_queue, job
from ..models import Settings
from .nautobot import Nautobot
from .utilities import System


@job("default")
def full_sync(**kwargs):
    """
    RQ Background Task for Syncing Cisco DNA Center Instances
    """
    data = {}

    # Sync all func from Cisco DNA Center
    sites = Data.sync_sites(**kwargs)
    devices = Data.sync_devices(**kwargs)

    # Count the synced items
    for tenant in sites:
        data[tenant] = {}
        Nautobot.Purge.database(tenant=tenant, type="devices", data=devices[tenant])
        Nautobot.Purge.database(tenant=tenant, type="sites", data=sites[tenant])
    for tenant in sites:
        data[tenant]["sites"] = len(sites[tenant])
    for tenant in devices:
        data[tenant]["devices"] = len(devices[tenant])

    # Return data as results for the job
    return data


class Data:
    def status():
        """
        Plugin Status Dashboard
        """

        # Create Cisco DNA Center API Instances
        data = {}
        tenants = CiscoDNAC()
        data["dnac"] = {}

        # Get local settings
        for tenant in Settings.objects.all().nocache():
            data["dnac"][tenant.hostname] = {}
            data["dnac"][tenant.hostname]["id"] = tenant.id
            data["dnac"][tenant.hostname]["sites"] = None
            data["dnac"][tenant.hostname]["devices"] = None
        # Get API status per Cisco DNA Center

        for k, v in tenants.dnac_status.items():
            data["dnac"][k]["api"] = v

        # Get data from Cisco DNA Center
        for tenant, dnac in tenants.dnac.items():
            data["dnac"][tenant]["sites"] = tenants.sites_count(tenant=dnac)
            data["dnac"][tenant]["devices"] = 0
            for device in tenants.devices(tenant=dnac):
                if device.deviceSupportLevel == "Supported":
                    data["dnac"][tenant]["devices"] += 1

        # Gather data from Nautobot
        data["nautobot"] = {}
        dnac_tag = System.PluginTag.get()
        data["nautobot"]["sites"] = len(Site.objects.filter(tags=dnac_tag))
        data["nautobot"]["devices"] = len(Device.objects.filter(tags=dnac_tag))
        data["nautobot"]["tenants"] = {}

        # Gather Tenants that is related to Cisco DNA Center
        for tenant in Tenant.objects.filter(tags=dnac_tag):
            managed = False
            if str(tenant) in [*data["dnac"]]:
                managed = True
            data["nautobot"]["tenants"][tenant.name] = {
                "id": tenant.id,
                "description": tenant.description,
                "created": tenant.created,
                "managed": managed,
            }
        return data

    def devices(**kwargs):
        """
        Cisco DNA Center Instance Devices
        """

        # Gather all devices from Cisco DNA Center Inventory (no sync)
        data = {}
        tenants = CiscoDNAC(**kwargs)
        for tenant, dnac in tenants.dnac.items():
            data[tenant] = tenants.devices(tenant=dnac)
        return data

    def sites(**kwargs):
        """
        Cisco DNA Center Sites Devices
        """

        # Gather all sites from Cisco DNA Center Network Designs (no sync)
        data = {}
        tenants = CiscoDNAC(**kwargs)
        for tenant, dnac in tenants.dnac.items():
            results = []
            for site in tenants.sites(tenant=dnac):

                # Get addtional data about the location
                if len(site.additionalInfo) != 0:
                    for additionalInfo in site.additionalInfo:
                        if "Location" in additionalInfo["nameSpace"]:
                            result = {
                                "name": site.name,
                                "siteNameHierarchy": site.siteNameHierarchy,
                                "type": additionalInfo["attributes"]["type"],
                                "country": additionalInfo["attributes"]["country"],
                            }
                else:
                    result = {
                        "name": site.name,
                        "siteNameHierarchy": site.siteNameHierarchy,
                        "type": None,
                        "country": None,
                    }
                results.append(result)
            results = sorted(results, key=lambda k: k["siteNameHierarchy"], reverse=False)
            data[tenant] = results
        return data

    @classmethod
    def sync_full(cls, **kwargs):
        """
        Sync Cisco DNA Center as RQ job
        """
        data = {}

        # Get RQ queue
        queue = get_queue("default")

        # Get RQ Job ID and display results
        if "id" in kwargs:
            data = queue.fetch_job(str(kwargs["id"]))
            if data is None:
                return None
            return data.result

        # Check if ongoing RQ Job is ongoing
        try:
            job = cache.get("ciscodnacnautobot_bg")
        except CacheMiss:
            # If not, start full sync task
            job = full_sync.delay(**kwargs)
            cache.set("ciscodnacnautobot_bg", job.id, timeout=600)

        # Get Job Status
        j = queue.fetch_job(cache.get("ciscodnacnautobot_bg"))
        if "finished" == j.get_status():
            # Start again, if cache expired
            job = full_sync.delay(**kwargs)
            cache.set("ciscodnacnautobot_bg", job.id, timeout=600)
        data["id"] = str(j.id)
        data["task"] = str(j.func_name)
        return data

    @classmethod
    def sync_sites(cls, **kwargs):
        """
        Sync Cisco DNA Center Sites
        """

        # Sync mandatory tag for Cisco DNA Center in Nautobot
        dnac_tag = Nautobot.Sync.tags(task="system")

        # Gather all sites in Cisco DNA Center Network Designs
        data = {}
        tenants = CiscoDNAC(**kwargs)
        for tenant, dnac in tenants.dnac.items():
            results = []
            # Sync Cisco DNA Center Tenant
            Nautobot.Sync.tenants(task="system", tenant=tenant, slug=tenant.replace(".", "-"))
            # Add tag to Cisco DNA Center Tenant
            Nautobot.Sync.tags(
                task="update",
                model="tenant",
                filter=tenant,
                tag=dnac_tag,
            )
            for site in tenants.sites(tenant=dnac):
                # Sync Site
                # Unique name for `Global` as it can't be duplicate in Nautobot
                if site.siteNameHierarchy == "Global":
                    suffix = site.id.split("-")
                    site.siteNameHierarchy = "{} {}".format(site.siteNameHierarchy, suffix[0])

                # Use Cisco DNA Center UUID for Site as Slug
                site.slug = site.id
                site.sync = Nautobot.Sync.site(tenant=tenant, site=site)

                # Add tag to Site
                Nautobot.Sync.tags(
                    task="update",
                    model="site",
                    filter=site.siteNameHierarchy,
                    tag=dnac_tag,
                )

                site.status = "Active"
                site.status_label = "success"
                result = {
                    "name": site.name,
                    "status": site.status,
                    "status_label": site.status_label,
                    "slug": site.slug,
                    "sync_status": site.sync[1],
                }
                results.append(result)

            # If site is removed in Cisco DNA Center, then remove in Nautobot
            Nautobot.Purge.database(tenant=tenant, type="sites", data=results)
            results = sorted(results, key=lambda k: k["name"], reverse=False)
            data[tenant] = results
        return data

    @classmethod
    def sync_devices(cls, **kwargs):
        """
        Sync Cisco DNA Center Devices
        """

        # Sync mandatory tag for Cisco DNA Center
        dnac_tag = Nautobot.Sync.tags(task="system")

        # Gather all devices in Cisco DNA Center Inventory
        data = {}
        tenants = CiscoDNAC(**kwargs)
        for tenant, dnac in tenants.dnac.items():
            results = []

            # Nautobot sites mandatory to assign sites
            if System.Check.sites(tenant=tenant) is False:
                data[tenant] = [{"sync_status": "Error: Sync sites first"}]
                continue
            # Map Devices (Serial) against Site UUID
            site_members = CiscoDNAC.devices_to_sites(tenant=dnac)

            # Get devices from Cisco DNA Center
            for device in tenants.devices(tenant=dnac):

                # Sync Cisco DNA Center Tenant
                Nautobot.Sync.tenants(task="system", tenant=tenant, slug=tenant.replace(".", "-"))
                Nautobot.Sync.tags(
                    task="update",
                    model="tenant",
                    filter=tenant,
                    tag=dnac_tag,
                )

                # Check that the device is supported in Cisco DNA Center
                if device.deviceSupportLevel == "Supported":

                    # Sync Manufacture
                    device.manufacture = device.type.split()[0]
                    device.manufacture = Nautobot.Sync.manufacturer(manufacture=device.manufacture, tenant=tenant)

                    # Sync Device Types
                    slug = System.Slug.create(device.family)
                    device.family_type = Nautobot.Sync.devicetype(
                        manufacture=device.manufacture,
                        model=device.family,
                        slug=slug,
                        tenant=tenant,
                    )
                    # Add tag to devicetype
                    Nautobot.Sync.tags(
                        task="update",
                        model="devicetype",
                        filter=slug,
                        tag=dnac_tag,
                    )

                    # Sync Device Roles
                    slug = System.Slug.create(device.role)
                    device.role = Nautobot.Sync.devicerole(role=device.role, slug=slug, tenant=tenant)

                    # Sync Device IP Address
                    device.primary_ip4 = Nautobot.Sync.ipaddress(
                        tenant=tenant,
                        address=device.managementIpAddress,
                        hostname=device.hostname,
                    )
                    # Add tags to IP Address
                    Nautobot.Sync.tags(
                        task="update",
                        model="ipaddress",
                        filter=device.primary_ip4,
                        tag=dnac_tag,
                    )
                    # Device Site Location
                    device.site = Site.objects.get(
                        slug=site_members[device.serialNumber],
                        tenant=Tenant.objects.get(name=tenant).id,
                    )

                    # Check if devices is reachable from Cisco DNA Center
                    if device.reachabilityStatus == "Reachable":
                        device.status = Status.objects.get(slug="active")
                        device.status_label = "success"
                    else:
                        device.status = Status.objects.get(slug="failed")
                        device.status_label = "danger"

                    # Sync Device and get status
                    sync_status = Nautobot.Sync.device(tenant=tenant, device=device)
                    # Add tag to device
                    Nautobot.Sync.tags(
                        task="update",
                        model="device",
                        filter=device.serialNumber,
                        tag=dnac_tag,
                    )
                    result = {
                        "name": device.hostname,
                        "status": device.status,
                        "status_label": device.status_label,
                        "role": device.role,
                        "type": device.family_type,
                        "site": device.site,
                        "primary_ip4": device.primary_ip4,
                        "serial": device.serialNumber,
                        "sync_status": sync_status[1],
                    }
                    results.append(result)

            # If device is removed in Cisco DNA Center, then remove in Nautobot
            Nautobot.Purge.database(tenant=tenant, type="devices", data=results)

            results = sorted(results, key=lambda k: k["name"], reverse=False)
            data[tenant] = results
        return data

    def purge_tenant(**kwargs):
        """
        Remove Nautobot Tenant that is related to Cisco DNA Center
        """
        results = Nautobot.Purge.tenant(**kwargs)
        return results

    @staticmethod
    def job_status(id):
        """
        Get RQ Job Status
        """

        # Get RQ queue
        data = {}
        queue = get_queue("default")
        # Get Job Id data
        j = queue.fetch_job(str(id))
        if j is None:
            # No job exists with that `id`
            return None
        data["id"] = str(id)
        data["task"] = str(j.func_name)
        data["status"] = str(j.get_status())
        data["result"] = str(j.result)
        data["exception"] = str(j.exc_info)
        return data

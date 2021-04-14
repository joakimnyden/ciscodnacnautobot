#from extras.plugins import PluginMenuButton, PluginMenuItem
from nautobot.extras.plugins import PluginMenuButton, PluginMenuItem
#from utilities.choices import ButtonColorChoices
from nautobot.utilities.choices import ButtonColorChoices


menu_items = (
    PluginMenuItem(
        link="plugins:ciscodnacnautobot:status",
        link_text="Status",
        permissions=["admin"],
        buttons=(
            PluginMenuButton(
                link="plugins:ciscodnacnautobot:sync_full",
                title="Settings",
                icon_class="mdi mdi-all-inclusive",
                color=ButtonColorChoices.BLUE,
                permissions=["admin"],
            ),
            PluginMenuButton(
                link="plugins:ciscodnacnautobot:settings",
                title="Settings",
                icon_class="mdi mdi-cog",
                color=ButtonColorChoices.BLUE,
                permissions=["admin"],
            ),
        ),
    ),
)

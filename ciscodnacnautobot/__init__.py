from nautobot.extras.plugins import PluginConfig

class CiscoDNACenterConfig(PluginConfig):
    version = "1.0"
    name = "ciscodnacnautobot"
    verbose_name = "Cisco DNA Center Sync Plugin"
    description = "Cisco DNA Center Integration with Nautobot"
    author = "Robert Csapo"
    author_email = "rcsapo@cisco.com"
    required_settings = []
    default_settings = {}
    base_url = "ciscodnacnautobot"
    caching_config = {}


config = CiscoDNACenterConfig

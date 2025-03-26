from yt_dlp_plugins.extractor.getpot import GetPOTProvider, register_provider

import httpx
import os
import subprocess


# def _get_pot() -> str:
#     url = "http://localhost:8081/token"
#     response = httpx.get(url)
#     json = response.json()
#     return json["potoken"]

def _get_pot() -> str:
    print("\n##############################################")
    print("# Running potoken-generator")
    print("##############################################\n")

    cp = subprocess.run(["potoken-generator"], capture_output=True, text=True, check=True)
    stdout = cp.stdout.strip()
    key = "po_token: "
    for line in stdout.splitlines():
        if line.startswith(key):
            return line[len(key):]
    raise ValueError(f"Could not find PO Token in output: {stdout}")

    # po_token: Mnl_G5bRbb5GXH8mwmcB24HURvwdB3ZXzGiLhS6WIXrs0Te8y9vxXlnHZv04MB9OLnFxIyAg9GC6axxzPValtrJehNAiSJAbePy-dDNcgM8exyCgnYPkbodbeyBeYmQZrohuihoKlzPozjGZ0tCiJiyRyOe41ZuohMpi


@register_provider
class MyProviderRH(GetPOTProvider):
   _PROVIDER_NAME = 'myprovider'
   _SUPPORTED_CLIENTS = ('web', )
   
   def _get_pot(self, client, ydl, visitor_data=None, data_sync_id=None, **kwargs):
        # Implement your PO Token retrieval here
        # return 'PO_TOKEN'
        return _get_pot()
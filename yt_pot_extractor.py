from yt_dlp_plugins.extractor.getpot import GetPOTProvider, register_provider

import httpx


# def _get_pot() -> str:
#     url = "http://localhost:8081/token"
#     response = httpx.get(url)
#     json = response.json()
#     return json["potoken"]

def _get_pot() -> str:
    import os
    import subprocess
    

@register_provider
class MyProviderRH(GetPOTProvider):
   _PROVIDER_NAME = 'myprovider'
   _SUPPORTED_CLIENTS = ('web', )
   
   def _get_pot(self, client, ydl, visitor_data=None, data_sync_id=None, **kwargs):
        # Implement your PO Token retrieval here
        # return 'PO_TOKEN'
        return _get_pot()
import os
import sys

print("Checking environment variables...")
proxy_vars = []
for key, value in os.environ.items():
    if 'proxy' in key.lower():
        proxy_vars.append((key, value))

if proxy_vars:
    print(f"Found {len(proxy_vars)} proxy-related environment variables:")
    for key, value in proxy_vars:
        print(f"  {key} = {value}")
else:
    print("No proxy-related environment variables found.")

print("\nChecking sys.modules for requests...")
if 'requests' in sys.modules:
    print("requests module is already loaded")
    import requests
    print(f"requests version: {requests.__version__}")

    # Check requests session defaults
    print("\nChecking requests default settings:")
    print(f"  Session proxies: {requests.Session().proxies}")

    # Check if there are default proxies in requests
    from requests.utils import default_headers
    print(f"  Default headers: {default_headers()}")
else:
    print("requests module not yet loaded")
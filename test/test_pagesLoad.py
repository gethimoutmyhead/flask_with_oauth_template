import requests
from loadMyAppSettings import env as env
import importlib
import pytest

# from 'gunicorn.conf' import certfile as page_publicCert

def test_basePageLoads():
	url = f"https://{env['app_server_url']}"
	try:
		page = requests.get(url, verify=env['publicCert_site'])
		assert page.status_code == 200, f"{url} returned status code {page.status_code}"
	except requests.exceptions.Timeout:
		pytest.fail(f"{url} - The request timed out")
	except requests.exceptions.ConnectionError:
		pytest.fail(f"{url} - Failed to connect to the server")

def test_loginPageRedirects():
	try:
		url = f"https://{env['app_server_url']}/login"
		page = requests.get(url, verify=env['publicCert_site'], allow_redirects=False)
		assert page.status_code == 302, f"login page returns status code {page.status_code}"
	except requests.exceptions.Timeout:
		pytest.fail(f"{url} - The request timed out")
	except requests.exceptions.ConnectionError:
		pytest.fail(f"{url} - Failed to connect to the server")

# def test_httpRedirectsToHTTPS():
# 	url = f"https://{env['app_server_url']}/"
# 	page = requests.get(url, verify=False)
# 	assert page.status_code == 302, f"login page returns status code {page.status_code}"
# 	except requests.exceptions.Timeout:
# 		pytest.fail(f"{url} - The request timed out")
# 	except requests.exceptions.ConnectionError:
# 		pytest.fail(f"{url} - Failed to connect to the server")
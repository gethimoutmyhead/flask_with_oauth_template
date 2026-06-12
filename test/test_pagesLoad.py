import requests
from loadMyAppSettings import env as env
import importlib
import pytest
from bs4 import BeautifulSoup

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

def test_oidcCallbackPage_returnsAPage():
	url = f"https://{env['app_server_url']}/after-authentication"
	try:
		page = requests.get(url, verify=env['publicCert_site'], allow_redirects=True)
		assert page.status_code == 200, f"{url} returned {page.status_code}"
	except requests.exceptions.Timeout:
		pytest.fail(f"{url} - The request timed out")
	except requests.exceptions.ConnectionError:
		pytest.fail(f"{url} - Failed to connect to the server")	

def test_oidcCallbackPage_error_caught():
	url = f"https://{env['app_server_url']}/after-authentication?error=access_denied"
	try:
		page = requests.get(url, verify=env['publicCert_site'], allow_redirects=False)
		checkList = [
			(page.status_code == 200),
			"text/html" in page.headers.get('content-type'),
		]
		assert not (False in checkList), f"{url} returned {page.status_code}, content type {page.headers.get('content-type')} "
	except requests.exceptions.Timeout:
		pytest.fail(f"{url} - The request timed out")
	except requests.exceptions.ConnectionError:
		pytest.fail(f"{url} - Failed to connect to the server")

	soup = BeautifulSoup(page.text, 'html.parser')
	try:
		pageTitle = soup.find('title')
		assert "error" in pageTitle.contents[0]
	except:
		pytest.fail(f"{url} - page title is {pageTitle.contents}")

def test_oidcCallbackPage_stateMissing():
	url = f"https://{env['app_server_url']}/after-authentication?code=roofus"
	try:
		page = requests.get(url, verify=env['publicCert_site'], allow_redirects=False)
		checkList = [
			page.status_code == 200,
			"text/html" in page.headers.get('content-type'),
		]
		assert not (False in checkList), f"{url} returned {page.status_code}, content type {page.headers.get('content-type')} "
	except requests.exceptions.Timeout:
		pytest.fail(f"{url} - The request timed out")
	except requests.exceptions.ConnectionError:
		pytest.fail(f"{url} - Failed to connect to the server")

	soup = BeautifulSoup(page.text, 'html.parser')
	try:
		pageTitle = soup.find('title')
		assert "error" in pageTitle.contents[0]
	except:
		pytest.fail(f"{url} - page title is {pageTitle.get('contents')}")

# def test_httpRedirectsToHTTPS():
# 	url = f"https://{env['app_server_url']}/"
# 	page = requests.get(url, verify=False)
# 	assert page.status_code == 302, f"login page returns status code {page.status_code}"
# 	except requests.exceptions.Timeout:
# 		pytest.fail(f"{url} - The request timed out")
# 	except requests.exceptions.ConnectionError:
# 		pytest.fail(f"{url} - Failed to connect to the server")
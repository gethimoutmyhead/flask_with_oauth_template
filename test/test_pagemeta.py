from bs4 import BeautifulSoup
import requests
from loadMyAppSettings import env as env
import pytest

def test_pageHasMetaTags():
	url = f"https://{env['app_server_url']}"
	try:
		page = requests.get(url, verify=env['publicCert_site'])
		# assert page.status_code == 200, f"{url} returned status code {page.status_code}"
		soup = BeautifulSoup(page.text, 'html.parser')
		metaTags = soup.find_all('meta')
		assert len(metaTags) > 0, f"{url} has no meta tags"
	except requests.exceptions.Timeout:
		pytest.fail(f"{url} - The request timed out")
	except requests.exceptions.ConnectionError:
		pytest.fail(f"{url} - Failed to connect to the server")

def test_pageHasAnAppName():
	url = f"https://{env['app_server_url']}"
	try:
		page = requests.get(url, verify=env['publicCert_site'])
		# assert page.status_code == 200, f"{url} returned status code {page.status_code}"
		soup = BeautifulSoup(page.text, 'html.parser')
		metaTags = soup.find_all('meta')
		appName_metaTag = filter(lambda tag: tag.get('name') =='application-name', metaTags)

		assert len([*appName_metaTag]) > 0, f"{url} has no name"
	except requests.exceptions.Timeout:
		pytest.fail(f"{url} - The request timed out")
	except requests.exceptions.ConnectionError:
		pytest.fail(f"{url} - Failed to connect to the server")	

def test_appNameIsCannculator():
	url = f"https://{env['app_server_url']}"
	try:
		page = requests.get(url, verify=env['publicCert_site'])
		# assert page.status_code == 200, f"{url} returned status code {page.status_code}"
		soup = BeautifulSoup(page.text, 'html.parser')
		metaTags = soup.find_all('meta')
		metaTags_appName = [*filter(lambda tag: tag.get('name') =='application-name', metaTags)]
		metaTags_appName_en = [*filter(lambda tag: tag.get('lang') == 'en', metaTags_appName)]
		appName = metaTags_appName_en[0].get('content')

		assert 'Cannculator' in appName, f"wrong name - {url} application Name is {appName}"
	except requests.exceptions.Timeout:
		pytest.fail(f"{url} - The request timed out")
	except requests.exceptions.ConnectionError:
		pytest.fail(f"{url} - Failed to connect to the server")	
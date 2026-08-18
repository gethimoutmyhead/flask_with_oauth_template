from bs4 import BeautifulSoup
import requests
from loadMyAppSettings import flaskAppSettings
import pytest
from itertools import repeat, compress
import json

fileToLoad=flaskAppSettings['app_defaultPageMeta_jsonfile']
with open(fileToLoad, "r", encoding='utf-8') as file:
	listOfDicts_defaultPageMeta = json.load(file)


def test_pageDefaultTagsSet():
	url = f"https://{flaskAppSettings['app_server_url']}"
	try:
		page = requests.get(url, verify=flaskAppSettings['publicCert_site'])
		# assert page.status_code == 200, f"{url} returned status code {page.status_code}"
		soup = BeautifulSoup(page.text, 'html.parser')
		metaTags = soup.find_all('meta')
		assert len(metaTags) > 0, f"{url} has no meta tags"
	except requests.exceptions.Timeout:
		pytest.fail(f"{url} - The request timed out")
	except requests.exceptions.ConnectionError:
		pytest.fail(f"{url} - Failed to connect to the server")

	listOfDicts_pageMetaAttrs = [dict(tag.attrs) for tag in metaTags]

	targetPresent = lambda targetMeta, meta_attrList: any(attrs == targetMeta for attrs in meta_attrList)

	checklist_defaultTagPresent = [*map(targetPresent, listOfDicts_defaultPageMeta, repeat(listOfDicts_pageMetaAttrs))]
	checklist_defaultTagMissing = [not check for check in checklist_defaultTagPresent]
	assert (not False in checklist_defaultTagPresent), f"following meta Tags not found - {list(compress(listOfDicts_defaultPageMeta, checklist_defaultTagMissing))}"


# def test_pageHasAnAppName():
# 	url = f"https://{flaskAppSettings['app_server_url']}"
# 	try:
# 		page = requests.get(url, verify=flaskAppSettings['publicCert_site'])
# 		# assert page.status_code == 200, f"{url} returned status code {page.status_code}"
# 		soup = BeautifulSoup(page.text, 'html.parser')
# 		metaTags = soup.find_all('meta')
# 		appName_metaTag = filter(lambda tag: tag.get('name') =='application-name', metaTags)

# 		assert len([*appName_metaTag]) > 0, f"{url} has no name"
# 	except requests.exceptions.Timeout:
# 		pytest.fail(f"{url} - The request timed out")
# 	except requests.exceptions.ConnectionError:
# 		pytest.fail(f"{url} - Failed to connect to the server")	


# def test_appNameIsCannculator():
# 	url = f"https://{flaskAppSettings['app_server_url']}"
# 	try:
# 		page = requests.get(url, verify=flaskAppSettings['publicCert_site'])
# 		# assert page.status_code == 200, f"{url} returned status code {page.status_code}"
# 		soup = BeautifulSoup(page.text, 'html.parser')
# 		metaTags = soup.find_all('meta')
# 		metaTags_appName = [*filter(lambda tag: tag.get('name') =='application-name', metaTags)]
# 		metaTags_appName_en = [*filter(lambda tag: tag.get('lang') == 'en', metaTags_appName)]
# 		appName = metaTags_appName_en[0].get('content')

# 		assert 'Cannculator' in appName, f"wrong name - {url} application Name is {appName}"
# 	except requests.exceptions.Timeout:
# 		pytest.fail(f"{url} - The request timed out")
# 	except requests.exceptions.ConnectionError:
# 		pytest.fail(f"{url} - Failed to connect to the server")	
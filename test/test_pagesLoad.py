import requests
from loadMyAppSettings import env as env
import importlib
import pytest
from bs4 import BeautifulSoup

# from 'gunicorn.conf' import certfile as page_publicCert
URLsToCheck = []
URLsToCheck.append({"pageName": ''})
URLsToCheck.append({"pageName": 'guest-user'})
URLsToCheck.append({"pageName": 'onlytheauth'})
URLsToCheck.append({"pageName": 'login', "expectedResponse": 302, "allow_redirects":False})
URLsToCheck.append({"pageName": 'after-authentication', "expectedResponse": 302, "allow_redirects": False})

@pytest.mark.parametrize("testConditions", URLsToCheck)
def test_expectedURLResponse(testConditions):
	str_baseURL = env.get('app_server_url','not set')
	try:
		str_url = f"https://{str_baseURL}/{testConditions['pageName']}"
	except:
		pytest.fail(f"no pageName set\n base URL {str_baseURL}\n received {testConditions}")

	int_expectedStatusCode = testConditions.get('expectedResponse', 200)
	bool_redirectIsOK = testConditions.get('allow_redirects', True)
	str_contentType = testConditions.get('content-type', 'text/html')

	try:
		page = requests.get(str_url, verify=env['publicCert_site'], allow_redirects=bool_redirectIsOK)
	except requests.exceptions.Timeout:
		pytest.fail(f"{str_url} - The request timed out")
	except requests.exceptions.ConnectionError:
		pytest.fail(f"{str_url} - Failed to connect to the server")
	except Exception as e:
		pytest.fail(f"Unexpected error {e}")

	checkList = [
		page.status_code == int_expectedStatusCode,
		str_contentType in page.headers.get('content-type')
	]
	str_errorResponse = (
		f"{str_url} returned {page.status_code}{' :CORRECT' if checkList[0] else ' :expected '+ str(int_expectedStatusCode)}\n"
		f"content type {page.headers.get('content-type')}{' :CORRECT' if checkList[1] else ' :expected '+ str_contentType}"
	)
	assert not (False in checkList), str_errorResponse
	

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
	metaTags = soup.find_all('meta')
	metaTag_descriptions = [*filter(lambda tag: tag.get('name') =='description', metaTags)]
	metaTag_description_ta = [*filter(lambda tag: tag.get('lang') == 'ta', metaTag_descriptions)]
	assert len(metaTag_description_ta) > 0, f"{url} - no description Meta in Tamil"
	assert "ஓட்டப் பிழை" in metaTag_description_ta[0].get('content'), f"{url} - no error, description - {metaTag_description_ta[0].get('content')} "

def test_oidcCallbackPage_ArgumentMissing():
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

	metaTags = soup.find_all('meta')
	metaTag_descriptions = [*filter(lambda tag: tag.get('name') =='description', metaTags)]
	metaTag_description_ta = [*filter(lambda tag: tag.get('lang') == 'ta', metaTag_descriptions)]
	assert len(metaTag_description_ta) > 0, f"{url} - no description Meta in Tamil"
	assert "ஓட்டப் பிழை" in metaTag_description_ta[0].get('content'), f"{url} - no error, description - {metaTag_description_ta[0].get('content')} "
	# except:
	# 	pytest.fail(f"{url} - description is {metaTag_description_en[0].get('content')}")

# def test_httpRedirectsToHTTPS():
# 	url = f"https://{env['app_server_url']}/"
# 	page = requests.get(url, verify=False)
# 	assert page.status_code == 302, f"login page returns status code {page.status_code}"
# 	except requests.exceptions.Timeout:
# 		pytest.fail(f"{url} - The request timed out")
# 	except requests.exceptions.ConnectionError:
# 		pytest.fail(f"{url} - Failed to connect to the server")
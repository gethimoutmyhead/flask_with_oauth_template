from playwright.sync_api import sync_playwright, Page, BrowserContext
import pytest
from pytest_playwright.pytest_playwright import CreateContextCallback
from loadMyAppSettings import flaskAppSettings, authServerSettings, pyApp_auth0Settings
import flaskCookieMaker
import requests, jwt

url_for_oidcserver_metadataURL = f"{authServerSettings['oidc_authserver']}/.well-known/openid-configuration"
request_oidcserver_metadata = requests.get(url_for_oidcserver_metadataURL)
oidcserver_metadata = request_oidcserver_metadata.json()
oidc_jwksClient = jwt.PyJWKClient(oidcserver_metadata["jwks_uri"])
accessToken_jwksClient = jwt.PyJWKClient(f"{authServerSettings['oidc_authserver']}/.well-known/jwks.json")
oidc_tokenSigningAlgos = oidcserver_metadata['id_token_signing_alg_values_supported']

@pytest.fixture(scope='session')
def loggedInState():
	pw = sync_playwright().start()
	browser = pw.firefox.launch(headless=False)
	page = browser.new_page()
	page.goto(f"https://{flaskAppSettings['app_server_url']}/login?login_hint=lazysummers@duck.com")
	breakpoint()
	loggedState = page.context.storage_state()
	browser.close()
	pw.stop()

	return loggedState

def test_validateAppCookies(loggedInState):
	appCookie_domain = flaskAppSettings['app_server_url'].split(':')[0]

	appCookie = [*filter(lambda cookie: cookie['domain'] == appCookie_domain, loggedInState['cookies'])]

	assert len(appCookie) > 0, f"expected cookie with domain {flaskAppSettings['app_server_url']}, received {loggedInState}"

	dict_sessionCookieDecoded = flaskCookieMaker.decodeFlaskCookie(flaskAppSettings['app_cookieSigning_secret'], appCookie[0]['value'])
	list_requiredSessionCookieKeys = ['authserver_token']
	
	requiredKeysPresent = set(list_requiredSessionCookieKeys) <= set(dict_sessionCookieDecoded.keys())
	assert requiredKeysPresent, f"session cookie is missing {list_requiredSessionCookieKeys - dict_sessionCookieDecoded.keys()}, has {dict_sessionCookieDecoded.keys()}"

	dict_authServerToken = dict_sessionCookieDecoded['authserver_token']
	list_requiredAuthServerTokenKeys = ['access_token', 'id_token']

	requiredKeysPresent = set(list_requiredAuthServerTokenKeys) <= set(dict_authServerToken.keys())
	assert requiredKeysPresent, f"authServerToken is missing {list_requiredAuthServerTokenKeys - dict_authServerToken.keys()}, has {dict_authServerToken.keys()}"


	list_requiredAccessTokenClaims = ['iss', 'sub', 'aud',f'https://{flaskAppSettings['app_server_url']}/roles']
	list_requiredIdTokenClaims = ['iss', 'sub', 'aud',f'https://{flaskAppSettings['app_server_url']}/roles']

	try:
		signing_key = oidc_jwksClient.get_signing_key_from_jwt(dict_authServerToken['id_token'])
		dict_idTokenDecoded = jwt.decode_complete(
			dict_authServerToken['id_token'],
			key=signing_key,
			audience=authServerSettings['oidc_clientID'],
			algorithms=oidc_tokenSigningAlgos,
			options={"require":list_requiredIdTokenClaims},
			)
	except jwt.MissingRequiredClaimError as e:
		pytest.fail(f"{e}")
	except Exception as e:
		pytest.fail(f'id token failed to decode - {e}')

	try:
		signing_key = accessToken_jwksClient.get_signing_key_from_jwt(dict_authServerToken['access_token'])
		dict_accessTokenDecoded = jwt.decode_complete(
			dict_authServerToken['access_token'],
			key=signing_key,
			audience=f"{authServerSettings['oidc_authserver']}/api/v2/",
			algorithms=['RS256'],
			options={"require":list_requiredAccessTokenClaims},
			)
	except jwt.MissingRequiredClaimError as e:
		pytest.fail(f"{e}")
	except Exception as e:
		pytest.fail(f'access token failed to decode - {e} \n access token {dict_authServerToken["access_token"]}')



def test_loadAuthzPageWithAuthn(loggedInState, new_context):

	context = new_context(storage_state=loggedInState)
	page = context.new_page()

	targetURL = f"https://{flaskAppSettings['app_server_url']}/authenticated"

	response = page.goto(targetURL)
	# assert 3==5, f"{page.content()}"
	assert response.status == 200, f"expected status 200, received {response.status}"

	assert response.url == targetURL, f"expected {targetURL}, received {response.url}"

def test_loadAuthzPageWithWrongRole(loggedInState, new_context):

	context = new_context(storage_state=loggedInState)
	page = context.new_page()

	targetURL = f"https://{flaskAppSettings['app_server_url']}/pharmacist-page"

	response = page.goto(targetURL)
	# assert 3==5, f"{page.content()}"
	assert response.status == 403, f"expected status 403, received {response.status}"

	assert response.url == targetURL, f"expected {targetURL}, received {response.url}"


def test_loadAuthzPageWithCorrectRole(loggedInState, new_context):

	context = new_context(storage_state=loggedInState)
	page = context.new_page()

	targetURL = f"https://{flaskAppSettings['app_server_url']}/doctor-page"

	response = page.goto(targetURL)
	# assert 3==5, f"{page.content()}"
	assert response.status == 200, f"expected status 200, received {response.status}"

	assert response.url == targetURL, f"expected {targetURL}, received {response.url}"

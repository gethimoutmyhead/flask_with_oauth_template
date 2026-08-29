import pytest, pytest_asyncio
from playwright.async_api import Page, Browser, async_playwright
from loadMyAppSettings import flaskAppSettings, authServerSettings, pyApp_auth0Settings
import flaskCookieMaker
import requests, jwt

url_for_oidcserver_metadataURL = f"{authServerSettings['oidc_authserver']}/.well-known/openid-configuration"
request_oidcserver_metadata = requests.get(url_for_oidcserver_metadataURL)
oidcserver_metadata = request_oidcserver_metadata.json()
oidc_jwksClient = jwt.PyJWKClient(oidcserver_metadata["jwks_uri"])
accessToken_jwksClient = jwt.PyJWKClient(f"{authServerSettings['oidc_authserver']}/.well-known/jwks.json")
oidc_tokenSigningAlgos = oidcserver_metadata['id_token_signing_alg_values_supported']

@pytest_asyncio.fixture(scope='session')
async def getLoggedInState():
	async with async_playwright() as pw:
		browser = await pw.firefox.launch(headless=False)
		page = await browser.new_page()
		await page.goto(f"https://{flaskAppSettings['app_server_url']}/login?login_hint=uneven-kennel-quit@duck.com")
		breakpoint()
		# input('login then press enter')
		loggedState = await page.context.storage_state()
		await browser.close()

	return loggedState

@pytest.mark.order(1)
@pytest.mark.asyncio(loop_scope="session")
async def test_validateAppCookies(getLoggedInState):
	loggedInState = getLoggedInState
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

@pytest.mark.order(2)
@pytest.mark.asyncio(loop_scope='session')
async def test_loadMainPage(page: Page):
	targetURL = f"https://{flaskAppSettings['app_server_url']}/authenticated"
	response = await page.goto(targetURL)
	assert response.status == 200,f"{response}"

@pytest.mark.order(3)
@pytest.mark.asyncio(loop_scope='session')
async def test_accessAuthzPageWithAuthn(browser: Browser, getLoggedInState):
	g = await browser.new_context(storage_state=getLoggedInState)
	page = await g.new_page()
	targetURL = f"https://{flaskAppSettings['app_server_url']}/authenticated"
	response = await page.goto(targetURL)
	pageData = await response.text()
	assert response.status == 200,f"expected status 200, received {response} \n {pageData}"

	await g.close()

@pytest.mark.order(4)
@pytest.mark.asyncio(loop_scope='session')
async def test_accessAuthzPageWithWrongRole(browser: Browser, getLoggedInState):
	g = await browser.new_context(storage_state=getLoggedInState)
	page = await g.new_page()
	targetURL = f"https://{flaskAppSettings['app_server_url']}/doctor-page"
	response = await page.goto(targetURL)
	pageData = await response.text()
	assert response.status == 403,f"expected status 403, received {response} \n {pageData}"

	await g.close()

@pytest.mark.order(5)
@pytest.mark.asyncio(loop_scope='session')
async def test_accessAuthzPageWithCorrectRole(browser: Browser, getLoggedInState):
	g = await browser.new_context(storage_state=getLoggedInState)
	page = await g.new_page()

	targetURL = f"https://{flaskAppSettings['app_server_url']}/pharmacist-page"
	response = await page.goto(targetURL)
	pageData = await response.text()
	assert response.status == 200,f"expected status 200, received {response} \n {pageData}"

	targetURL = f"https://{flaskAppSettings['app_server_url']}/allied-health-page"
	response = await page.goto(targetURL)
	pageData = await response.text()
	assert response.status == 200,f"expected status 200, received {response} \n {pageData}"

	await g.close()

@pytest.mark.order(6)
@pytest.mark.asyncio(loop_scope='session')
async def test_logoutFlow(browser: Browser, getLoggedInState):
	g = await browser.new_context(storage_state=getLoggedInState)
	page = await g.new_page()

	targetURL = f"https://{flaskAppSettings['app_server_url']}/logout"
	expectedDestinationURL = f"https://{flaskAppSettings['app_server_url']}/logged_out"
	response = await page.goto(targetURL)
	pageData = await response.text()
	destURL = page.url
	assert response.status == 200,f"expected status 200, received {response} \n {pageData}"
	assert expectedDestinationURL in destURL, f"logout request sent to {destURL}"

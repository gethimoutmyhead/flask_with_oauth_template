from loadMyAppSettings import flaskAppSettings, authServerSettings, pyApp_auth0Settings
import flaskCookieMaker
from user_cred import user_credentials
import httpx
import pytest,pytest_asyncio
from urllib.parse import urlencode
import json
import ssl
from playwright.async_api import Page, Browser, async_playwright
import requests, jwt

userAccountDetails = None
targetRole_name = 'Doctor'
targetRole_id = None

url_for_oidcserver_metadataURL = f"{authServerSettings['oidc_authserver']}/.well-known/openid-configuration"
request_oidcserver_metadata = requests.get(url_for_oidcserver_metadataURL)
oidcserver_metadata = request_oidcserver_metadata.json()
oidc_jwksClient = jwt.PyJWKClient(oidcserver_metadata["jwks_uri"])
accessToken_jwksClient = jwt.PyJWKClient(f"{authServerSettings['oidc_authserver']}/.well-known/jwks.json")
oidc_tokenSigningAlgos = oidcserver_metadata['id_token_signing_alg_values_supported']

@pytest.fixture(scope="session")
def newTestUser():
	return {
		'email':user_credentials['testuser_username'],
		'password': user_credentials['testuser_password'],
	}

@pytest_asyncio.fixture(scope='session')
async def getLoggedInState():
	async with async_playwright() as pw:
		browser = await pw.firefox.launch(headless=False)
		page = await browser.new_page()
		await page.goto(f"https://{flaskAppSettings['app_server_url']}/login?login_hint={user_credentials['testuser_username']}")
		breakpoint()
		# input('login then press enter')
		loggedState = await page.context.storage_state()
		await browser.close()

	return loggedState

@pytest_asyncio.fixture(scope="session")
async def oidc_client():
	url_for_token=f"{authServerSettings['oidc_authserver']}/oauth/token"
	client_id=authServerSettings['oidc_clientID']
	client_secret=authServerSettings['oidc_clientSecret']
	audience=f"{authServerSettings['oidc_authserver']}/api/v2/"
	grant_type="client_credentials"	
	async with httpx.AsyncClient() as client:
		payload =  { 
			'grant_type': grant_type,
			'client_id': client_id,
			'client_secret': client_secret,
			'audience': audience,
			'scope':'create:users delete:users'
  		}
		response = await client.post(url_for_token, data=payload)
		oauth = response.json()
		access_token = oauth.get('access_token')
	headers = {
		'Authorization': f'Bearer {access_token}',
		'Content-Type': 'application/json'
	}

	async with httpx.AsyncClient(headers=headers) as client:
		yield client

@pytest.mark.order(1)
@pytest.mark.asyncio(loop_scope='session')
async def test_makeNewUserWithoutCredentials(newTestUser):
	async with httpx.AsyncClient() as client:

		parameters ={
			"email":newTestUser['email'],
			"password":newTestUser['password'],
			"connection":'Username-Password-Authentication',
			"client_id":authServerSettings['oidc_clientID'],
		}
		url=f"{authServerSettings['oidc_authserver']}/dbconnections/signup"

		response = await client.post(url,data=parameters)
		data = response.json()
		try:
			checklist = [
				response.status_code == 400,
				data['error'] == 'public signup is disabled'
			]
		except Exception as e:
			pytest.fail(f"unexpected error {e} \n {response} \n {data}")
		assert not False in checklist, f"{response.status_code}\n{response.content}"

@pytest.mark.order(2)
@pytest.mark.asyncio(loop_scope='session')
async def test_getUserRoles(oidc_client):
	requestURL = f"{authServerSettings['oidc_authserver']}/api/v2/roles"
	query = {
		'include_totals':'true',
	}

	response = await oidc_client.get(f"{requestURL}?{urlencode(query)}")
	data = response.json()
	try:
		checklist = [
			response.status_code == 200,
			data['total'] > 0,
		]
	except Exception as e:
		pytest.fail(f"unexpected error - {e}")
	assert not False in checklist, f"{response.content}"

	matchingRoles = [*filter(lambda role: role['name'] == targetRole_name, data['roles'])]
	global targetRole_id
	targetRole_id = matchingRoles[0]['id']

@pytest.mark.order(3)
@pytest.mark.asyncio(loop_scope='session')
async def test_checkUserExists(oidc_client, newTestUser):
	# email ='slartibartfast@hitchhiker.com'
	query = {
		'email': newTestUser['email'],
		# 'fields': 'email',
		# 'include_fields':'true',
	}
	url_auth0APIRequest = f"{authServerSettings['oidc_authserver']}/api/v2/users-by-email?{urlencode(query)}"
	response = await oidc_client.get(url_auth0APIRequest)
	data = response.json()

	assert not data, f"matching user for {newTestUser['email']}\n{data}"

@pytest.mark.order(4)
@pytest.mark.asyncio(loop_scope='session')
async def test_createNewUser(oidc_client, newTestUser):
	# email ='slartibartfast@hitchhiker.com'
	payload = {
		'email': newTestUser['email'],
		'connection': 'Username-Password-Authentication',
		'password': newTestUser['password'],
		'app_metadata': {
			'western':'diagnosis',
		},
		'verify_email':False,
		# 'fields': 'email',
		# 'include_fields':'true',
	}
	url_auth0APIRequest = f"{authServerSettings['oidc_authserver']}/api/v2/users"
	response = await oidc_client.post(url_auth0APIRequest, json=payload)
	data = response.json()
	try:
		checklist = [
			response.status_code == 201,
			data['email'] == newTestUser['email'],
		]
	except Exception as e:
		pytest.fail(f"unexpected error {e} \n {data}")
	keyDump = [*map(lambda key: f"{key}:{data[key]}", data.keys())]
	assert not False in checklist, f"matching user for {newTestUser['email']}\n{"\n".join(keyDump)}"
	global userAccountDetails
	userAccountDetails = data

@pytest.mark.order(4)
@pytest.mark.asyncio(loop_scope='session')
async def test_createDuplicate(oidc_client, newTestUser):
	# email ='slartibartfast@hitchhiker.com'
	payload = {
		'email': newTestUser['email'],
		'connection': 'Username-Password-Authentication',
		'password': newTestUser['password'],
		'app_metadata': {
			'horace':'beetroot',
		},
		'verify_email':False,
		# 'fields': 'email',
		# 'include_fields':'true',
	}
	url_auth0APIRequest = f"{authServerSettings['oidc_authserver']}/api/v2/users"
	response = await oidc_client.post(url_auth0APIRequest, json=payload)
	data = response.json()
	try:
		checklist = [
			response.status_code == 409,
			data['error'] == 'Conflict',
			'The user already exists.' in data['message'],

		]
	except Exception as e:
		pytest.fail(f"unexpected error {e} \n {response} \n {data}")
	keyDump = [*map(lambda key: f"{key}:{data[key]}", data.keys())]
	assert not False in checklist, f"tried creating duplicate user {newTestUser['email']}\n{response}{"\n".join(keyDump)}"



@pytest.mark.order(4)
@pytest.mark.asyncio(loop_scope='session')
async def test_addRoleToUser(oidc_client, newTestUser):
	global userAccountDetails, targetRole_id
	response = await oidc_client.post(
		f"{authServerSettings['oidc_authserver']}/api/v2/users/{userAccountDetails['user_id']}/roles",
		json={"roles": [targetRole_id]},
	)
	try:
		checklist = [
			response.status_code == 204,
		]
	except Exception as e:
		pytest.fail(f"unexpected error {e} \n {response} \n {data}")
	assert not False in checklist, f"tried adding user role {targetRole_id} to {newTestUser['email']}{"\n".join(keyDump)}"



@pytest.mark.order(5)
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

@pytest.mark.order(6)
@pytest.mark.asyncio(loop_scope='session')
async def test_loadMainPage(page: Page):
	targetURL = f"https://{flaskAppSettings['app_server_url']}/authenticated"
	response = await page.goto(targetURL)
	assert response.status == 200,f"{response}"

@pytest.mark.order(7)
@pytest.mark.asyncio(loop_scope='session')
async def test_accessAuthzPageWithAuthn(browser: Browser, getLoggedInState):
	g = await browser.new_context(storage_state=getLoggedInState)
	page = await g.new_page()
	targetURL = f"https://{flaskAppSettings['app_server_url']}/authenticated"
	response = await page.goto(targetURL)
	assert response.status == 200,f"{response}"
	assert targetURL in page.url,f"mismatch between requested page {targetURL} and response {page.url}"

	await g.close()

@pytest.mark.order(8)
@pytest.mark.asyncio(loop_scope='session')
async def test_accessAuthzPageWithWrongRole(browser: Browser, getLoggedInState):
	g = await browser.new_context(storage_state=getLoggedInState)
	page = await g.new_page()
	targetURL = f"https://{flaskAppSettings['app_server_url']}/pharmacist-page"

	response = await page.goto(targetURL)
	pageData = await response.text()
	assert response.status == 403,f"expected status 403, received {response} \n {pageData}"

	await g.close()

@pytest.mark.order(9)
@pytest.mark.asyncio(loop_scope='session')
async def test_accessAuthzPageWithCorrectRole(browser: Browser, getLoggedInState):
	g = await browser.new_context(storage_state=getLoggedInState)
	page = await g.new_page()
	targetURL = f"https://{flaskAppSettings['app_server_url']}/doctor-page"

	response = await page.goto(targetURL)
	pageData = await response.text()
	assert response.status == 200,f"expected status 200, received {response} \n {pageData}"
	assert targetURL in page.url,f"mismatch between requested page {targetURL} and response {page.url}"

	targetURL = f"https://{flaskAppSettings['app_server_url']}/allied-health-page"
	response = await page.goto(targetURL)
	pageData = await response.text()
	assert response.status == 200,f"expected status 200, received {response} \n {pageData}"
	assert targetURL in page.url,f"mismatch between requested page {targetURL} and response {page.url}"

	await g.close()

@pytest.mark.order(10)
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


@pytest.mark.order(11)
@pytest.mark.asyncio(loop_scope='session')
async def test_deleteTestUser(oidc_client, newTestUser):
	global userAccountDetails, targetRole_id
	user_id = userAccountDetails['user_id']
	response = await oidc_client.delete(f"{authServerSettings['oidc_authserver']}/api/v2/users/{user_id}")
	
	try:
		checklist = [
			response.status_code == 204,
		]
	except Exception as e:
		pytest.fail(f"unexpected error {e} \n {response}")
	assert not False in checklist, f"tried deleting user {newTestUser['email']} \n {response}"

	query = {
		'email': newTestUser['email'],
	}
	url_auth0APIRequest = f"{authServerSettings['oidc_authserver']}/api/v2/users-by-email?{urlencode(query)}"
	response = await oidc_client.get(url_auth0APIRequest)
	data = response.json()

	assert not data, f"matching user for {newTestUser['email']}\n{data}"	



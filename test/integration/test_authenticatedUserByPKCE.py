from user_cred import user_credentials
from loadMyAppSettings import flaskAppSettings, authServerSettings, pyApp_auth0Settings
import pytest
import requests
from requests import Request as urlFetch
import json
import flaskCookieMaker
from itertools import repeat
from functools import reduce
import jwt
from functions_pyapp_loginByPKCE import get_tokens_pkce

# def test_testUser_credentials_present():
# assert len(user_credentials.keys()) > 5, 'FAIL: no user credentials'

url_for_oidcserver_metadataURL = f"{authServerSettings['oidc_authserver']}/.well-known/openid-configuration"
request_oidcserver_metadata = requests.get(url_for_oidcserver_metadataURL)
oidcserver_metadata = request_oidcserver_metadata.json()
oidc_jwksClient = jwt.PyJWKClient(oidcserver_metadata["jwks_uri"])

accessToken_jwksClient = jwt.PyJWKClient(f"{authServerSettings['oidc_authserver']}/.well-known/jwks.json")
oidc_tokenSigningAlgos = oidcserver_metadata['id_token_signing_alg_values_supported']
oidc_token = dict()

doctorSession = requests.Session()

@pytest.fixture(scope="session")
def oidc_token():

	oidc_token = get_tokens_pkce(
			client_id = pyApp_auth0Settings['oidc_clientID'],
			auth_server_url = pyApp_auth0Settings['oidc_authserver'],
			audience = f"{pyApp_auth0Settings['oidc_authserver']}/api/v2/",
			login_hint = 'lazysummers@duck.com'
		)
	return oidc_token
	

tokensToTest = [
	{
		'test_token': {'nauthserver_token': 'someNonsense'},
		'expected_error_message': 'AppAuthnMissing: authserver token missing from session'
	},
	{
		'test_token': {
			'authserver_token':{
				'id_token':'whisky',
				}
			},
		'expected_error_message': 'AppAuthnERROR: access token not present'
	},
	{
		'test_token': {
			'authserver_token':{
				'access_token':'whisky',
				}
			},
		'expected_error_message': 'AppAuthnERROR: id token not present'
	},
	{
		'test_token': {
			'authserver_token':{
				'access_token':'whisky',
				'id_token':'malt',
				}
			},
		'expected_error_message': 'AppAuthnERROR: id token failed to decode'
	},
]
@pytest.mark.order(3)
@pytest.mark.parametrize("tokenToTest", tokensToTest)
def test_accessAuthzPageWithInvalidTokens(tokenToTest):
	try:
		target_url=f"https://{flaskAppSettings['app_server_url']}/authenticated"
		tokenAsFlaskCookie = flaskCookieMaker.encodeFlaskCookie(flaskAppSettings['app_cookieSigning_secret'],tokenToTest['test_token'])
		sessionCookie = requests.cookies.create_cookie(
				name='session',
				value=tokenAsFlaskCookie,
				domain='127.0.0.1',
				path='/',
				secure=True,
				rest={'HttpOnly': True}
			)
		testSession = requests.Session()
		testSession.cookies.set_cookie(sessionCookie)

	except Exception as e:
		pytest.fail(f"unknown exception, tokenToTest is {tokenToTest['test_token']}\n {e} \n {tokenAsFlaskCookie} \n {sessionCookie}")

	response = testSession.get(f"https://{flaskAppSettings['app_server_url']}/authenticated",verify=flaskAppSettings['publicCert_site'], allow_redirects=False)

	# 1. Assert the response is a redirect.
	assert response.status_code in [301, 302, 303, 307, 308], (
		f"Expected a redirect status code (one of [301, 302, 303, 307, 308]), "
		f"got {response.status_code} instead. "
		f"Response body: {response.text[:500]!r}"
	)
 
	# 2. Assert the expected error header is present with the correct value.
	assert "X-Error-Message" in response.headers, (
		f"Expected 'X-Error-Message' header in response, but it was missing. "
		f"Headers received: {dict(response.headers)}"
	)
 
	assert tokenToTest['expected_error_message'] in response.headers["X-Error-Message"], (
		f"Expected X-Error-Message to be {tokenToTest['expected_error_message']}, "
		f"got {response.headers['X-Error-Message']!r} instead."
	)

@pytest.mark.order(4)
def test_getUserTokens_authenticatedoctorSession(oidc_token):
	# url=f"{authServerSettings['oidc_authserver']}/oauth/token"
	# headers = {
	# 	'content-type': 'application/x-www-form-urlencoded',
	# }
	# data = {
	# 	'grant_type': 'password',
	# 	'username': f'{user_credentials["testuser_username"]}',
	# 	'password': f'{user_credentials["testuser_password"]}',
	# 	'scope': 'openid profile read:current_user',
	# 	'client_id': f'{authServerSettings["oidc_clientID"]}',
	# 	'client_secret': f'{authServerSettings["oidc_clientSecret"]}',
	# 	'audience': f"{authServerSettings['oidc_authserver']}/api/v2/"
	# }

	# response = requests.post(url, headers=headers, data=data)
	# assert response.status_code == 200, f"expected code 200, returned {response.status_code}"

	# oidc_token = json.loads(response.content)
	checkList = [
		len(oidc_token.keys()) > 0,
		'access_token' in oidc_token.keys(),
		'id_token' in oidc_token.keys(),
	]
	assert not False in checkList, f"missing data in oidc_token, contains {oidc_token}"

	authserver_token = {'authserver_token': oidc_token}
	authserver_token_asFlaskCookie = flaskCookieMaker.encodeFlaskCookie(flaskAppSettings['app_cookieSigning_secret'], authserver_token)

	flaskSessionCookie = requests.cookies.create_cookie(
			name='session',
			value=authserver_token_asFlaskCookie,
			domain='127.0.0.1',
			path='/',
			secure=True,
			rest={'HttpOnly': True}
		)

	doctorSession.cookies.set_cookie(flaskSessionCookie)

@pytest.mark.order(5)
def test_accessAuthzPageWithoutAuthn():
	page = requests.get(f"https://{flaskAppSettings['app_server_url']}/authenticated",verify=flaskAppSettings['publicCert_site'], allow_redirects=False)
	assert page.status_code == 302, f'expected redirect, got {page.status_code}'

@pytest.mark.order(6)
def test_confirmSessionCookie():
	cookies = doctorSession.cookies

	cookiesNamedSession = [*filter(lambda cookie: 'session' in cookie.name, cookies)]
	assert len(cookiesNamedSession) > 0, f"cookie dump {cookies}"

	# accessToken_decoded = cookies['session']
	dict_sessionCookieDecoded = flaskCookieMaker.decodeFlaskCookie(flaskAppSettings['app_cookieSigning_secret'], cookiesNamedSession[0].value)
	list_requiredSessionCookieKeys = ['authserver_token']
	
	checklist_sessionCookiesKeys = map(lambda keyToTest, dict: keyToTest in dict.keys(), list_requiredSessionCookieKeys, repeat(dict_sessionCookieDecoded))

	assert not (False in checklist_sessionCookiesKeys), f"session cookie requires {requiredSessionCookieKeys}, got {dict_sessionCookieDecoded.keys()}"


	dict_authServerToken = dict_sessionCookieDecoded['authserver_token']
	list_requiredAuthServerTokenKeys = ['access_token', 'id_token']

	checklist_authServerTokenKeys = map(lambda keyToTest, dict: keyToTest in dict.keys(), list_requiredAuthServerTokenKeys, repeat(dict_authServerToken))

	assert not (False in checklist_authServerTokenKeys), f"authServer key requires {list_requiredAuthServerTokenKeys}, got {dict_authServerToken.keys()}"

	# dict_accessTokenDecoded = flaskCookieMaker.decodeFlaskCookie(flaskAppSettings['app_cookieSigning_secret'], dict_authServerToken['access_token'])
	# dict_idTokenDecoded = flaskCookieMaker.decodeFlaskCookie(flaskAppSettings['app_cookieSigning_secret'], dict_authServerToken['id_token'])

	# list_requiredTokenKeys = ['expires_at']
	# checklist_accessTokenKeys = map(lambda keyToTest, dict: keyToTest in dict.keys(), list_requiredAuthServerTokenKeys, repeat(dict_accessTokenDecoded))

	# assert not (False in checklist_accessTokenKeys), f"access token key requires {list_requiredTokenKeys}, got {dict_accessTokenDecoded.keys()}"

	# signing_key = oidc_jwksClient.get_signing_key_from_jwt(id_token)

	list_requiredAccessTokenClaims = ['iss', 'sub', 'aud',f'https://{flaskAppSettings['app_server_url']}/roles']
	list_requiredIdTokenClaims = ['iss', 'sub', 'aud',f'https://{flaskAppSettings['app_server_url']}/roles']

	try:
		signing_key = oidc_jwksClient.get_signing_key_from_jwt(dict_authServerToken['id_token'])
		dict_idTokenDecoded = jwt.decode_complete(
			dict_authServerToken['id_token'],
			key=signing_key,
			audience=pyApp_auth0Settings['oidc_clientID'],
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


@pytest.mark.order(7)
def test_accessAuthzPageWithAuthn():
	page = doctorSession.get(f"https://{flaskAppSettings['app_server_url']}/authenticated",verify=flaskAppSettings['publicCert_site'], allow_redirects=False)
	assert page.status_code == 200, f'expected page to load, got {page.status_code}\n {page.headers}'


@pytest.mark.order(8)
def test_accessAuthzPageWithWrongRole():
	page = doctorSession.get(f"https://{flaskAppSettings['app_server_url']}/pharmacist-page",verify=flaskAppSettings['publicCert_site'], allow_redirects=False)
	assert page.status_code == 403, f"expected 403 forbidden, got {page.status_code}\n {page.headers}"

@pytest.mark.order(9)
def test_accessAuthzPageWithCorrectRole():
	page = doctorSession.get(f"https://{flaskAppSettings['app_server_url']}/doctor-page",verify=flaskAppSettings['publicCert_site'], allow_redirects=False)
	assert page.status_code == 200, f"expected page to load, got {page.status_code}\n {page.headers}"

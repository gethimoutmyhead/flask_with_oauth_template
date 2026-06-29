from user_cred import user_credentials
from loadMyAppSettings import flaskAppSettings, authServerSettings
import pytest
import requests
from requests import Request as urlFetch
import json
import flaskCookieMaker
from itertools import repeat
import jwt

# def test_testUser_credentials_present():
# assert len(user_credentials.keys()) > 5, 'FAIL: no user credentials'

url_for_oidcserver_metadataURL = f"{authServerSettings['oidc_authserver']}/.well-known/openid-configuration"
request_oidcserver_metadata = requests.get(url_for_oidcserver_metadataURL)
oidcserver_metadata = request_oidcserver_metadata.json()
oidc_jwksClient = jwt.PyJWKClient(oidcserver_metadata["jwks_uri"])

accessToken_jwksClient = jwt.PyJWKClient(f"{authServerSettings['oidc_authserver']}/.well-known/jwks.json")
oidc_tokenSigningAlgos = oidcserver_metadata['id_token_signing_alg_values_supported']


surfSession = requests.Session()

@pytest.mark.order(1)
def test_keysInUserCredentials():
	assert len(user_credentials.keys()) > 0, 'FAIL: no user credentials'

keysToValidate=['testuser_username', 'testuser_password']
@pytest.mark.order(2)
@pytest.mark.parametrize('keyToValidate', keysToValidate)
def test_validateKey(keyToValidate):
	assert keyToValidate in user_credentials.keys(), f"{keyToValidate} not in user_cred"

@pytest.mark.order(3)
def test_getUserTokens_authenticateSurfSession():
	url=f"{authServerSettings['oidc_authserver']}/oauth/token"
	headers = {
		'content-type': 'application/x-www-form-urlencoded',
	}
	data = {
		'grant_type': 'password',
		'username': f'{user_credentials["testuser_username"]}',
		'password': f'{user_credentials["testuser_password"]}',
		'scope': 'openid profile read:current_user',
		'client_id': f'{authServerSettings["oidc_clientID"]}',
		'client_secret': f'{authServerSettings["oidc_clientSecret"]}',
		'audience': f"{authServerSettings['oidc_authserver']}/api/v2/"
	}

	response = requests.post(url, headers=headers, data=data)
	assert response.status_code == 200, f"expected code 200, returned {response.status_code}"

	oidc_token = json.loads(response.content)
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

	surfSession.cookies.set_cookie(flaskSessionCookie)

@pytest.mark.order(4)
def test_accessAuthPageWithoutLogin():
	page = requests.get(f"https://{flaskAppSettings['app_server_url']}/onlytheauth",verify=flaskAppSettings['publicCert_site'], allow_redirects=False)
	assert page.status_code == 302, f'expected redirect, got {page.status_code}'

@pytest.mark.order(5)
def test_confirmSessionCookie():
	cookies = surfSession.cookies

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
	try:
		signing_key = oidc_jwksClient.get_signing_key_from_jwt(dict_authServerToken['id_token'])
		dict_idTokenDecoded = jwt.decode_complete(
			dict_authServerToken['id_token'],
			key=signing_key,
			audience=authServerSettings['oidc_clientID'],
			algorithms=oidc_tokenSigningAlgos
			)
	except Exception as e:
		pytest.fail(f'id token failed to decode - {e}')

	try:
		signing_key = accessToken_jwksClient.get_signing_key_from_jwt(dict_authServerToken['access_token'])
		dict_accessTokenDecoded = jwt.decode_complete(
			dict_authServerToken['access_token'].strip(),
			key=signing_key,
			audience=f"{authServerSettings['oidc_authserver']}/api/v2/",
			algorithms=['RS256']#oidc_tokenSigningAlgos
			)
	except Exception as e:
		pytest.fail(f'access token failed to decode - {e} \n access token {dict_authServerToken["access_token"]}')


@pytest.mark.order(6)
def test_accessAuthPageWithLogin():
	page = surfSession.get(f"https://{flaskAppSettings['app_server_url']}/onlytheauth",verify=flaskAppSettings['publicCert_site'], allow_redirects=False)
	assert page.status_code == 200, f'expected page to load, got {page.status_code}'

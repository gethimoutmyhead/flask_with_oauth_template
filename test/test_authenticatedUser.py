from user_cred import env as user_credentials
from loadMyAppSettings import env
import pytest
import requests
from requests import Request as urlFetch
import json
# def test_testUser_credentials_present():
# assert len(user_credentials.keys()) > 5, 'FAIL: no user credentials'

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
def test_getUserTokens():
	url=f"{env['oidc_authserver']}/oauth/token"
	headers = {
		'content-type': 'application/x-www-form-urlencoded',
	}
	data = {
		'grant_type': 'password',
		'username': f'{env["testuser_username"]}',
		'password': f'{env["testuser_password"]}',
		'scope': 'openid profile',
		'client_id': f'{env["oidc_clientID"]}',
		'client_secret': f'{env["oidc_clientSecret"]}'
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

@pytest.mark.order(4)
def test_accessAuthPageWithoutLogin():
	zen = requests.get(f"https://{env['app_server_url']}/onlytheauth",verify=env['publicCert_site'], allow_redirects=False)
	assert zen.status_code == 302, f'expected redirect, got {zen.status_code}'

def test_accessAuthPageWithLogin():
	zen = surfSession.get(f"https://{env['app_server_url']}/onlytheauth",verify=env['publicCert_site'], allow_redirects=False)
	assert zen.status_code == 200, f'expected redirect, got {zen.status_code}'
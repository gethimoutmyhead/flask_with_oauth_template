from loadMyAppSettings import flaskAppSettings, authServerSettings
import pytest
import requests
from requests import Request as urlFetch
import json
import flaskCookieMaker
from itertools import repeat
from functools import reduce
import jwt
from urllib.parse import urlencode

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
				domain=f"{flaskAppSettings['app_server_url'].split(':')[0]}",
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

	testSession.close()

def test_loggedOutPageWithInvalidTokens():
	oidc_state = {'oidc_state':'zonzon'}
	requestParameter_state = {'state': 'luptar'}
	target_url=f"https://{flaskAppSettings['app_server_url']}/logged_out"
	
	try:
		tokenAsFlaskCookie = flaskCookieMaker.encodeFlaskCookie(flaskAppSettings['app_cookieSigning_secret'],oidc_state)
		sessionCookie = requests.cookies.create_cookie(
				name='session',
				value=tokenAsFlaskCookie,
				domain=f"{flaskAppSettings['app_server_url'].split(':')[0]}",
				path='/',
				secure=True,
				rest={'HttpOnly': True}
			)
		with requests.Session() as testSession:
			testSession.cookies.set_cookie(sessionCookie)

			response = testSession.get(f"{target_url}?{urlencode(requestParameter_state)}",verify=flaskAppSettings['publicCert_site'], allow_redirects=False)

			assert response.status_code == 400, f"expected 400 \n received {response} \n {oidc_state} _ {requestParameter_state}"
	except Exception as e:
		pytest.fail(f"unknown exception, tokenToTest is {oidc_state}\n {e} \n {tokenAsFlaskCookie} \n {sessionCookie}")

def test_loggedOutPageWithValidTokens():
	oidc_state = {'oidc_state':'zonzon'}
	requestParameter_state = {'state': 'zonzon'}
	target_url=f"https://{flaskAppSettings['app_server_url']}/logged_out"
	
	try:
		tokenAsFlaskCookie = flaskCookieMaker.encodeFlaskCookie(flaskAppSettings['app_cookieSigning_secret'],oidc_state)
		sessionCookie = requests.cookies.create_cookie(
				name='session',
				value=tokenAsFlaskCookie,
				domain=f"{flaskAppSettings['app_server_url'].split(':')[0]}",
				path='/',
				secure=True,
				rest={'HttpOnly': True}
			)
		with requests.Session() as testSession:
			testSession.cookies.set_cookie(sessionCookie)

			response = testSession.get(f"{target_url}?{urlencode(requestParameter_state)}",verify=flaskAppSettings['publicCert_site'], allow_redirects=False)

			assert response.status_code == 200, f"expected 200 \n received {response} \n {oidc_state} _ {requestParameter_state}"
	except Exception as e:
		pytest.fail(f"unknown exception, tokenToTest is {oidc_state}\n {e} \n {tokenAsFlaskCookie} \n {sessionCookie}")

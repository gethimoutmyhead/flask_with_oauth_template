from loadMyAppSettings import authServerSettings
from user_cred import user_credentials
import httpx
import pytest,pytest_asyncio
from urllib.parse import urlencode
import json
import ssl


userAccountDetails = None
targetRole_name = 'Doctor'
targetRole_id = None

@pytest.fixture(scope="session")
def newTestUser():
	return {
		'email':user_credentials['testuser_username'],
		'password': user_credentials['testuser_password'],
	}
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
			'scope':'create:users'
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




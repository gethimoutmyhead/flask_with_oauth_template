import pytest, pytest_asyncio
from loadMyAppSettings import flaskAppSettings, authServerSettings
import httpx
from urllib.parse import urlencode
import json
import ssl

@pytest.fixture(scope="session")
def SSLContext():
	return ssl.create_default_context(cafile=flaskAppSettings['publicCert_site'])
@pytest.mark.asyncio(loop_scope="session")
async def test_emailAccountInDB(SSLContext):
	url=f"https://{flaskAppSettings['app_server_url']}/authAPI/checkUserEmail"
	emailsToCheck = [
		'lazysummers@duck.com',
		'uneven-kennel-quit@duck.com',
		'afar-subtly-bling@duck.com',
	]

	async with httpx.AsyncClient(verify=SSLContext) as client:
		for email in emailsToCheck:

			response = await client.get(f"{url}?email={email}")
			assert response.status_code == 200, f"response {response.status_code}"
			data = response.json()
			assert data[0]['email'] == email, f"expected {email} received {data}"

@pytest.mark.asyncio(loop_scope="session")
async def test_emailAccountNotInDB(SSLContext):
	url=f"https://{flaskAppSettings['app_server_url']}/authAPI/checkUserEmail"
	emailsToCheck = [
		'lazysummers22@duck.com',
		'uneven-kennel-quit22@duck.com',
		'afar-subtly-bling22@duck.com',
	]
	async with httpx.AsyncClient(verify=SSLContext) as client:
		for email in emailsToCheck:

			response = await client.get(f"{url}?email={email}")
			assert response.status_code == 200, f"response {response.status_code}"
			data = response.json()
			assert not data, f"expected empty list, received {data}"

@pytest.mark.asyncio(loop_scope="session")
async def test_invalidEmailRequested(SSLContext):
	url=f"https://{flaskAppSettings['app_server_url']}/authAPI/checkUserEmail"
	emailsToCheck = [
		'horder@@55',
		'uneven-kennel-quit22@duck.com22',
		'TheBestDogs',
	]
	async with httpx.AsyncClient(verify=SSLContext) as client:
		for email in emailsToCheck:

			response = await client.get(f"{url}?email={email}")
			assert response.status_code == 400, f"status code {response.status_code}"
			data = response.json()

			expectedErrorCode = 'invalid_query_string'
			assert data['errorCode'] == expectedErrorCode, f"expected error code {expectedErrorCode}, received {data}"
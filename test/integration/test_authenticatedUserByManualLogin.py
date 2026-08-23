from playwright.sync_api import sync_playwright, Page, BrowserContext
import pytest
from pytest_playwright.pytest_playwright import CreateContextCallback
from loadMyAppSettings import flaskAppSettings, authServerSettings, pyApp_auth0Settings


@pytest.fixture(scope='session')
def loggedInState():
	pw = sync_playwright().start()
	browser = pw.firefox.launch(headless=False)
	page = browser.new_page()
	page.goto(f"https://{flaskAppSettings['app_server_url']}/login")
	breakpoint()
	loggedState = page.context.storage_state()
	browser.close()
	pw.stop()

	return loggedState


def test_loadMainPage(loggedInState, new_context):

	z=loggedInState
	context = new_context(storage_state=z)
	page = context.new_page()

	request = page.goto(f"https://{flaskAppSettings['app_server_url']}/user_details")
	assert 3==5, f"{page.content()}"
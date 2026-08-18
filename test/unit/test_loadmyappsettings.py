from loadMyAppSettings import flaskAppSettings, authServerSettings, pyApp_auth0Settings
from itertools import compress, repeat
import json

def checkEnvVariable(varName):
	assert len(env[varName]) > 0, f"env variable {varName} length <= 0" 

def doesEnvVariableExist(varName):
	assert varName in env.keys(), f"{varName} is not declared"

def is_envVariable_NotEmptyString(varName):
	doesEnvVariableExist(varName)

	assert type(env[varName]) == str, f"varName not a str, its a {type(env[varName])}"

	assert len(env[varName]) > 0, f"varName length is {len(env[varName])}"

def is_configItemsValid(keysToCheck, dictToCheck):
	checklist_keysPresent = [*map(lambda key, dict: key in dict.keys(), keysToCheck, repeat(dictToCheck))]
	keyValuesToVerify = keysToCheck * (not (False in checklist_keysPresent))
	checklist_keyValIsString = [*map(lambda key, dict: type(dict[key]) == str, keyValuesToVerify, repeat(dictToCheck))]
	keyValuesThatAreStrings = list(compress(keyValuesToVerify, checklist_keyValIsString))
	checklist_strlengthNonzero = [*map(lambda key, dict: len(dict[key]) > 0, keyValuesThatAreStrings, repeat(dictToCheck))]


	return {
		'checklist_keysPresent': checklist_keysPresent,
		'checklist_keysAreStrings': checklist_keyValIsString,
		'checklist_nonzeroStrings': checklist_strlengthNonzero,
	}
def test_flaskAppSettings_exist():
	keysNeeded = ['app_cookieSigning_secret', 'app_server_url', 'app_defaultPageMeta_jsonfile']

	# checklist_keysPresent = [*map(lambda key: key in flaskAppSettings.keys(), keysNeeded)]

	configItemsValidity = is_configItemsValid(keysNeeded, flaskAppSettings)
	assert not (False in configItemsValidity['checklist_keysPresent']), f"flaskAppSettings required keys {list(set(keysNeeded) - set(flaskAppSettings.keys()))} missing, found {flaskAppSettings.keys()}"
	assert not (False in configItemsValidity['checklist_keysAreStrings']), f"flaskAppSettings keys are not strings, found {[*map(lambda val: type(val), flaskAppSettings.values())]}"
	assert not (False in configItemsValidity['checklist_nonzeroStrings']), f"flaskAppSettings key values missing data, found {flaskAppSettings.keys()}"

	# list(map(is_envVariable_NotEmptyString, variablesNeeded))

def test_env_oidcVariables_exist():
	keysNeeded = [ 'oidc_clientID', 'oidc_clientSecret', 'oidc_authserver']
	# list(map(is_envVariable_NotEmptyString, variablesNeeded))

	configItemsValidity = is_configItemsValid(keysNeeded, authServerSettings)
	assert not (False in configItemsValidity['checklist_keysPresent']), f"authServerSettings required keys missing,found {authServerSettings.keys()} "
	assert not (False in configItemsValidity['checklist_keysAreStrings']), f"authServerSettings keys are not strings, found {[*map(lambda val: type(val), authServerSettings.values())]}"
	assert not (False in configItemsValidity['checklist_nonzeroStrings']), f"authServerSettings key values missing data, found {authServerSettings.values()}"

def test_env_pyApp_OAuthSettings_exist():
	keysNeeded = [ 'oidc_clientID', 'callbackServer_port', 'oidc_authserver']
	# list(map(is_envVariable_NotEmptyString, variablesNeeded))

	configItemsValidity = is_configItemsValid(keysNeeded, pyApp_auth0Settings)
	assert not (False in configItemsValidity['checklist_keysPresent']), f"pyApp_auth0Settings required keys missing,found {authServerSettings.keys()} "
	assert not (False in configItemsValidity['checklist_keysAreStrings']), f"pyApp_auth0Settings keys are not strings, found {[*map(lambda val: type(val), authServerSettings.values())]}"
	assert not (False in configItemsValidity['checklist_nonzeroStrings']), f"pyApp_auth0Settings key values missing data, found {authServerSettings.values()}"

def test_defaultPageMeta_loads():
	fileToLoad=flaskAppSettings['app_defaultPageMeta_jsonfile']
	with open(fileToLoad, "r", encoding='utf-8') as file:
		list_defaultPageMeta = json.load(file)

	assert isinstance(list_defaultPageMeta, list), f"file loaded is not a dict, its a {type(list_defaultPageMeta)}"

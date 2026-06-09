from loadMyAppSettings import env as env



def checkEnvVariable(varName):
	assert len(env[varName]) > 0, f"env variable {varName} length <= 0" 

def doesEnvVariableExist(varName):
	assert varName in env.keys(), f"{varName} is not declared"

def is_envVariable_NotEmptyString(varName):
	doesEnvVariableExist(varName)

	assert type(env[varName]) == str, f"varName not a str, its a {type(env[varName])}"

	assert len(env[varName]) > 0, f"varName length is {len(env[varName])}"


def test_env_AppVariables_exist():
	variablesNeeded = ['app_cookieSigning_secret', 'app_server_url']
	list(map(is_envVariable_NotEmptyString, variablesNeeded))
def test_env_oidcVariables_exist():
	variablesNeeded = [ 'oidc_clientID', 'oidc_clientSecret', 'oidc_authserver']
	list(map(is_envVariable_NotEmptyString, variablesNeeded))
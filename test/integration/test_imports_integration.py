import pytest
import importlib


def test_add():
	assert 3 == 3
def doesModuleExist(moduleName):
	try:
		importlib.import_module(moduleName)
	except:
		pytest.fail(f"no module {moduleName}")

def test_envModulesAvailable():
	modulesToTest = ['os','dotenv','loadMyAppSettings', 'user_cred']
	z = list(map(doesModuleExist, modulesToTest))



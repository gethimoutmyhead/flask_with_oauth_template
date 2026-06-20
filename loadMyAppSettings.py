from dotenv import dotenv_values
from os import environ as env

filePath_flaskAppSettings = 'flaskApp-settings.env'
flaskAppSettings = dotenv_values(filePath_flaskAppSettings)

filePath_oidcSettings = flaskAppSettings['authserver_configEnv']
authServerSettings = dotenv_values(filePath_oidcSettings)





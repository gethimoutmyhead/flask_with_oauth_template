from dotenv import load_dotenv
from os import environ as env

filePath_flaskAppSettings = 'flaskApp-settings.env'
load_dotenv(filePath_flaskAppSettings)

filePath_oidcSettings = env['authserver_configEnv']
load_dotenv(filePath_oidcSettings)





from dotenv import dotenv_values
from os import environ as env

filePath_flaskAppSettings = 'test/user_cred.env'
user_credentials = dotenv_values(filePath_flaskAppSettings)
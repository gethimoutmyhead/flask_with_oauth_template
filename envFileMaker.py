from dotenv import dotenv_values
import re
# from dotenv import dotenv_values
env_defaults = {
    'gunicorn.conf.py': {
        'bind': '127.0.0.1:1234',
        'certfile': 'neb.pem',
        'keyfile': 'neb-key.pem',
        'workers': 1,
        'timeout': 300,
        'worker_class': 'asgi'
        },
    'flaskApp-settings.env': {
        'app_server_url': '127.0.0.1:1234',
        'app_cookieSigning_secret': '',
        'app_defaultPageMeta_jsonfile': 'defaultPageMeta.json',
        'authserver_configEnv': 'flaskapp_auth0-oidc.env',
        'publicCert_site': 'neb.pem'},
    'flaskapp_auth0-oidc.env': {
        'oidc_clientID': '',
        'oidc_clientSecret': '',
        'oidc_authserver': ''},
}

NUMBER_PATTERN = re.compile(r"-?\d+(\.\d+)?")


def format_env_value(value):
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)

    text = str(value)
    if NUMBER_PATTERN.fullmatch(text):
        return text

    escaped = text.replace("\\", "\\\\").replace("'", "\\'")
    return f"'{escaped}'"

def load_env_files(env_defaults):
    loaded = {}
    for filename in env_defaults:
        loaded[filename] = dotenv_values(filename)
    return loaded


def userInputWithDefaultValue(prompt, default=""):
    if default in ("", None):
        return input(f"{prompt}: ")

    response = input(
        f"{prompt} (default value: {default})\nEnter to keep, or type a new value): "
    )
    return response if response != "" else default

z= {
    'bread.env': {'Flaur':23,'HYDRATION': 0.2},
    'app.env': {'DEBUG': True}
}

def combine_env(env_defaults, loaded_envs):
    combined = {}
    for filename, defaults in env_defaults.items():
        loaded = loaded_envs.get(filename, {})
        combined[filename] = {**defaults, **loaded}
    return combined

def write_env_files(combined):
    for filename, variables in combined.items():
        with open(filename, "w") as f:
            for key, value in variables.items():
                f.write(f"{key}={format_env_value(value)}\n")

def prompt_env_values(combined):
    for filename, variables in combined.items():
        print(f"\n{filename}")
        for key, value in variables.items():
            variables[key] = userInputWithDefaultValue(key, value)
    return combined

loaded = load_env_files(env_defaults)
combined = combine_env(env_defaults, loaded)
prompt_env_values(combined)
write_env_files(combined)
import json
import logging
import os
from os import environ as env
from urllib.parse import quote_plus, urlencode

from authlib.integrations.flask_client import OAuth
from dotenv import find_dotenv, load_dotenv
from flask import Flask, redirect, render_template, session, url_for, request

load_dotenv()

load_dotenv(env['authserver_configEnv'])


app = Flask(__name__)

app.config['SECRET_KEY'] = os.getenv("app_cookieSigning_secret")
app.config['SERVER_NAME'] = os.getenv("app_server_url")


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)
# logger.info(app.config['SECRET_KEY'])
# logger.info(app.config['SERVER_NAME'])
logger.info(f"client id using os getenv is {os.getenv("oidc_clientID")}")
logger.info(f"using env is {env['oidc_clientID']}")


def _inspect(resp):
    req = resp.request
    body = getattr(req, "body", None) or getattr(req, "content", None)  # requests vs httpx
    logger.info("=== TOKEN REQUEST ===")
    logger.info(f"URL:   {req.url} ")
    logger.info(f"HEADERS:{dict(req.headers)}", )
    logger.info(f"BODY:   {body}")
    logger.info("=== TOKEN RESPONSE ===")
    logger.info(f"STATUS: {resp.status_code}")
    logger.info(f"BODY:   {resp.text}")
    logger.info("======================")
    return resp
def _compliance_fix(session):
    session.register_compliance_hook('access_token_response', _inspect)



oauth = OAuth(app)
oauth.register(
	"oidc",
	client_id=env.get("oidc_clientID"),
	client_secret=env.get("oidc_clientSecret"),
	client_kwargs={
		"scope": "openid",
		"token_endpoint_auth_method": "client_secret_post",
	},
	compliance_fix=_compliance_fix,
	server_metadata_url=f'{os.getenv("oidc_authserver")}/.well-known/openid-configuration',
)

# logger.info(f'https://{os.getenv("authserver_domain")}/.well-known/openid-configuration')
# logger.info(env.get("authgear_client_id"))
# logger.info(env.get("authgear_client_secret"))



@app.before_request
def log_request():
	logger.info(request.headers)
	logger.info(request.data)
	logger.info(request.args)
@app.route("/")
def hello():
	return f"serving from {os.getenv('app_server_url')}"

@app.route("/login")
def login():
	# print (url_for("callback"))
	logger.info(f"/login requested. callback url is {url_for("callback", _external=True)}")
	return oauth.oidc.authorize_redirect(
        redirect_uri=url_for("callback", _external=True)
    )

@app.route("/after-authentication", methods=["GET", "POST"])
def callback():
	logger.info(f"/after-authentication requested, with parameters {request.args.to_dict()}")
	# logger.info(session["state"])
	token = oauth.oidc.authorize_access_token()
	logger.info(token)
	user = token['userinfo']
	session["user"] = user
	session["user_id_token"] = token["id_token"]
	session["user_access_token"] = token["access_token"]
	# session["user_refresh_token"] = token["refresh_token"]
	return redirect("/logged-in")


@app.route("/logged-in")
def logged_in():
	# usersession = session.get("user")
	logger.info(f"/logged-in requested, cookie dump {session}")
	if "user" not in session:
		username ='guest user'
	else:

		username = session.get("user")

	return (f"successfully logged in {username}")

@app.route("/logout")
def logout():
	session.clear()
	return redirect(f"{os.getenv('oidc_authserver')}/v2/logout")
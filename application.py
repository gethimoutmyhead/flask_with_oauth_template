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
logger.info(os.getenv("oidc_clientID"))
logger.info(env['oidc_clientID'])
oauth = OAuth(app)
oauth.register(
	"oidc",
	client_id=env.get("oidc_clientID"),
	client_secret=env.get("oidc_clientSecret"),
	client_kwargs={
		"scope": "openid",
		"token_endpoint_auth_method": "client_secret_post",
	},
	server_metadata_url=f'{os.getenv("oidc_authserver")}/.well-known/openid-configuration',
)

# logger.info(f'https://{os.getenv("authserver_domain")}/.well-known/openid-configuration')
# logger.info(env.get("authgear_client_id"))
# logger.info(env.get("authgear_client_secret"))

@app.route("/")
def hello():
	return f"serving from {os.getenv('app_server_url')}"

@app.route("/login")
def login():
	# print (url_for("callback"))
	logger.info(url_for("callback", _external=True))
	return oauth.oidc.authorize_redirect(
        redirect_uri=url_for("callback", _external=True)
    )

@app.route("/after-authentication", methods=["GET", "POST"])
def callback():
	logger.info(request.args.to_dict())
	# logger.info(session["state"])
	token = oauth.oidc.authorize_access_token()
	logger.info(token)
	user = token['userinfo']
	session["user"] = user
	session["user_id_token"] = token["id_token"]
	session["user_access_token"] = token["access_token"]
	session["user_refresh_token"] = token["refresh_token"]
	return redirect("/logged-in")


@app.route("/logged-in")
def logged_in():
	# usersession = session.get("user")
	logger.info(session)
	if "user" not in session:
		username ='guest user'
	else:

		username = session.get("user")

	return (f"successfully logged in {username}")

@app.route("/logout")
def logout():
	if "user_refresh_token" not in session:
		session.clear()
		je= redirect('/')
	else:
		refresh_token = session['user_refresh_token']
		response = oauth.oidc.get("/oauth2/revoke", token=refresh_token, client_id=env.get("oidc_clientID"))
		resp.raise_for_status()
		je = resp.json()
	return je
    # session.clear()
    # # return redirect(
    #     "https://"
    #     + os.getenv("oidc_authserver")
    #     + "/oauth2/end_session"
    # )
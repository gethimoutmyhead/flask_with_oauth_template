import json
import logging
import os
from os import environ as env
from urllib.parse import quote_plus, urlencode

from authlib.integrations.flask_client import OAuth
from dotenv import find_dotenv, load_dotenv
from flask import Flask, redirect, render_template, session, url_for, request

load_dotenv()

app = Flask(__name__)

app.config['SECRET_KEY'] = os.getenv("app_cookieSigning_secret")
app.config['SERVER_NAME'] = os.getenv("app_server_url")


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

logger.info(app.config['SECRET_KEY'])
logger.info(app.config['SERVER_NAME'])

oauth = OAuth(app)
oauth.register(
	"authgear",
	client_id=env.get("authgear_client_id"),
	client_secret=env.get("authgear_client_secret"),
	# client_id='a19a29de67d9f981',
	# # client_id='quacklikeaduck',
	# # client_secret='mjNxcb18TmAofW8mD7OLBtykzxXhF6VO',
	# client_secret='disappoint',
	client_kwargs={
		"scope": "openid profile offline_access",
		"token_endpoint_auth_method": "client_secret_post",
	},
	server_metadata_url=f'https://{os.getenv("authserver_domain")}/.well-known/openid-configuration',
)

logger.info(f'https://{os.getenv("authserver_domain")}/.well-known/openid-configuration')

logger.info(env.get("authgear_client_id"))
logger.info(env.get("authgear_client_secret"))

@app.route("/")
def hello():
	return f"serving from{os.getenv('app_server_url')}"

@app.route("/login")
def login():
	# print (url_for("callback"))
	logger.info(url_for("callback", _external=True))
	return oauth.authgear.authorize_redirect(
        redirect_uri=url_for("callback", _external=True)
    )

@app.route("/after-authentication", methods=["GET", "POST"])
def callback():
	logger.info(request.args.to_dict())
	# logger.info(session["state"])
	token = oauth.authgear.authorize_access_token()
	session["user"] = token
	return redirect("/logged-in")


@app.route("/logged-in")
def logged_in():
	# usersession = session.get("user")
	if "user" not in session:
		username ='guest user'
	else:
		username = session.get("user")["userinfo"]

	return (f"successfully logged in {username}")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(
        "https://"
        + os.getenv("AUTHGEAR_DOMAIN")
        + "/oauth2/end_session"
    )
import json
import logging
from flask import Flask, redirect, render_template, session, url_for, request
from authlib.integrations.requests_client import OAuth2Session

from loadMyAppSettings import env as env


app = Flask(__name__)

app.config['SECRET_KEY'] = env["app_cookieSigning_secret"]
app.config['SERVER_NAME'] = env["app_server_url"]

oidcserver_metadataURL = f"{env['oidc_authserver']}/.well-known/openid-configuration"

oidcServer_client = OAuth2Session(
	client_id=env['oidc_clientID'],
	client_secret=env['oidc_clientSecret'],
	server_metadata_url=oidcserver_metadataURL,
	client_kwargs={
		"scope": "openid profile",
		"token_endpoint_auth_method": "client_secret_post",
	}
)

@app.route("/")
def hello():
	return render_template("base.html")

@app.route("/login")
def login():
	url_redirectAfterAuth = url_for('oidc_server_callback', _external=True)
	loginURI, state = oidcServer_client.create_authorization_url(url=f"{env['oidc_authserver']}/authorize",redirect_uri=url_redirectAfterAuth)
	session['oidc_state'] = state
	return redirect(loginURI)

@app.route("/after-authentication")
def oidc_server_callback():

	token_endpoint = f"{env['oidc_authserver']}/oauth/token"
	jojo = oidcServer_client.fetch_token(token_endpoint, 
		authorization_response=request.url, 
		redirect_uri=url_for('oidc_server_callback', _external=True))
	return f'{jojo}'

@app.route('/logged-in')
def logged_in():
	return render_template("base.html")

@app.route ('/logout')
def logout():
	return render_template("base.html")
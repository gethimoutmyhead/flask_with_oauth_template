import json
import logging
from flask import Flask, redirect, render_template, session, url_for, request
from authlib.integrations.requests_client import OAuth2Session

from loadMyAppSettings import env as env
from itertools import repeat, chain
from functools import wraps

app = Flask(__name__)

app.config['SECRET_KEY'] = env["app_cookieSigning_secret"]
app.config['SERVER_NAME'] = env["app_server_url"]

oidcserver_metadataURL = f"{env['oidc_authserver']}/.well-known/openid-configuration"

oidcServer_client = OAuth2Session(
	client_id=env['oidc_clientID'],
	client_secret=env['oidc_clientSecret'],
)

def check_loggedIn(func):
	# @wraps(f)
	def checkLog(*args):
		token_is_present = 'authserver_token' in session.keys()
		if token_is_present is not True:
			return redirect(url_for('guest'))
		return func(*args)
	return checkLog

@app.route("/")
def hello():
	return render_template("base.html")

@app.route("/login")
def login():
	url_redirectAfterAuth = url_for('oidc_server_callback', _external=True)
	loginURI, state = oidcServer_client.create_authorization_url(
		url=f"{env['oidc_authserver']}/authorize",
		redirect_uri=url_redirectAfterAuth,
		response_type='code',
		scope='openid profile offline_access',
	)
	session['oidc_state'] = state
	return redirect(loginURI)

@app.route("/after-authentication")
def oidc_server_callback():
	token_endpoint = f"{env['oidc_authserver']}/oauth/token"
	returnPage = []
	if "error" in request.args.keys():
		metaTags = [
			{'name': 'description', 'content': 'OAuth authentication flow error', 'lang': 'en'},
			{'name': 'description', 'content': 'OAuth அங்கீகார ஓட்டப் பிழை', 'lang': 'ta'},
		]
		return render_template(
			"auth-error.html", 
			errorMessage=f"{request.args.get('error')} -  {request.args.get('error_description')}",
			metaTags = metaTags,
			)

	URIargumentsNeeded = ['code', 'state']

	argumentsPresentCheck = [*map(lambda argToTest, argsReceived: argToTest in argsReceived, URIargumentsNeeded, repeat(request.args.keys()))]
	missingArguments = False in argumentsPresentCheck
	if missingArguments:
		metaTags = [
			{'name': 'description', 'content': 'OAuth authentication flow error', 'lang': 'en'},
			{'name': 'description', 'content': 'OAuth அங்கீகார ஓட்டப் பிழை', 'lang': 'ta'},
		]
		return render_template(
			"auth-error.html", 
			errorMessage= f"AuthServer response error - missing arguments, arguments present are {request.args.keys()}",
			metaTags = metaTags,
			)

	else:
		try:
			oidc_token = oidcServer_client.fetch_token(token_endpoint,
				authorization_response=request.url, 
				redirect_uri=url_for('oidc_server_callback', _external=True),
			)
			# return oidc_token
			session['authserver_token'] = oidc_token
			return ('login achieved')
		except Exception as e:
			return render_template(
				"auth-error.html",
				errorMessage=e
				)
	# return f"AuthServer response error - missing arguments, arguments present are {request.args.keys()}"

@app.route('/logged-in')
def logged_in():
	return render_template("base.html")

@app.route ('/logout')
def logout():
	return render_template("base.html")

@app.route('/guest-user')
def guest():
	return ('only a guest here')


@app.route('/onlytheauth')
@check_loggedIn
def theauth():
	return (f'the auth is here {session['authserver_token']}')



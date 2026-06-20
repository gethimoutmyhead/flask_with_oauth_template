import json
import logging
import requests as fetch_url
from flask import Flask, redirect, render_template, session, url_for, request, make_response
from authlib.integrations.requests_client import OAuth2Session
import jwt
from datetime import datetime, timezone, timedelta
from urllib.parse import urlencode

import random, string
from loadMyAppSettings import flaskAppSettings, authServerSettings
from itertools import repeat, chain
from functools import wraps

app = Flask(__name__)

app.config['SECRET_KEY'] = flaskAppSettings["app_cookieSigning_secret"]
app.config['SERVER_NAME'] = flaskAppSettings["app_server_url"]

url_for_oidcserver_metadataURL = f"{authServerSettings['oidc_authserver']}/.well-known/openid-configuration"

request_oidcserver_metadata = fetch_url.get(url_for_oidcserver_metadataURL)
oidcserver_metadata = request_oidcserver_metadata.json()
oidc_jwksClient = jwt.PyJWKClient(oidcserver_metadata["jwks_uri"])
oidc_tokenSigningAlgos = oidcserver_metadata['id_token_signing_alg_values_supported']
oidcServer_client = OAuth2Session(
	client_id=authServerSettings['oidc_clientID'],
	client_secret=authServerSettings['oidc_clientSecret'],
)

def check_loggedIn(func):
	# @wraps(f)
	def checkLog(*args, **kwargs):
		token_is_present = 'authserver_token' in session.keys()
		if token_is_present is not True:
			return redirect(url_for('guest'))
		return func(*args)
	return checkLog

def URIandState_request_authserverLoginURL(clientSession, dict_idProviderMetaData, url_audience, url_callbackAfterLogin, url_destinationAfterAuth):
	loginURI, state = clientSession.create_authorization_url(
		url=dict_idProviderMetaData['authorization_endpoint'],
		redirect_uri=url_callbackAfterLogin,
		response_type='code',
		scope='openid profile offline_access read:current_user',
		state=jwt_generateRedirectState(url_destinationAfterAuth),
		audience=url_audience
	)
	return loginURI, state
def jwt_generateRedirectState(str_urlToRedirect):
    """
    Create a short-lived signed JWT capturing the page the user is currently
    trying to access, so we can redirect back to it after a successful login.
 
    Returns the encoded token string.
    """
    # full_path keeps the query string; fall back to path when there isn't one
    # (full_path appends a bare "?" otherwise).
    # intended_path = request.full_path if request.query_string else request.path
 
    payload = {
        "intended_path": str_urlToRedirect,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=360),
    }
    return jwt.encode(
        payload,
        app.config["SECRET_KEY"],
        algorithm="HS256",
    )

def dict_decodedJWT(myjwt):
	payload = jwt.decode(myjwt, app.config['SECRET_KEY'], algorithms=['HS256'])
	return payload

def authorization_check(permittedRoles=[], permittedAttributes=[]):
	def decorator(view_func):
		@wraps(view_func)
		def wrapper(*args, **kwargs):
			token_is_present = 'authserver_token' in session.keys()
			if not token_is_present:              
				# url_redirectAfterAuth = request.full_path
				# loginURI, state = oidcServer_client.create_authorization_url(
				# 	url=oidcserver_metadata['authorization_endpoint'],
				# 	redirect_uri=url_for('oidc_server_callback', _external=True),
				# 	response_type='code',
				# 	scope='openid profile offline_access read:users read:roles',
				# 	state=jwt_generateRedirectState(url_redirectAfterAuth),
				# 	audience='https://dev-ei6babp7krz2qnk3.au.auth0.com/api/v2/',
				# )
				# session['oidc_state'] = state
				# return redirect(loginURI)
				loginURI, state = URIandState_request_authserverLoginURL(
					clientSession=oidcServer_client,
					dict_idProviderMetaData=oidcserver_metadata,
					url_audience=f"{authServerSettings['oidc_authserver']}/api/v2/",
					url_callbackAfterLogin=url_for('oidc_server_callback', _external=True),
					url_destinationAfterAuth=request.full_path,
				)	
				session['oidc_state'] = state
				return redirect(loginURI)
			return view_func(*args, **kwargs)
		return wrapper
	return decorator

@app.route("/")
def hello():
	return render_template("base.html")

@app.route("/login")
def login():
	url_redirectAfterAuth = url_for('oidc_server_callback', _external=True)
	# loginURI, state = oidcServer_client.create_authorization_url(
	# 	url=oidcserver_metadata['authorization_endpoint'],
	# 	redirect_uri=url_redirectAfterAuth,
	# 	response_type='code',
	# 	scope='openid profile offline_access read:current_user read:roles',
	# 	state=jwt_generateRedirectState(url_for('logged_in', _external=True)),
	# 	audience='https://dev-ei6babp7krz2qnk3.au.auth0.com/api/v2/',
	# )
	loginURI, state = URIandState_request_authserverLoginURL(
			clientSession=oidcServer_client,
			dict_idProviderMetaData=oidcserver_metadata,
			url_audience=f"{authServerSettings['oidc_authserver']}/api/v2/",
			url_callbackAfterLogin=url_for('oidc_server_callback', _external=True),
			url_destinationAfterAuth=url_for('logged_in', _external=True),
		)	
	session['oidc_state'] = state
	return redirect(loginURI)

@app.route("/after-authentication")
def oidc_server_callback():
	token_endpoint = oidcserver_metadata['token_endpoint']
	bool_errorParameterReceived = 'error' in request.args.keys()
	
	requiredParameters = ['code', 'state']
	checklist_requiredParameters = [*map(lambda argToTest, argsReceived: argToTest in argsReceived, requiredParameters, repeat(request.args.keys()))]
	bool_missingArguments = False in checklist_requiredParameters

	if bool_errorParameterReceived:
		# metaTags = [
		# 	{'name': 'description', 'content': 'OAuth authentication flow error', 'lang': 'en'},
		# 	{'name': 'description', 'content': 'OAuth அங்கீகார ஓட்டப் பிழை', 'lang': 'ta'},
		# ]
		# return render_template(
		# 	"auth-error.html", 
		# 	errorMessage=f"{request.args.get('error')} -  {request.args.get('error_description')}",
		# 	metaTags = metaTags,
		# 	)
		response = make_response(redirect('logout'))
		response.headers['X-Error-Title'] = 'OAuth authentication flow error'
		response.headers['X-Error-Message'] = f"AuthServer error parameter - {request.args.get('error')} -  {request.args.get('error_description')}"
		return response
	# URIargumentsNeeded = ['code', 'state']

	# argumentsPresentCheck = [*map(lambda argToTest, argsReceived: argToTest in argsReceived, URIargumentsNeeded, repeat(request.args.keys()))]
	# missingArguments = False in argumentsPresentCheck
	if bool_missingArguments:
		# metaTags = [
		# 	{'name': 'description', 'content': 'OAuth authentication flow error', 'lang': 'en'},
		# 	{'name': 'description', 'content': 'OAuth அங்கீகார ஓட்டப் பிழை', 'lang': 'ta'},
		# ]
		# return render_template(
		# 	"auth-error.html", 
		# 	errorMessage= f"AuthServer response error - missing arguments, arguments present are {request.args.keys()}",
		# 	metaTags = metaTags,
		# 	)
		response = make_response(redirect('logout'))
		response.headers['X-Error-Title'] = 'OAuth authentication flow error'
		response.headers['X-Error-Message'] = f"Response missing arguments, arguments present are {request.args.keys()}"
		return response


	
	try:
		oidc_token = oidcServer_client.fetch_token(token_endpoint,
			authorization_response=request.url, 
			redirect_uri=url_for('oidc_server_callback', _external=True),
		)
		# return oidc_token

		# return (f'login achieved, redirecting to {state_decoded}')
	except Exception as e:
		return render_template(
			"auth-error.html",
			errorMessage=e
			)

	access_token = oidc_token['access_token']
	id_token = oidc_token['id_token']

	signing_key = oidc_jwksClient.get_signing_key_from_jwt(id_token)
	try:
		signing_key = oidc_jwksClient.get_signing_key_from_jwt(id_token)
		validation = jwt.decode_complete(
			id_token,
			key=signing_key,
			audience=authServerSettings['oidc_clientID'],
			algorithms=oidc_tokenSigningAlgos
			)
	except Exception as e:
		return render_template(
			"auth-error.html",
			errorMessage=f"id_token validation error: {e}" 
			)

	session['authserver_token'] = oidc_token
	state_decoded = dict_decodedJWT(session['oidc_state'])
	redirect_url = state_decoded['intended_path']
	response = make_response(redirect(redirect_url))
	return response
	# return f"AuthServer response error - missing arguments, arguments present are {request.args.keys()}"

@app.route('/logged-in')
def logged_in():
	return render_template("base.html")

@app.route ('/logout')
def logout():
	oidc_token_list = [session.get('authserver_token')]
	oidc_token = filter(lambda x: x is not None, oidc_token_list)
	id_token_list = map(lambda x: x.get('id_token'), oidc_token)
	id_token = [*filter(lambda x: x is not None, id_token_list)]
	params = {'client_id': authServerSettings['oidc_clientID']}

	if len(id_token) > 0:
		params['id_token_hint'] = id_token[0]

	length = 10
	alphabet = string.ascii_letters + string.digits
	state = ''.join(random.choice(alphabet) for _ in range(length))

	session.clear()
	session['oidc_state'] = state
	params['state'] = state
	params['post_logout_redirect_uri'] = url_for('logged_out',_external=True)
	url = f"{oidcserver_metadata['end_session_endpoint']}?{urlencode(params)}"
	return redirect(url)
	# return redirect(oidcserver_metadata['authorization_endpoint'])

@app.route('/guest-user')
def guest():
	return ('only a guest here')


@app.route('/onlytheauth')
@authorization_check()
def theauth():
	return (f'the auth is here {session['authserver_token']}')

@app.route('/disappoint')
def disappoint():
	zen = make_response(redirect('logged_in'))
	zen.headers['X-Error-Message'] = 'sad'
	return zen

@app.route('/logged_out')
def logged_out():
	localState = session.get('oidc_state','')
	responseState = request.args.get('state','x')

	if localState != responseState:

		page = make_response(render_template(
					"auth-error.html", 
					errorMessage=f"Error - local and response state mismatch\nlocal state is {session.get('oidc_state','undefined')}\nresponse state is {request.args.get('state', 'undefined')}"
					))
		session.clear()
		return page
	session.clear()
	return render_template('logged-out.html')

@app.route('/user_details')
@authorization_check()
def user_details():
	oidcToken = [*filter(lambda x: x is not None, [session.get('authserver_token')])]
	id_token = [*filter(lambda x: x is not None, map(lambda x: x.get('id_token'), oidcToken))]
	access_token = [*filter(lambda x: x is not None, map(lambda x: x.get('access_token'), oidcToken))]

	userMeta = fetch_url.get(oidcserver_metadata['userinfo_endpoint'], headers={'authorization': f"Bearer {access_token[0]}"})
	# getUserURL=f"{env['oidc_authserver']}/api/v2/users/{fillThisWithAccessTokenSub}"
	# z=requests.get(getUserURL,headers={'authorization':f"Bearer {access_token}"})
	return render_template(
			"auth-error.html",
			errorMessage=userMeta.content
			)


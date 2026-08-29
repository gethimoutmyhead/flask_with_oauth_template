import json
import logging
import requests as fetch_url
from quart import Quart, redirect, render_template, session, url_for, request, make_response
from authlib.integrations.httpx_client import AsyncOAuth2Client
import jwt
from datetime import datetime, timezone, timedelta
from urllib.parse import urlencode

import random, string
from loadMyAppSettings import flaskAppSettings, authServerSettings, pyApp_auth0Settings
from itertools import repeat, chain
from functools import wraps, reduce, partial, Placeholder
from functions_tokenValidation import authserverToken_validateIdToken, authserverToken_validateAccessToken
import asyncio

fileToLoad=flaskAppSettings['app_defaultPageMeta_jsonfile']
with open(fileToLoad, "r", encoding='utf-8') as file:
	listOfDicts_defaultPageMeta = json.load(file)

app = Quart(__name__)
app.config['SECRET_KEY'] = flaskAppSettings["app_cookieSigning_secret"]
app.config['SERVER_NAME'] = flaskAppSettings["app_server_url"]
app.config['SESSION_COOKIE_SECURE'] = True
app.config['DEFAULTPAGEMETA'] = listOfDicts_defaultPageMeta
url_for_oidcserver_metadataURL = f"{authServerSettings['oidc_authserver']}/.well-known/openid-configuration"

request_oidcserver_metadata = fetch_url.get(url_for_oidcserver_metadataURL)
oidcserver_metadata = request_oidcserver_metadata.json()
oidc_jwksClient = jwt.PyJWKClient(oidcserver_metadata["jwks_uri"])
accessToken_jwksClient = jwt.PyJWKClient(f"{authServerSettings['oidc_authserver']}/.well-known/jwks.json")

oidc_tokenSigningAlgos = oidcserver_metadata['id_token_signing_alg_values_supported']
oidcServer_client = AsyncOAuth2Client(
	client_id=authServerSettings['oidc_clientID'],
	client_secret=authServerSettings['oidc_clientSecret'],
)


async def URIandState_request_authserverLoginURL(clientSession, dict_idProviderMetaData, url_audience, url_callbackAfterLogin, url_destinationAfterAuth, login_hint=''):
	loginURI, state = clientSession.create_authorization_url(
		url=dict_idProviderMetaData['authorization_endpoint'],
		redirect_uri=url_callbackAfterLogin,
		response_type='code',
		scope='openid profile read:current_user',
		state=jwt_generateRedirectState(url_destinationAfterAuth),
		audience=url_audience,
		login_hint=login_hint
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
		async def wrapper(*args, **kwargs):
	
			## checks for errors in the tokens

			list_requiredIdTokenClaims = [
				'iss',
				'sub',
				'aud',
				f'https://{flaskAppSettings['app_server_url']}/roles'
			]

			list_requiredAccessTokenClaims = [
				'iss',
				'sub',
				'aud',
				f'https://{flaskAppSettings['app_server_url']}/roles'
			]
	
			def sessionCookie_check1(sessionCookie):
				return {
					True: sessionCookie,
					False: {
						'X-Error-Title': "User not authenticated",
						'X-Error-Message':'AppAuthnERROR: session missing token authserver_token'
					}
				}[('authserver_token' in sessionCookie)]

			def sessionCookie_check2(sessionCookie):
				keysRequired = ['access_token', 'id_token']
				keysPresent = sessionCookie['authserver_token'].keys()
				keysMissing = sorted(list(set(keysRequired) - set(keysPresent)))
				# print (keysRequired, keysPresent, keysMissing)
				# print (set(keysRequired) <= set(keysPresent))
				return {
					True: sessionCookie,
					False: {
						'X-Error-Message': f"AppAuthnERROR: session['authserver_token'] missing keys {', '.join(keysMissing)}",
						'X-Error-Title': f"App Authentication Token Error - Bad Request"
						}
					}[(set(keysRequired) <= set(keysPresent))]


			async def sessionCookie_check3(sessionCookie):
				IdToken_check = partial(
					authserverToken_validateIdToken,
					Placeholder,
					list_requiredIdTokenClaims,
					url_for_oidcserver_metadataURL, 
					[authServerSettings['oidc_clientID'], pyApp_auth0Settings['oidc_clientID']], 
					oidc_tokenSigningAlgos
				)

				z = await IdToken_check(sessionCookie['authserver_token'])
				validatedToken = not ('AppAuthnERROR' in z)
				if validatedToken:
					newCookie = sessionCookie.copy()
					newCookie['authserver_token']['idTokenDecoded'] = z['idTokenDecoded']

				else:
					newCookie = {
						'X-Error-Message': z,
						'X-Error-Title': f"App Authentication Token Error"
					}
				return newCookie

			async def sessionCookie_check4(sessionCookie):
				AccessToken_check = partial(
					authserverToken_validateAccessToken,
					Placeholder,
					list_requiredIdTokenClaims,
					url_for_oidcserver_metadataURL, 
					f"{authServerSettings['oidc_authserver']}/api/v2/", 
					oidc_tokenSigningAlgos
				)

				z = await AccessToken_check(sessionCookie['authserver_token'])
				validatedToken = not ('AppAuthnERROR' in z)
				if validatedToken:
					newCookie = sessionCookie.copy()
					newCookie['authserver_token']['accessTokenDecoded'] = z['accessTokenDecoded']
				else:
					newCookie = {
						'X-Error-Message': z,
						'X-Error-Title': f"App Authentication Token Error"
					}
				return newCookie

			checklist_authzFunctions = [
				sessionCookie_check1,
				sessionCookie_check2,
				# sessionCookie_check3,
				# sessionCookie_check4,
			]
			# print (sessionCookie_check2(session))
			def errorCheck(acc, func):
				if 'X-Error-Title' in acc:
					return (acc)
				return func(acc)

			checks = reduce(errorCheck, checklist_authzFunctions, session)
			for func in [sessionCookie_check3, sessionCookie_check4]:
				if 'X-Error-Title' not in checks:
					print (checks)
					checks = await func(checks)


			if ('X-Error-Message' in checks):              
				loginURI, state = await URIandState_request_authserverLoginURL(
					clientSession=oidcServer_client,
					dict_idProviderMetaData=oidcserver_metadata,
					url_audience=f"{authServerSettings['oidc_authserver']}/api/v2/",
					url_callbackAfterLogin=url_for('oidc_server_callback', _external=True),
					url_destinationAfterAuth=request.full_path,
				)	
				session['oidc_state'] = state
				headers = {}

				response = await make_response(redirect(loginURI))
				response.headers.update(checks)
				return response

			## checks if user is authorized to access this area
			userRoles = checks['authserver_token']['idTokenDecoded']['payload'][f'https://{flaskAppSettings['app_server_url']}/roles']

			## if no permittedRoles are assigned, then any user role is accepted
			acceptedRoles = permittedRoles + userRoles * (len(permittedRoles) == 0)
			authorizedUserRoles = set(acceptedRoles) & set(userRoles)

			if (not authorizedUserRoles):			
				return await render_template(
						'forbidden.html',
						errorMessage='You do not have the correct roles to access this page'
					), 403
			## every check has passed, so return the requested page
			return await view_func(*args, **kwargs)
		return wrapper
	return decorator

@app.route("/")
async def hello():
	return await render_template("base.html")

@app.route("/login")
async def login():
	login_hint = request.args.get('login_hint', '')
	loginURI, state = await URIandState_request_authserverLoginURL(
			clientSession=oidcServer_client,
			dict_idProviderMetaData=oidcserver_metadata,
			url_audience=f"{authServerSettings['oidc_authserver']}/api/v2/",
			url_callbackAfterLogin=url_for('oidc_server_callback', _external=True),
			url_destinationAfterAuth=url_for('logged_in', _external=True),
			login_hint=login_hint
		)	
	session['oidc_state'] = state
	return redirect(loginURI)

@app.route("/after-authentication")
async def oidc_server_callback():
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
		headers = {}
		response = await make_response(redirect('logout'))
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
		headers = {}

		response = await make_response(redirect('logout'))
		response.headers['X-Error-Title'] = 'OAuth authentication flow error'
		response.headers['X-Error-Message'] = f"Response missing arguments, arguments present are {request.args.keys()}"

		return response


	
	try:
		oidc_token = await oidcServer_client.fetch_token(token_endpoint,
			authorization_response=request.url, 
			redirect_uri=url_for('oidc_server_callback', _external=True),
		)
		# return oidc_token

		# return (f'login achieved, redirecting to {state_decoded}')
	except Exception as e:
		return await render_template(
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
		return await render_template(
			"auth-error.html",
			errorMessage=f"id_token validation error: {e}" 
			)

	try:
		signing_key = accessToken_jwksClient.get_signing_key_from_jwt(access_token)
		dict_accessTokenDecoded = jwt.decode_complete(
			access_token,
			key=signing_key,
			audience=f"{authServerSettings['oidc_authserver']}/api/v2/",
			algorithms=['RS256']#oidc_tokenSigningAlgos
			)
	except Exception as e:
		return await render_template(
			"auth-error.html",
			errorMessage=f"access_token validation error: {e}" 
			)

	session['authserver_token'] = oidc_token
	state_decoded = dict_decodedJWT(session['oidc_state'])
	redirect_url = state_decoded['intended_path']
	response = make_response(redirect(redirect_url))
	return await response
	# return f"AuthServer response error - missing arguments, arguments present are {request.args.keys()}"

@app.route('/logged-in')
async def logged_in():
	return await render_template("base.html")

@app.route ('/logout')
async def logout():
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
async def guest():
	return ('only a guest here')


@app.route('/authenticated')
@authorization_check()
async def authenticated():
	return await render_template('authenticated.html', authserver_token = session['authserver_token'])
	# return (f'the auth is here {session['authserver_token']}')

@app.route('/disappoint')
async def disappoint():
	headers = {}

	zen = await make_response(redirect('logged_in'))
	response.headers['X-Error-Message'] = 'sad'	
	return zen

@app.route('/logged_out')
async def logged_out():
	localState = session.get('oidc_state','')
	responseState = request.args.get('state','x')

	if localState != responseState:

		page = await make_response(await render_template(
					"auth-error.html", 
					errorMessage=f"Error - local and response state mismatch\nlocal state is {session.get('oidc_state','undefined')}\nresponse state is {request.args.get('state', 'undefined')}"
					))
		session.clear()
		return page, 400
	session.clear()
	return await render_template('logged-out.html')

@app.route('/user_details')
@authorization_check()
async def user_details():
	oidcToken = [*filter(lambda x: x is not None, [session.get('authserver_token')])]
	id_token = [*filter(lambda x: x is not None, map(lambda x: x.get('id_token'), oidcToken))]
	access_token = [*filter(lambda x: x is not None, map(lambda x: x.get('access_token'), oidcToken))]

	userMeta = fetch_url.get(oidcserver_metadata['userinfo_endpoint'], headers={'authorization': f"Bearer {access_token[0]}"})

	# getUserURL=f"{env['oidc_authserver']}/api/v2/users/{fillThisWithAccessTokenSub}"
	# z=requests.get(getUserURL,headers={'authorization':f"Bearer {access_token}"})

	return await render_template(
			"response.html",
			responseMessage=userMeta.content
			)

@app.route('/pharmacist-page')
@authorization_check(permittedRoles=['Pharmacist'])
async def pharmacistPage():
	# getUserURL=f"{env['oidc_authserver']}/api/v2/users/{fillThisWithAccessTokenSub}"
	# z=requests.get(getUserURL,headers={'authorization':f"Bearer {access_token}"})

	return await render_template(
			"response.html",
			responseMessage="You have opened the pharmacist page"
			)

@app.route('/doctor-page')
@authorization_check(permittedRoles=['Doctor'])
async def doctorPage():
	# getUserURL=f"{env['oidc_authserver']}/api/v2/users/{fillThisWithAccessTokenSub}"
	# z=requests.get(getUserURL,headers={'authorization':f"Bearer {access_token}"})

	return await render_template(
			"response.html",
			responseMessage="You have opened the doctor page"
			)

@app.route('/allied-health-page')
@authorization_check(permittedRoles=['Doctor', 'Pharmacist'])
async def alliedHealthPage():
	# getUserURL=f"{env['oidc_authserver']}/api/v2/users/{fillThisWithAccessTokenSub}"
	# z=requests.get(getUserURL,headers={'authorization':f"Bearer {access_token}"})

	return await render_template(
			"response.html",
			responseMessage="You have opened the Allied Health page"
			)
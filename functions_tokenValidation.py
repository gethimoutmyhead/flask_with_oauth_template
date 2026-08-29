import jwt
def authserverToken_validateIdToken(token, list_requiredClaims, jwksClient, audience, list_signingAlgorithms):
	# list_requiredIdTokenClaims = ['iss', 'sub', 'aud',f'https://{flaskAppSettings['app_server_url']}/roles']

	try:
		signing_key = jwksClient.get_signing_key_from_jwt(token['id_token'])
		dict_idTokenDecoded = jwt.decode_complete(
			token['id_token'],
			key=signing_key,
			audience=audience,#authServerSettings['oidc_clientID'],
			algorithms=list_signingAlgorithms,
			options={"require":list_requiredClaims},
			)
	except jwt.MissingRequiredClaimError as e:
		return f"AppAuthnERROR: id token - {e}"
	except Exception as e:
		return f'AppAuthnERROR: id token failed to decode - {e}' 

	updatedToken = token.copy()
	updatedToken.update({'idTokenDecoded': dict_idTokenDecoded})

	return updatedToken

def authserverToken_validateAccessToken(token, list_requiredClaims, jwksClient, audience, list_signingAlgorithms):
	# list_requiredIdTokenClaims = ['iss', 'sub', 'aud',f'https://{flaskAppSettings['app_server_url']}/roles']

	try:
		signing_key = jwksClient.get_signing_key_from_jwt(token['access_token'])
		dict_accessTokenDecoded = jwt.decode_complete(
			token['access_token'],
			key=signing_key,
			audience=audience,
			algorithms=list_signingAlgorithms,
			options={"require":list_requiredClaims},
			)
	except jwt.MissingRequiredClaimError as e:
		return f"AppAuthnERROR: access token - {e}"
	except Exception as e:
		return f'AppAuthnERROR: access token failed to decode - {e}' 

	updatedToken = token.copy()
	updatedToken.update({'accessTokenDecoded': dict_accessTokenDecoded})

	return updatedToken
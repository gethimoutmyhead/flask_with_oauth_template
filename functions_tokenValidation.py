import jwt
from loadMyAppSettings import authServerSettings
import httpx
from functools import lru_cache

async def getJWKS(url_for_oidcserver_metadataURL):
	# url_for_oidcserver_metadataURL = f"{authServerSettings['oidc_authserver']}/.well-known/openid-configuration"

	async with httpx.AsyncClient() as client:
		request_oidcserver_metadata = await client.get(url_for_oidcserver_metadataURL)
		oidcserver_metadata = request_oidcserver_metadata.json()
		JWKS_URL = oidcserver_metadata["jwks_uri"]
		response = await client.get(JWKS_URL)
		jwks = response.json()
	return jwks

async def authserverToken_validateIdToken(token, list_requiredClaims, url_oidcserver_metadata, audience, list_signingAlgorithms):
	# url_for_oidcserver_metadataURL = f"{authServerSettings['oidc_authserver']}/.well-known/openid-configuration"

	try:
		headers = jwt.get_unverified_header(token['id_token'])
		token_kid = headers.get("kid")
		jwks = await getJWKS(url_oidcserver_metadata)
		# async with httpx.AsyncClient() as client:
		# 	request_oidcserver_metadata = await client.get(url_for_oidcserver_metadataURL)
		# 	oidcserver_metadata = request_oidcserver_metadata.json()
		# 	JWKS_URL = oidcserver_metadata["jwks_uri"]
		# 	response = await client.get(JWKS_URL)
		# 	jwks = response.json()

		jwk_set = jwt.PyJWKSet(jwks["keys"])
		matching_key = None
		for jwk in jwk_set.keys:
		    if jwk.key_id == token_kid:
		        matching_key = jwk
		        break
		        
		if not matching_key:
		    raise jwt.InvalidTokenError("Signing key not found in JWKS.")

		dict_idTokenDecoded = jwt.decode_complete(
			token['id_token'],
			key=matching_key.key,
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

async def authserverToken_validateAccessToken(token, list_requiredClaims, url_oidcserver_metadata, audience, list_signingAlgorithms):
	# list_requiredIdTokenClaims = ['iss', 'sub', 'aud',f'https://{flaskAppSettings['app_server_url']}/roles']

	url_for_oidcserver_metadataURL = f"{authServerSettings['oidc_authserver']}/.well-known/openid-configuration"

	try:
		headers = jwt.get_unverified_header(token['access_token'])
		token_kid = headers.get("kid")
		jwks = await getJWKS(url_oidcserver_metadata)
		# async with httpx.AsyncClient() as client:
		# 	request_oidcserver_metadata = await client.get(url_for_oidcserver_metadataURL)
		# 	oidcserver_metadata = request_oidcserver_metadata.json()
		# 	JWKS_URL = oidcserver_metadata["jwks_uri"]
		# 	response = await client.get(JWKS_URL)
		# 	jwks = response.json()

		jwk_set = jwt.PyJWKSet(jwks["keys"])
		matching_key = None
		for jwk in jwk_set.keys:
		    if jwk.key_id == token_kid:
		        matching_key = jwk
		        break
		        
		if not matching_key:
			raise jwt.InvalidTokenError("Signing key not found in JWKS.")
		# signing_key = jwksClient.get_signing_key_from_jwt(token['access_token'])
		dict_accessTokenDecoded = jwt.decode_complete(
			token['access_token'],
			key=matching_key.key,
			audience=audience,
			algorithms=list_signingAlgorithms,
			options={"require":list_requiredClaims},
			# **key_entry
			)
	except jwt.MissingRequiredClaimError as e:
		return f"AppAuthnERROR: access token - {e}"
	except Exception as e:
		return f'AppAuthnERROR: access token failed to decode - {e}' 

	updatedToken = token.copy()
	updatedToken.update({'accessTokenDecoded': dict_accessTokenDecoded})

	return updatedToken
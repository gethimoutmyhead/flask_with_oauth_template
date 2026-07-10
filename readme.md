## Flask with OAuth Template

template set up to allow me to make a flask app that has authentication built in

Main branch auth0-oidc is set up to work as an auth0 client

## Completed
2026-07-10
* set up tests for token cookies that are invalid
* page now has a system to validate access token, identity token. it needs more extensive testing, but will check necessary claims, identify if the audience is incorrect. adding code to check roles should be easy, its all functional now huzzah

2026-06-29 
* set up tests to see that auth0 roles are being included in access token
* set up tests to see that auth0 roles are being included in id token
* add access token validation to flask App (can lift this from the test function)

## Things to do
* set up granular tests that check id_token, access_token validity
* authorization tests that utilise permittedRoles, permittedAttributes
* authorization code that uses permittedRoles and permittedAttributes
* template functions that allow user metadata, app metadata modifications
* global variable to set meta tag 'application-name' in templates
* push form that allows user creation
* script that creates new, or updates existing .env files (makes it easier to deploy anywhere)
* script to configure gunicorn.conf.py

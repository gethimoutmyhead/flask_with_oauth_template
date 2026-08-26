## Flask with OAuth Template

template set up to allow me to make a flask app that has authentication built in

Main branch auth0-oidc is set up to work as an auth0 client


## How to use


launch with

```
pipenv shell
gunicorn async-app:app --worker-class asgi --preload
```


test with

```
pytest
```

config files - todo

## Things to do
### tests
* test that logout flow works correctly
* tests to monitor behavior of access token, id token tests that are present but tampered
* tests to monitor behavior of access token, id token tests that are present but have claims missing
* tests to monitor behavior of access token, id token tests that are present but expired

### Functions
* push form that allows user creation
* user creation based on roles
* template functions for client to edit user metadata, app metadata
* script that creates new, or updates existing .env files (makes it easier to deploy anywhere)
* script to configure gunicorn.conf.py
* authorization check that checks permittedAttributes

### refactoring
* the authorization_check has an if for logged out / authenticated / authorized; should be able to refactor these


### Research
* permittedAttributes function testing - need more homework on how I would implement

## Completed
2026-08-26
* re-did everything as ASGI, to allow concurrency and multi-user logins. OUTSTANDING RESULT - a single worker is able to handle 3 users, logged in at once and interacting with the website

2026-08-25
* break-up ROPC test into invalid session cookie test, and a deprecated authenticateByROPCTest function
* permittedRoles test with a 2nd user in a different role
* permittedRoles test where multiple roles can be accepted
* re-engineered tests to use playwright_async api, to allow multiple concurrent tests without breaking code
* test for users with multiple roles will accessing authorized pages works correctly

2026-08-23
* new testing method using playwright - user logs in manually, allows MFA and other stuff, introspection when errors happen
* deprecated the oauth by pkce grant; may need in future, but can do without this right now.
* completed authenticateUserWithRoleDoctor test function
* added a login hint parameter to the login page, which should auto-fill username. helpful for my test functions

2026-08-22
* rename wsgi_002 and application_002
* added how-to-use in readme.md

2026-08-19
* completed OAuth by PKCE grant as a test option - now can do testing with MFA

2026-08-18
* refactored location of .env files to sit in root folder, rather than everywhere. should facilitate writing script for writing and updating .env files
* split tests up into unit and integration tests; latter when we directly test server responses
* basic code to facilitate Proof-Key for Code Exchange (PKCE) grants, tested elsewhere
* modified readme to display the to-do list first. edited and re-ordered to-do list

2026-08-11
* global variable to set meta tag 'application-name' in templates
* tests for meta Tags

2026-07-14
* authorization tests that checks permittedRoles works correctly
* authorization code to verify permittedRoles
* re-organised todo list into tests and functions

2026-07-13
* set up tests that confirm authserver_token cookies that are malformed will be rejected
2026-07-10
* set up tests for token cookies that are invalid
* page now has a system to validate access token, identity token. it needs more extensive testing, but will check necessary claims, identify if the audience is incorrect. adding code to check roles should be easy, its all functional now huzzah

2026-06-29 
* set up tests to see that auth0 roles are being included in access token
* set up tests to see that auth0 roles are being included in id token
* add access token validation to flask App (can lift this from the test function)
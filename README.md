# Railsbank Mock Card Endpoints
This is Mock API framework to emulate the Railsbank play APIs.
It uses the Zappa Serverless Framework to allow you to only pay for the milliseconds of usage that you need.
On top of this an endpoint is created in AWS api gateway so that you can invoke this framework via API calls.

This is designed for use by staging environments and automated testing suites
##### FOR THE LOVE OF GOD, NEVER USE THIS IN PRODUCTION!!
#
#
To deploy this new lambda function:
### INSTALLATION
* Ensure you are working within a virtualenv
* Install stuff from the requirements.txt attached
* Ensure that you have aws creds configures in ~/.aws/credentials
* These AWS creds need full lambda access
* Create or specify a S3 bucket to be used for data card details

### APPLY CREDS
* Replace `{Your S3 Bucket}` in zappa_settings.json with your bucket name
* Replace `{Your customer ID for railsbank}` in flask_app/RailsbankCardStubs.py
* Replace `{Your webhook secret for your Railsbank play account }` in flask_app/RailsbankCardStubs.py
* Replace `{Your s3 bucket name}` in flask_app/s3.py
* Replace `{your railsbank staging API key}` with your railsbank play api key


### TAKEOFF!
* run `zappa init`
* run `zappa deploy`

### Optional extras
If you are like me and have the short term memory of a goldfish, you can add a custom url for this suite.
To do this:
* Create a `Customer Domain Name` in API gateway
* Attach your appropriate TLS certificate in AWS Certificate manager
* Wherever you set your domains DNS settings, create a CNAME record to the `API Gateway domain name` cloudfront url that was created with your API gateway Customer Domain Name.

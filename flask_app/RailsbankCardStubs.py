__author__ = "Bruce Pannaman"

from flask import Flask, request, jsonify
import secrets
import json
import os
from flask_app.testConditions import TestConditions
from flask_app.s3 import s3
import datetime
import boto3
import random
from random import randint

app = Flask(__name__)

"""
THIS SMALL FLASK APP MOCKS THE RAILSBANK CARDS APIS THAT ARE CURRENTLY NOT AVAILIABLE IN THE PLAY ENVIRONMENT

METHODS AVAILIABLE:
* GET NEW CARD - https://docs.railsbank.com/api/cards/adds-a-new-card-to-the-ledger
* GET CARD DETAILS - https://docs.railsbank.com/api/cards/get-card-details
* GET CARD IMAGE - https://docs.railsbank.com/api/cards/get-card-image-the-temporary-image-url-is-valid-for-10-minutes
* GET CARD DETAILS FROM TOKEN - https://docs.railsbank.com/api/cards/get-card-details-from-token
* ACTIVATE CARD - https://docs.railsbank.com/api/cards/activate-card
* GET PIN - https://docs.railsbank.com/api/cards/get-pin-for-the-physical-card
* SUSPEND CARD - https://docs.railsbank.com/api/cards/suspend-card

"""

temporary_storage_location = "/tmp/temp_storage"
owner_id = "{Your customer ID for railsbank}"
staging_webhook_secret = "{Your webhook secret for your Railsbank play account }"
async_timeout = 10


def create_response(success, error, success_response):
    """
    Creates a Flask JSON response to send back the call originator

    :param success: if the call logic deemed it a success <bool>
    :param error: The error message if the call was not successful <str>
    :param success_response: The response payload is the call was a success <obj>
    :return: Fully ready Flask API return object
    """
    if error:
        return jsonify(success=success,
                       message=error,
                       ), 404
    else:
        return success_response, 200


def create_card_file(card_id, data):
    """
    Creates a file in s3 to represent_card_details

    :param card_id: the card_id to create
    :param details: The <json> object of the card
    :return: None
    """
    if os.path.isdir(temporary_storage_location) is False:
        os.mkdir("%s" % (temporary_storage_location))

    with open('%s/%s.json' % (temporary_storage_location, card_id), 'w') as outfile:
        json.dump(data, outfile)

    es3 = s3()
    es3.upload_to_s3(card_id)


def open_temp_card_details(card_id):
    """
    This accesses the local storage files and returns the card details saved to local disk

    :param card_id: CardId to fetch
    :return: Card Object <obj>
    """
    try:
        if os.path.isfile("%s/%s.json" % (temporary_storage_location, card_id)):
            with open("%s/%s.json" % (temporary_storage_location, card_id), "r") as filo:
                card_details = json.load(filo)

            return card_details
        else:
            if os.path.isdir(temporary_storage_location) is False:
                os.mkdir("%s" % (temporary_storage_location))

            es3 = s3()
            if es3.get_file(card_id):
                open_temp_card_details(card_id)
            else:
                return None

    except json.decoder.JSONDecodeError as e:
        print(e)
        return None


def updateJsonFile(card_id, updates):
    """
    This allows you to access a local storage file and update it with new values

    :param card_id: The cardId to update
    :param updates: A JSON object with the changes to create
    :return: None
    """
    card_details = open_temp_card_details(card_id)
    if card_details is None:
        card_details = open_temp_card_details(card_id)

    for update in updates:
        card_details[update] = updates[update]

    create_card_file(card_id, card_details)


def sendAsyncCall(url, headers={}, message={}, method="POST", ):
    """
    Sends message to Lambda_Async_Call_Maker Lambda to wait to send call

    :param message:
    :return: None
    """
    client = boto3.client('lambda')
    headers["Content-Type"] = "application/json"
    headers["Accept"] = "application/json"

    message["secret"] = staging_webhook_secret

    payload = json.dumps({"method": method,
                          "url": url,
                          "timeout": async_timeout,
                          "api_payload": json.dumps(message),
                          "api_headers": headers})

    client.invoke(
        FunctionName="Lambda_Async_Call_Maker",
        InvocationType='Event',
        Payload=payload
    )


@app.route('/', methods=['GET'])
def health_check():
    return jsonify(success=True,
                   message="Hello there",
                   ), 200


@app.route('/v1/customer/cards', methods=['POST'])
def issue_card():
    """
    Emulates - https://docs.railsbank.com/api/cards/adds-a-new-card-to-the-ledger

    :return:
    """
    tc = TestConditions(request.get_json(), "add_card.json", request.headers)
    success, errors = tc.data_type_checks()

    card_id = secrets.token_urlsafe(16)
    card_token = random.randint(9999, 99999)

    if success:
        data = request.get_json()
        data["card_status"] = "card-status-awaiting-activation"
        data["card_id"] = card_id
        data["card_token"] = card_token

        create_card_file(card_id, data)

        message = {
            "card_id": card_id,
            "ledger_id": request.get_json().get("ledger_id"),
            "owner": owner_id,
            "type": "card-awaiting-activation",
            "created_at": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S.000Z")
        }

        sendAsyncCall("https://transactions-staging.storkcard.com/", message=message)

    return create_response(success, errors, jsonify(card_id=card_id))


@app.route('/v1/customer/cards/<card_id>', methods=['GET'])
def get_card(card_id):
    """
    Emulates - https://docs.railsbank.com/api/cards/get-card-details

    :param card_id: card_id given in URL string
    :return:
    """
    tc = TestConditions({"card_id": card_id}, "get_card.json", request.headers)
    success, errors = tc.data_type_checks()

    if success:
        card_details = open_temp_card_details(card_id)

        # WIERD TECH DEBT, NEEDS TO BE CALLED TWICE TO GET ANSWER WHEN REQUESTING FROM S3
        if card_details is None:
            card_details = open_temp_card_details(card_id)
        if card_details is None:
            return create_response(False, "Card doesn't exist in temporary Storage", {})
        else:
            return create_response(success, errors, jsonify(card_details))

    else:
        return create_response(success, errors, {})


@app.route('/v1/customer/cards/by-token/<card_token>', methods=['GET'])
def get_card_from_token(card_token):
    """
    Emulates - https://docs.railsbank.com/api/cards/get-card-details-from-token

    :param card_token: card_token given in URL string
    :return:
    """
    tc = TestConditions({"card_token": card_token}, "get_card_by_token.json", request.headers)
    success, errors = tc.data_type_checks()

    if success:
        for filename in os.listdir(temporary_storage_location):
            card_details = open_temp_card_details(filename.replace(".json", ""))
            if card_details is not None and card_details["card_token"] == card_token:
                return create_response(success, errors, jsonify(card_details))

        return create_response(False, "Card doesn't exist in temporary Storage", {})


@app.route('/v1/customer/cards/<card_id>/image', methods=['GET'])
def get_card_image(card_id):
    """
    Emulates - https://docs.railsbank.com/api/cards/get-card-image-the-temporary-image-url-is-valid-for-10-minutes

    Returns the same image each and every time Not personalised

    :param card_id: card_id: card_id given in URL string
    :return:
    """
    card_url = "https://assets.storkcard.com/App_Static_Assets/StorkCard_Virtual_Card2.png"
    tc = TestConditions({"card_id": card_id}, "get_card_image.json", request.headers)
    success, errors = tc.data_type_checks()

    return create_response(success, errors, jsonify(temp_card_image_url=card_url))


@app.route('/v1/customer/cards/<card_id>/activate', methods=['POST'])
def activate_card(card_id):
    """
    Emulates - https://docs.railsbank.com/api/cards/activate-card

    :param card_id: card_id: card_id given in URL string
    :return:
    """
    tc = TestConditions({"card_id": card_id}, "activate_card.json", request.headers)
    success, errors = tc.data_type_checks()

    if success:
        updateJsonFile(card_id, {"card_status": "card-status-active"})

    message = {
        "card_id": card_id,
        "owner": owner_id,
        "type": "card-activated",
        "created_at": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S.000Z")
    }

    sendAsyncCall("https://transactions-staging.storkcard.com/", message=message)

    return create_response(success, errors, jsonify(card_id=card_id))


@app.route('/v1/customer/cards/<card_id>/suspend', methods=['POST'])
def suspend_card(card_id):
    """
    Emulates - https://docs.railsbank.com/api/cards/suspend-card

    :param card_id: card_id: card_id given in URL string
    :return:
    """
    tc = TestConditions({"card_id": card_id}, "suspend_card.json", request.headers)
    success, errors = tc.data_type_checks()

    if success:
        updateJsonFile(card_id, {"card_status": "card-status-suspended"})

        message = {
            "card_id": card_id,
            "owner": owner_id,
            "type": "card-suspended",
            "created_at": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S.000Z")
        }

        sendAsyncCall("https://transactions-staging.storkcard.com/", message=message)

    return create_response(success, errors, jsonify(card_id=card_id))


@app.route('/v1/customer/cards/<card_id>/pin', methods=['GET'])
def get_pin(card_id):
    """
    Emulates - https://docs.railsbank.com/api/cards/get-pin-for-the-physical-card

    :param card_id: card_id: card_id given in URL string
    :return:
    """
    tc = TestConditions({"card_id": card_id}, "get_pin.json", request.headers)
    success, errors = tc.data_type_checks()

    pin = randint(1000, 9999)

    return create_response(success, errors, jsonify(pin=pin))


if __name__ == '__main__':
    app.run()

#!/usr/bin/env python
from twilio.rest import Client
client = Client()

import os

#TODO: Sanity checking using os.environ.get

toNumber = os.environ['TWILIO_TO_NUMBER']
fromNumber = os.environ['TWILIO_FROM_NUMBER']

def sendMessage(body):
    client.api.account.messages.create(
            to=toNumber,
            from_=fromNumber,
            body=body)

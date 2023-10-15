import json
import asyncio

import graphene
from payment.types import CreditCardType, StatusReturnType
import logging
import os

from dotenv import load_dotenv
from payment.resolvers import ApplicationConfigResolvers, logic_resolve_member, resolve_wallet_accounts
from payment.constants import Constants
from payment.rtrPayments import RtrPayments
from payment.utils import get_softheon_identity
from harmoney.aiohttp_client import AioHttpClient
from harmoney.exceptions import DupicateObjectException, InvalidCreditCardTypeException, NoneReturnTypeException


EVENT_LOOP = None

try:
    EVENT_LOOP = asyncio.get_running_loop()
except RuntimeError:
    EVENT_LOOP = asyncio.new_event_loop()
    asyncio.set_event_loop(EVENT_LOOP)

load_dotenv()

RTR = RtrPayments()
HTTP = AioHttpClient()
SOFTHEON_WALLET_HOST = os.environ.get("SOFTHEON_WALLET_HOST")
SOFTHEON_WALLET_PREFIX = os.environ.get("SOFTHEON_WALLET_PREFIX")

SOFTHEON_PAYMENT_SCOPE = Constants.SOFTHEON_PAYMENT_SCOPE.value
APPLICATION_JSON_CONTENT_TYPE = "application/json"

logger = logging.getLogger(__name__)


class CreateCreditCard(graphene.Mutation):

    class Arguments:
        member_id = graphene.String(required=True)
        card_number = graphene.String(required=True)
        security_code = graphene.String(required=True)
        expiration_month = graphene.String(required=True)
        expiration_year = graphene.String(required=True)
        card_holder_name = graphene.String(required=True)
        address1 = graphene.String(required=True)
        address2 = graphene.String(required=False)
        city = graphene.String(required=True)
        state = graphene.String(required=True)
        zip_code = graphene.String(required=True)
        email = graphene.String(required=True)

    credit_card = graphene.Field(CreditCardType)

    def mutate(self, info, member_id, card_number, security_code, expiration_month,
              expiration_year, card_holder_name, address1, city, state, zip_code,
              email, address2 = ""):
        card_object = {
            "cardNumber": f"{card_number}",
            "securityCode": f"{security_code}",
            "expirationMonth": f"{expiration_month}",
            "expirationYear": f"{expiration_year}",
            "cardHolderName": f"{card_holder_name}",
            "billingAddress": {
                "address1": f"{address1}",
                "address2": f"{address2}",
                "city": f"{city}",
                "state": f"{state}",
                "zipCode": f"{zip_code}"
            },
            "email": f"{email}"
        }
        member = EVENT_LOOP.run_until_complete(
            logic_resolve_member(
                member_id
            )
        )
        response = EVENT_LOOP.run_until_complete(
            CreateCreditCard.format_add_credit_card(
                member, card_object
            )
        )
        credit_card = CreditCardType(**response)
        return CreateCreditCard(credit_card=credit_card)
    

    @staticmethod
    async def format_add_credit_card(member, card_object):
        payment_config= await ApplicationConfigResolvers.logic_resolve_application_config(member)
        wallet = await resolve_wallet_accounts(member)
        tokenized_cc = await CreateCreditCard._tokenize_credit_card(card_object, payment_config)
        if tokenized_cc['cardType'] == "AMEX":
            raise InvalidCreditCardTypeException("Support for American Express (AMEX) does not exist")
        active_tokens = [cc['token'] for cc in wallet['creditCards']]
        if tokenized_cc['token'] in active_tokens:
            raise DupicateObjectException(f"credit card ending with {tokenized_cc['cardNumber']} already exists")

        token = await get_softheon_identity(member, SOFTHEON_PAYMENT_SCOPE)
        url = f'{SOFTHEON_WALLET_HOST}{SOFTHEON_WALLET_PREFIX}/v4/wallet/{wallet["id"]}/creditCard'
        card_to_post = {"paymentToken": str(tokenized_cc['token']),
                        "isDefault": True}
        request_options = {
            'method': "post",
            'data': json.dumps(card_to_post),
            'headers': {
                'Authorization': f'Bearer {token}',
                'Content-Type': APPLICATION_JSON_CONTENT_TYPE
            }
        }

        data = await HTTP.run_instance(url, request_options)
        data = data["data"]
        cards = data['creditCards']
        target_card = cards[-1]
        card_to_return = {
                    'cardHolderName': target_card.get('cardHolderName'),
                    'maskedCardNumber': target_card.get('cardNumber'),
                    'cardState': target_card.get('cardState'),
                    'cardType': target_card.get('cardType'),
                    'createdAt': target_card.get('createdTime'),
                    'email': target_card.get('email'),
                    'expirationMonth': target_card.get('expirationMonth'),
                    'expirationYear': target_card.get('expirationYear'),
                    'memberId': target_card.get('id'),
                    'modifiedOn': target_card.get('modifiedTime'),
                    'token': target_card.get('token'),
                    'isDefault': target_card.get('isDefault', True)
        }
        return card_to_return

    @staticmethod
    async def _tokenize_credit_card(card_object, payment_config):
        payment_tokenization_url = payment_config["creditCardTokenizationURL"]
        payment_token = payment_config['paymentClientId']
        request_options = {
            'method': "post",
            'data': json.dumps(card_object),
            'headers': {
                'Authorization': f'Bearer {payment_token}',
                'Content-Type': APPLICATION_JSON_CONTENT_TYPE
            }
        }
        data = await HTTP.run_instance(payment_tokenization_url, request_options)
        if data is None:
            raise NoneReturnTypeException('Unable to tokenize credit card. Verify all required data is entered correctly')
        return data['data']


class DeleteCreditCard(graphene.Mutation):
    class Arguments:
        member_id = graphene.String()
        token = graphene.String()

    card_status = graphene.Field(StatusReturnType)

    def mutate(self, info, member_id, token):
        member = EVENT_LOOP.run_until_complete(
            logic_resolve_member(member_id)
        )
        resp = EVENT_LOOP.run_until_complete(
            DeleteCreditCard.format_delete_credit_card(
                member, token
            )
        )
        status_resp = StatusReturnType(**resp)
        return DeleteCreditCard(card_status=status_resp)


    @staticmethod
    async def format_delete_credit_card(member, cc_token):
        wallet = await resolve_wallet_accounts(member)
        active_tokens = [cc['token'] for cc in wallet['creditCards']]
        token = await get_softheon_identity(member, SOFTHEON_PAYMENT_SCOPE)
        if cc_token not in active_tokens:
            return {'status': '400', 'error': f'credit card token: {cc_token} does not exist in the members wallet'}
        wallet_id = wallet['id']

        card_to_delete = [card for card in wallet['creditCards'] if card['token'] == cc_token]
        card_id = card_to_delete[0]['id']

        url = f'{SOFTHEON_WALLET_HOST}{SOFTHEON_WALLET_PREFIX}/v4/wallet/{wallet_id}/creditCard/{card_id}'
        request_options = {
            'method': "delete",
            'data': json.dumps({}),
            'headers': {
                'Authorization': f'Bearer {token}',
                'Content-Type': APPLICATION_JSON_CONTENT_TYPE
            }
        }
        await HTTP.run_instance(url, request_options)
        return {'status': '200', 'error': ''}


class Mutation(graphene.ObjectType):
    create_credit_card = CreateCreditCard.Field()
    remove_credit_card = DeleteCreditCard.Field()

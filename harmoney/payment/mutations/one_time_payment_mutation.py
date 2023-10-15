import json
import asyncio

import graphene
from payment.types import OneTimePaymentType
from payment.types import PaymentMethodType
import logging
import os

from dotenv import load_dotenv
from payment.resolvers import CreditCardResolvers, logic_resolve_member
from payment.constants import Constants, APPLICATION_JSON_CONTENT_TYPE
from payment.rtrPayments import RtrPayments
from payment.utils import get_softheon_identity
from harmoney.aiohttp_client import AioHttpClient
from harmoney.exceptions import InvalidFieldForObject, InvalidFormatException


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

logger = logging.getLogger(__name__)


class ExecuteOneTimePayment(graphene.Mutation):

    class Arguments:
        member_id = graphene.String(required=True)
        payment_amount = graphene.Float()
        payment_date = graphene.String(required=False)
        description = graphene.String(required=False)
        payment_token = graphene.String()
        payment_type = graphene.String()
        source = graphene.String()
        properties = graphene.JSONString(required=False)

    payment = graphene.Field(OneTimePaymentType)
    

    def mutate(self, info, member_id, payment_amount, payment_date, description,
             payment_token, payment_type, source, properties):
        
        member = EVENT_LOOP.run_until_complete(
            logic_resolve_member(
                member_id
            )
        )
        ref_id = EVENT_LOOP.run_until_complete(
            RTR.get_member_ref_id(member)
        )
        payment_object = {
            "paymentAmount": payment_amount,
            "paymentDate": f"{payment_date}",
            "description": f"{description}",
            "paymentMethod": {
                "paymentToken": f"{payment_token}",
                "type": f"{payment_type}"
            },
            "referenceId": f"{ref_id}",
            "source": "Online",
            "properties": {}
        }

        credit_cards = EVENT_LOOP.run_until_complete(
            CreditCardResolvers.format_credit_cards(member)
        )
        active_tokens = [cc['token'] for cc in credit_cards]
        if payment_token not in active_tokens:
            raise InvalidFieldForObject(f'Credit card token: {payment_token} does not exist for the current member')
        if payment_amount <= 0:
             raise InvalidFieldForObject(f'Payment amount must be larger than 0')
        
        response = EVENT_LOOP.run_until_complete(
            ExecuteOneTimePayment.format_payment(
                member, payment_object
            )
        )
        payment = ExecuteOneTimePayment.create_payment_object(response)
        return ExecuteOneTimePayment(payment=payment)
    

    @staticmethod
    async def format_payment(member, card_object):
        token = await get_softheon_identity(member, SOFTHEON_PAYMENT_SCOPE)
        url = f"{SOFTHEON_WALLET_HOST}{SOFTHEON_WALLET_PREFIX}/v3/payments"
        request_options = {
            'method': "post",
            'data': json.dumps(card_object),
            'headers': {
                'Authorization': f'Bearer {token}',
                'Content-Type': APPLICATION_JSON_CONTENT_TYPE
            }
        }
        data = await HTTP.run_instance(url, request_options)
        if data is None:
            raise InvalidFormatException('Request could not go though. Verify all data entered is correct')
        data = data['data']
        return data
    
    @staticmethod
    def create_payment_object(data_object):
        pm = {
                "type": f'{data_object["paymentMethod"]["type"]}',
                "token": f'{data_object["paymentMethod"]["paymentToken"]}',
                "source": f'{data_object["source"]}'
            }
        payment_method = PaymentMethodType(**pm)
        object_shell = {
            "accountId": f'{data_object["accountId"]}',
            "paymentAmount": f'{data_object["paymentAmount"]}',
            "description": f'{data_object["description"]}',
            "referenceId": f'{data_object["referenceId"]}',
            "_id": f'{data_object["id"]}',
            "confirmationNumber": f'{data_object["confirmationNumber"]}',
            "createdDate": f'{data_object["createdDate"]}',
            "modifiedDate": f'{data_object["modifiedDate"]}',
            "paymentDate": f'{data_object["paymentDate"]}',
            "paymentMethod": payment_method
        }
        payment = OneTimePaymentType(**object_shell)
        return payment

class Mutation(graphene.ObjectType):
    create_one_time_payment = ExecuteOneTimePayment.Field()


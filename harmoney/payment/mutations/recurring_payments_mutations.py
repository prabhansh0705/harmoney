import json
import asyncio

import graphene
import requests

from payment.types import RecurringPaymentReturnType, StatusReturnType
import logging
import os
from payment.resolvers import CreditCardResolvers, logic_resolve_member, RecurringPaymentsResolver, ApplicationConfigResolvers, BankAccountsResolver

from dotenv import load_dotenv
from payment.constants import Constants, ValidInputs
from payment.rtrPayments import RtrPayments
from payment.utils import get_softheon_identity
from harmoney.aiohttp_client import AioHttpClient
from harmoney.exceptions import InvalidFieldForObject, InvalidTokenException, PaymentNotFoundException


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


def validate_payment_object(member, payment_obj):

    if payment_obj['paymentType'].lower() == 'credit card':
        credit_cards = EVENT_LOOP.run_until_complete(
            CreditCardResolvers.format_credit_cards(member)
        ) 
        active_tokens = [cc['token'] for cc in credit_cards]
        if payment_obj['paymentToken'] not in active_tokens:
            raise InvalidTokenException(f'Credit card token: {payment_obj["paymentToken"]} '
                                    f'does not exist for the current member')
    elif payment_obj['paymentType'].lower() == 'ach':
        bank_accounts = EVENT_LOOP.run_until_complete(
            BankAccountsResolver.format_bank_accounts(member)
        )
        active_bank_tokens = [ba['token'] for ba in bank_accounts]
        if payment_obj['paymentToken'] not in active_bank_tokens:
            raise InvalidTokenException(f'Bank account token: {payment_obj["paymentToken"]} '
                                    f'does not exist for the current member')
    else:
        raise InvalidFieldForObject(f'Invalid Payment Type: {payment_obj["paymentType"]} was entered')

    if payment_obj['amount'] <= 0.0:
        raise InvalidFieldForObject('Amount entered must be larger than 0')
    if payment_obj['state'].lower() not in ValidInputs.valid_states.value:
        raise InvalidFieldForObject(f'Invalid State: {payment_obj["state"]} was entered')
    #TODO: Not all months have 31 days
    if payment_obj['runDay'] < 1 or payment_obj['runDay'] > 31:
        raise InvalidFieldForObject(f'Invalid Day: {payment_obj["runDay"]} was entered. Must be between 1 and 31')


def get_create_payment_obj(
        name, description, run_day, end_date, state, payment_type,
        payment_token, amount_type, amount, ref_id):
    payment_object = {
        "name": f"{name}",
        "properties": {},
        "runDay": run_day,
        "state": f"{state}",
        "paymentType": f"{payment_type}",
        "paymentToken": f"{payment_token}",
        "amountType": f"{amount_type}",
        "source": "Online",
        "referenceId": f"{ref_id}"
    }
    if end_date != '':
        payment_object['endDate'] = f'{end_date}'
    if description != '':
        payment_object['description'] = description
    if amount != 0.0:
        payment_object["amount"] = amount

    return payment_object


class CreateRecurringPayment(graphene.Mutation):
    class Arguments:
        member_id = graphene.String(required=True)
        name = graphene.String(required=True)
        description = graphene.String(required=False)
        run_day = graphene.Int(required=True)
        state = graphene.String(required=True)
        payment_type = graphene.String(required=True)
        payment_token = graphene.String(required=True)
        amount_type = graphene.String(required=True)
        amount = graphene.Float(required=False)
        end_date = graphene.String(required=False)

    rec_payment = graphene.Field(RecurringPaymentReturnType)

    def mutate(self, info, member_id, name, amount_type, run_day,
               state, payment_type, payment_token, amount=0,
               end_date='', description=''):
        member = EVENT_LOOP.run_until_complete(
            logic_resolve_member(
                member_id
            )
        )
        ref_id = EVENT_LOOP.run_until_complete(
            RTR.get_member_ref_id(
                member
            )
        )
        payment_object = get_create_payment_obj(
            name, description, run_day, end_date, state,
            payment_type, payment_token, amount_type, amount, ref_id)

        validate_payment_object(member, payment_object)
        #currently this value is not used, but the action must take place and this var may be needed later
        response = EVENT_LOOP.run_until_complete(
            CreateRecurringPayment.create_recurring_payment(
                member, payment_object
            )
        )
        ret_response = EVENT_LOOP.run_until_complete(
            CreateRecurringPayment.format_response_object(member)
        )
        rec_payment = RecurringPaymentReturnType(**ret_response)

        return CreateRecurringPayment(rec_payment=rec_payment)
    
    @staticmethod
    async def create_recurring_payment(member, payment_obj):
        token = await get_softheon_identity(member, SOFTHEON_PAYMENT_SCOPE)
        url = f'{SOFTHEON_WALLET_HOST}{SOFTHEON_WALLET_PREFIX}/v4/subscriptions'
        request_options = {
            'method': "post",
            'data': json.dumps(payment_obj),
            'headers': {
                'Authorization': f'Bearer {token}',
                'Content-Type': APPLICATION_JSON_CONTENT_TYPE
            }
        }
        data = await HTTP.run_instance(url, request_options)
        return_data = data["data"]
        return return_data

    @staticmethod
    async def format_response_object(member):
        new_autopay_object_list = await RecurringPaymentsResolver.format_recurring_payments(member)
        if not new_autopay_object_list:
            raise PaymentNotFoundException('Recurring payment was not created properly and could not be fetched')
        new_autopay_object = new_autopay_object_list[0]
        app_config = await ApplicationConfigResolvers.logic_resolve_application_config(member)
        new_autopay_object["paymentClientId"] = app_config["paymentClientId"]
        return new_autopay_object


class UpdateRecurringPayment(graphene.Mutation):

    class Arguments:
        member_id = graphene.String(required=True)
        payment_id = graphene.Int(required=True)
        name = graphene.String(required=True)
        description = graphene.String(required=False)
        run_day = graphene.Int(required=True)
        state = graphene.String(required=True)
        payment_type = graphene.String(required=True)
        payment_token = graphene.String(required=True)
        amount_type = graphene.String(required=True)
        amount = graphene.Float(required=False)
        end_date = graphene.String(required=False)

    payment_update_status = graphene.Field(StatusReturnType)

    def mutate(self, info, member_id, payment_id, name, run_day,
               state, payment_type, payment_token, amount_type, amount=0,
               end_date="", description=""):

        member = EVENT_LOOP.run_until_complete(
            logic_resolve_member(
                member_id
            )
        )
        ref_id = EVENT_LOOP.run_until_complete(
            RTR.get_member_ref_id(
                member
            )
        )
        payment_object = get_create_payment_obj(
            name, description, run_day, end_date, state,
            payment_type, payment_token, amount_type, amount, ref_id)
        # adding extra fields required to update
        payment_object['id'] = payment_id

        validate_payment_object(member, payment_object)
        response = EVENT_LOOP.run_until_complete(
            UpdateRecurringPayment.format_recurring_payment_update(
                member, payment_object
            )
        )
        status_resp = StatusReturnType(**{
            "status": response.status_code,
            "error": response.text
        })
        return UpdateRecurringPayment(payment_update_status=status_resp)
        

    @staticmethod
    async def format_recurring_payment_update(member, payment_obj):
        token = await get_softheon_identity(member, SOFTHEON_PAYMENT_SCOPE)
        url = f'{SOFTHEON_WALLET_HOST}{SOFTHEON_WALLET_PREFIX}/v4/subscriptions'
        data = json.dumps(payment_obj)
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': APPLICATION_JSON_CONTENT_TYPE
        }
        response = requests.put(url, data=data, headers=headers)
        return response


class DeleteRecurringPayment(graphene.Mutation):

    class Arguments:
        # TODO: Since we can't find any documentation for delete
        #  API, using default arguments used in Update API
        member_id = graphene.String(required=True)
        payment_id = graphene.Int(required=True)
        name = graphene.String(required=True)
        description = graphene.String(required=False)
        run_day = graphene.Int(required=True)
        payment_type = graphene.String(required=True)
        payment_token = graphene.String(required=True)
        amount_type = graphene.String(required=True)
        amount = graphene.Float(required=False)
        end_date = graphene.String(required=False)

    payment_delete_status = graphene.Field(StatusReturnType)

    def mutate(self, info, member_id, payment_id, name, run_day,
               payment_type, payment_token, amount_type, amount=0,
               end_date="", description=""):
        member = EVENT_LOOP.run_until_complete(
            logic_resolve_member(
                member_id
            )
        )
        ref_id = EVENT_LOOP.run_until_complete(
            RTR.get_member_ref_id(
                member
            )
        )
        # this is to make sure, subscription becomes inactive
        state = "inactive"
        payment_object = get_create_payment_obj(
            name, description, run_day, end_date, state,
            payment_type, payment_token, amount_type, amount, ref_id)
        # adding extra fields required to update
        #TODO: verify the payment ID actually exists
        payment_object['id'] = payment_id

        validate_payment_object(member, payment_object)
        response = EVENT_LOOP.run_until_complete(
            UpdateRecurringPayment.format_recurring_payment_update(
                member, payment_object
            )
        )
        status_resp = StatusReturnType(**{
            "status": response.status_code,
            "error": response.text
        })
        return DeleteRecurringPayment(payment_delete_status=status_resp)
    

class Mutation(graphene.ObjectType):
    create_recurring_payment = CreateRecurringPayment.Field()
    update_recurring_payment = UpdateRecurringPayment.Field()
    delete_recurring_payment = DeleteRecurringPayment.Field()
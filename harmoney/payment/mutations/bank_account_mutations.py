import json
import asyncio

import graphene
from payment.types import BankAccountType, StatusReturnType
import logging
import os

from dotenv import load_dotenv
from payment.resolvers import ApplicationConfigResolvers, logic_resolve_member, resolve_wallet_accounts
from payment.constants import Constants
from payment.rtrPayments import RtrPayments
from payment.utils import get_softheon_identity
from harmoney.aiohttp_client import AioHttpClient
from harmoney.exceptions import DupicateObjectException, NoneReturnTypeException


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


class CreateBankAccount(graphene.Mutation):

    class Arguments:
        member_id = graphene.String(required=True)
        accountNumber = graphene.String(required=True)
        routingNumber = graphene.String(required=True)
        accountHolderName = graphene.String(required=True)
        type = graphene.String(required=True)
        nickname = graphene.String(required=True)
        address1 = graphene.String(required=True)
        address2 = graphene.String(required=False)
        city = graphene.String(required=True)
        state = graphene.String(required=True)
        zip_code = graphene.String(required=True)
        email = graphene.String(required=True)

    bank_account = graphene.Field(BankAccountType)

    def mutate(self, info, member_id, accountNumber, routingNumber, accountHolderName,
              type, nickname, address1, city, state, zip_code,
              email, address2=""):
        bank_account_object = {
            "accountNumber": f"{accountNumber}",
            "routingNumber": f"{routingNumber}",
            "accountHolderName": f"{accountHolderName}",
            "type": f"{type}",
            "nickname": f"{nickname}",
            "accountHolderAddress": {
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
            CreateBankAccount.format_add_bank_account(
                member, bank_account_object
            )
        )
        bank_account = BankAccountType(**response)
        return CreateBankAccount(bank_account=bank_account)
    

    @staticmethod
    async def format_add_bank_account(member, bank_account_object):
        payment_config = await ApplicationConfigResolvers.logic_resolve_application_config(member)
        wallet = await resolve_wallet_accounts(member)
        tokenized_ba = await CreateBankAccount._tokenize_bank_account(bank_account_object, payment_config)
        token = await get_softheon_identity(member, SOFTHEON_PAYMENT_SCOPE)
        url = f'{SOFTHEON_WALLET_HOST}{SOFTHEON_WALLET_PREFIX}/v4/wallet/{wallet["id"]}/BankAccount'
        card_to_post = {"paymentToken": str(tokenized_ba['token']),
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
        bank_accounts = data["bankAccounts"]
        bank_account = bank_accounts[-1]
        bank_account_to_return = {
            'memberId': bank_account.get('id'),
            'token': bank_account.get('token'),
            'accountHolderName': bank_account.get('accountHolderName'),
            'accountState': bank_account.get('state'),
            'accountType': bank_account.get('type'),
            'nickName': bank_account.get('nickname'),
            'routingNumber': bank_account.get('routingNumber'),
            'accountNumber': bank_account.get('accountNumber'),
            'email': bank_account.get('email'),
            'createdAt': bank_account.get('createdTime'),
            'modifiedOn': bank_account.get('modifiedTime')
        }
        return bank_account_to_return

    @staticmethod
    async def _tokenize_bank_account(bank_account_object, payment_config):
        payment_tokenization_url = payment_config["bankAccountTokenizationURL"]
        payment_token = payment_config['paymentClientId']
        request_options = {
            'method': "post",
            'data': json.dumps(bank_account_object),
            'headers': {
                'Authorization': f'Bearer {payment_token}',
                'Content-Type': APPLICATION_JSON_CONTENT_TYPE
            }
        }
        data = await HTTP.run_instance(payment_tokenization_url, request_options)
        if data is None:
            raise NoneReturnTypeException(
                'Unable to tokenize bank account. '
                'Verify all required data is entered correctly')
        return data['data']


class DeleteBankAccount(graphene.Mutation):
    class Arguments:
        member_id = graphene.String()
        token = graphene.String()

    bank_account_status = graphene.Field(StatusReturnType)

    def mutate(self, info, member_id, token):
        member = EVENT_LOOP.run_until_complete(
            logic_resolve_member(member_id)
        )
        resp = EVENT_LOOP.run_until_complete(
            DeleteBankAccount.format_delete_bank_account(
                member, token
            )
        )
        status_resp = StatusReturnType(**resp)
        return DeleteBankAccount(bank_account_status=status_resp)


    @staticmethod
    async def format_delete_bank_account(member, ba_token):
        wallet = await resolve_wallet_accounts(member)
        active_tokens = [ba['token'] for ba in wallet['bankAccounts']]
        token = await get_softheon_identity(member, SOFTHEON_PAYMENT_SCOPE)
        if ba_token not in active_tokens:
            return {'status': '400', 'error': f'Bank Account token: {ba_token} does not exist in the members wallet'}
        wallet_id = wallet['id']

        bank_account_to_delete = [ba for ba in wallet['bankAccounts'] if ba['token'] == ba_token]
        bank_account_id = bank_account_to_delete[0]['id']

        url = f'{SOFTHEON_WALLET_HOST}{SOFTHEON_WALLET_PREFIX}/v4/wallet/{wallet_id}/bankAccount/{bank_account_id}'
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
    create_bank_account = CreateBankAccount.Field()
    remove_bank_account = DeleteBankAccount.Field()

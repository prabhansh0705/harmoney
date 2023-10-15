import logging
import os

from harmoney.aiohttp_client import AioHttpClient
from harmoney.exceptions import MemberNotFoundException, PaymentNotFoundException, PaymentDisabledException
from dotenv import load_dotenv
from payment.views import GetIds
from payment.queries import rtr_get_source_query, embark_ref_id_query
from payment.constants import HttpStatusCodes, Constants
from payment.utils import get_softheon_identity

load_dotenv()
RTR_API_KEY = os.environ.get('BILLING_PAYMENTS_RTR_API_KEY')
RTR_BASE = os.environ.get('BILLING_PAYMENTS_RTR_HOST')
RTR_PREFIX = os.environ.get('BILLING_PAYMENTS_RTR_PREFIX')
SOFTHEON_REMOTE_SCOPE = Constants.SOFTHEON_REMOTE_SCOPE.value
SOFTHEON_PAYMENT_SCOPE = Constants.SOFTHEON_PAYMENT_SCOPE.value

logger = logging.getLogger(__name__)


class RtrPayments():
    def __init__(self, override_value=False, use_config_first=False):
        self.rtr_url = f'{RTR_BASE}{RTR_PREFIX}'
        self.override_value = override_value
        self.use_config_first = use_config_first
        self.http_client = AioHttpClient()

    async def get_payment_system(self, member):
        if (member.get("PaymentSystem") is None):
            issuer_subscriber_id = GetIds.get_issuer_subscriber_id(member)
            is_embark_member = await self.check_is_embark_member_flag(issuer_subscriber_id)
            member['PaymentSystem'] = "embark" if is_embark_member else "softheon"
        return member.get('PaymentSystem')

    async def check_is_embark_member_flag(self, issuer_subscriber_id, enrollment_source=''):
        try:
            if self.use_config_first:
                # return self._useEnvConfig(enrollmentSource, overrideValue)
                logger.error(
                    'Logic for the env config has not yet been implemented')
                return
            try:
                return await self.is_embark_member(issuer_subscriber_id)
            except Exception as exc:
                # Must return false here to catch non-embark members
                logger.error(exc)
                logger.error(
                    "IsEmbarkMember check failed! Trying env config file")
                return False
                # return self._useEnvConfig(enrollmentSource, overrideValue)

        except Exception:
            logger.error(
                'An unexpected error occurred while searching for embark member data!')
            return None

    async def is_embark_member(self, sub_id):
        try:
            rtr_response = await self.get_source(sub_id)
            return (
                rtr_response.get('source') == 'Embark' and
                rtr_response.get('memberMigratedAwayFromSource') is False
            )
        except Exception:
            logger.error(f'Member with id: {sub_id} could not be found')
            raise MemberNotFoundException(
                f'Member with id: {sub_id} could not be found')

    async def get_source(self, account_id):
        query = rtr_get_source_query(account_id)
        results = await self.execute_rtr_query(query)
        accounts = results.get('data', {}).get('accounts', [{}])[0]
        source = accounts.get('source', False)
        member_migrated_away_from_source = accounts.get(
            'memberMigratedAwayFromSource',
            False
        )
        return {
            "source": source,
            "memberMigratedAwayFromSource": member_migrated_away_from_source
        }

    async def execute_rtr_query(self, query):
        request_options = {
            'method': "post",
            'data': query,
            'headers': {
                'Authorization': f"Basic {RTR_API_KEY}",
                'Content-Type': 'application/json'
            }
        }
        request_config = {
            'assumeResponseIsJson': False,
            'throwOnParseError': False,
            'timeoutSeconds': 2,
            'retries': 0
        }
        data = await self.http_client.run_instance(
            self.rtr_url,
            request_options,
            request_config
        )
        if not (
                data and
                data.get('ok') and
                data.get('isJson') and
                data.get('data') and
                not (data.get('errors') and len(data.get('errors')) > 0)
        ):
            errors = data.get('errors', [])
            code = None
            if isinstance(errors, list) and len(errors) > 0:
                error = errors[0]
                extensions = error.get('extensions', {})
                code = extensions.get('code')
            public_message = (
                'Payment account not found' if
                code == str(HttpStatusCodes.FileNotFoundErr.value) else
                'Error pulling data from RTR'
            )
            logger.error(public_message)
            raise PaymentNotFoundException(public_message)

        return data.get('data')

    def _use_env_config(self, enrollment_source, override_value):
        # TODO: Add entries to the envfile as a fail-safe.
        pass

    async def get_member_ref_id(self, member):
        member_status = member.get('PaymentSystem')
        account_id = GetIds.get_issuer_subscriber_id(member)
        if member_status == 'embark':
            query = embark_ref_id_query(account_id)
            ref_id = await self.execute_rtr_query(query)
            return ref_id['data']['accounts'][0]['paymentProfileId']
        elif member_status == 'softheon':
            ref_token = await get_softheon_identity(member, SOFTHEON_REMOTE_SCOPE)
            url = 'https://apitest.centene.com/Softheon.Payment.API.Centene/api/Subscriber?issuerSubscriberID='+account_id
            options = {
                'method': 'get',
                'headers': {
                    'Authorization': f'Bearer {ref_token}'
                }
            }
            data = await self.http_client.run_instance(url, options)
            return data.get('data', {}).get('FolderID')
        else:
            return

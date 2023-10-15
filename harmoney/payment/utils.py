"""
Module: utils.py

    utils.py is a helper file in the payment module of the Harmoney project.
    It encompasses various utility-based helper functions that as of now,
    currently have no respective file structure to live in. It includes various
    functions such as create_resource_url, get_enrollments, etc. 

"""

import logging
import time
import os
from payment.models import PaymentMethodRequest, Ref
from dotenv import load_dotenv
from harmoney.aiohttp_client import AioHttpClient
from payment.constants import Constants, FormattingStrings, HttpStatusCodes
from harmoney.exceptions import PaymentNotFoundException, InvoiceNotFoundException


load_dotenv()
logger = logging.getLogger(__name__)
client = AioHttpClient()
umv_api_key = os.environ.get('CNC_UMV_V3_API_KEY')


def create_resource_url(
        host: str,
        base_path: str,
        version: str,
        endpoint: str
) -> str:
    """Creates a url with the given host, base_path, version, and endpoint for
    relevant Centene members

    :param host: The host of the site to request data from
    :type host: str
    :param base_path: The base path of the site to request data from
    :type base_path: str
    :param version: The version of the base path to request data from
    :type version: str
    :param endpoint: The specific type of data to be requested
    :type endpoint: str
    :return: A url conjoining all elements
    :rtype: str
    """
    version_number = ''
    if version:
        version_number = version if version.startswith('v') else f'v{version}'
    else:
        return "/".join([host, base_path, endpoint])
    return "/".join([host, base_path, version_number, endpoint])


async def get_enrollments(cnc_member_id: str):
    """Retrieves enrollment information about cnc_member_id

    :param cnc_member_id: The CncUmvV3 Member ID 
    :type cnc_member_id: str
    :return: Returns an dictionary containing enrollment information
    :rtype: dict
    """
    url = create_resource_url(
        os.environ.get('CNC_UMV_V3_HOST'), os.environ.get(
            'CNC_UMV_V3_BASE_PATH'),
        os.environ.get('CNC_UMV_V3_VERSION'), f"{cnc_member_id}/enrollmentspans"
    )
    data = await client.get(url, umv_api_key)
    return data.get('enrollmentspans')


async def get_identifiers(cnc_member_id):
    """Retrieves identifiers information about cnc_member_id

    :param cnc_member_id: The CncUmvV3 Member ID
    :type cnc_member_id: str
    :return: Returns an dictionary containing identifier information
    :rtype: dict
    """
    url = create_resource_url(
        os.environ.get('CNC_UMV_V3_HOST'),
        os.environ.get('CNC_UMV_V3_BASE_PATH'),
        os.environ.get('CNC_UMV_V3_VERSION'),
        f"{cnc_member_id}/identifiers"
    )
    return await client.get(url, umv_api_key)


async def get_attributes(cnc_member_id):
    """Retrieves attribute information about cnc_member_id

    :param cnc_member_id: The CncUmvV3 Member ID
    :type cnc_member_id: str
    :return: Returns an dictionary containing attribute information
    :rtype: dict
    """
    url = create_resource_url(
        os.environ.get('CNC_UMV_V3_HOST'),
        os.environ.get('CNC_UMV_V3_BASE_PATH'),
        os.environ.get('CNC_UMV_V3_VERSION'),
        endpoint=f"{cnc_member_id}/attributes"
    )
    return await client.get(url, umv_api_key)


def decode_hios_id(hios_id: str):
    if hios_id is None:
        return {'stateCode': None, 'planDimCK': None}
    state_code = hios_id[5:7]
    return {
        'stateCode': state_code,
        'planDimCK': Constants.STATE_ID_MAPPING.value.get(state_code)
    }


# dict [member_id: [(remote_scope, expires), (payment_scope, expires)]]
ACCESS_TOKEN_CACHE = {}


# Must be called before a restapi call is made to the Softheon wallet
async def get_softheon_identity(member, type):
    if member['PaymentSystem'] == 'embark':
        client_id = os.environ.get('EMBARK_CLIENT_ID')
        client_secret = os.environ.get('EMBARK_CLIENT_SECRET')
    else:
        state_code = decode_hios_id(member['planHiosId'])
        client_id = os.environ.get('HEALTHNET_CLIENT_ID') if state_code == 'CA' else \
            os.environ.get('AMBETTER_CLIENT_ID')
        client_secret = os.environ.get('HEALTHNET_CLIENT_SECRET') if state_code == 'CA' else os.environ.get(
            'AMBETTER_CLIENT_SECRET')

    tokens = ACCESS_TOKEN_CACHE.get(client_id)
    if tokens:
        num = 1 if type == Constants.SOFTHEON_PAYMENT_SCOPE.value else 0
        if tokens[num] and len(tokens[num]) == 2 and tokens[num][1] > time.time():
            return ACCESS_TOKEN_CACHE[client_id][num][0]

    host = os.environ.get('SOFTHEON_IDENTITY_HOST')
    prefix = os.environ.get('SOFTHEON_IDENTITY_PREFIX')
    url = f'{host}{prefix}/token'

    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    payload = {
        'scope': f"api.softheon.{type}",
        'grant_type': 'client_credentials',
        'client_id': client_id,
        'client_secret': client_secret
    }

    request_options = {
        'method': "post",
        'data': payload,
        'headers': headers
    }
    start = time.time()
    try:
        data = await client.run_instance(url=url, request_options=request_options)
    except Exception as err:
        logger.error(err)
    else:
        access_token = data.get('data', {}).get('access_token')
        if client_id not in ACCESS_TOKEN_CACHE:
            ACCESS_TOKEN_CACHE[client_id] = [(), ()]
        if type == Constants.SOFTHEON_REMOTE_SCOPE.value:
            ACCESS_TOKEN_CACHE[client_id][0] = (access_token, start+3600)
        elif type == Constants.SOFTHEON_PAYMENT_SCOPE.value:
            ACCESS_TOKEN_CACHE[client_id][1] = (access_token, start+3600)
        else:
            logger.error("Invalid Type Provided")
        return access_token


async def get_medb_response(url, options):
    medb_error = "fetching Data from MEDB failed: timed out making MEDB request for Invoices"
    try:
        response = await client.run_instance(url, options)
    except InvoiceNotFoundException as exc:
        logger.error(FormattingStrings.ErrorLogFormat.value, medb_error, exc)
        raise InvoiceNotFoundException(medb_error)

    if response is None:
        return None
    is_timed_out, ok, status = response.get(
        'isTimedOut'), response.get('ok'), response.get('status')
    if status == HttpStatusCodes.FileNotFoundErr.value:
        logger.info("No records found for Invoices from MEDB")
        return []

    if is_timed_out or not ok or not response.get('isJson'):
        logger.error(medb_error)
        raise PaymentNotFoundException(medb_error)

    logger.debug("Invoices from MEDB: %s", response)
    return response


#### NESTED RETURN OBJECT HELPERS ####
def add_payment_method_obj(response_object):
    payment_method = PaymentMethodRequest()
    setattr(payment_method,'token',response_object.get('paymentToken'))
    setattr(payment_method,'type',response_object.get('paymentType'))
    setattr(payment_method,'source', 'softheon')
    setattr(payment_method,'amount',response_object.get('amount'))
    setattr(payment_method,'runDayOfMonth',response_object.get('runDay'))
    setattr(payment_method,'scheduleType','Monthly')
    return payment_method

def add_ref_object(response_object):
    ref = Ref()
    setattr(ref, 'refId', response_object.get('id'))
    setattr(ref, 'source', 'softheon')
    return ref

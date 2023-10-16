"""
Module: Cnc_Umv_V3_Client

Provides a wrapper client class for making calls to and retrieving member 
information from the CncUmvV3 API.

:raises Exception: Raises an exception if there is no provided API key
:raises Exception: Raises an exception if there isn't enough information about 
the API endpoint to retrieve the member data

"""

import logging
import os
from dotenv import load_dotenv
from harmoney.config import BaseConfig
from harmoney.exceptions import MissingAuthTokenException, FailedClientCreationException
from harmoney.aiohttp_client import AioHttpClient
from payment.utils import create_resource_url

logger = logging.getLogger(__name__)
load_dotenv()


class CncUmvV3Client:
    """
    A wrapper class for simplifying making requests to the CncUmvV3 API as part
    of the network of Centene systems. Searches for members and handles error
    handling, authorization, and is built on top of the AioHttpClient, utilizing
    its core functionality to make the calls

    To search for members, the asynchronous method, search_member_client is 
    used to query the CncUmvV3 API for the respective member information, which
    is then passed to other services such as the GraphQL resolvers
    """

    def __init__(self) -> None:
        self.api_key = "eqeqweqw"
        self.host = "eqweqweqw"
        self.base_path = "eqeqweqw"
        self.version = "eqeqweqwe"

        if not self.api_key:
            raise MissingAuthTokenException(
                "Cannot create CNC UMV Client without an API key.  "
                "Check your config: CNC_UMV_V3_API_KEY"
            )

        if not self.host or not self.base_path or not self.version:
            raise FailedClientCreationException(
                "Cannot create CNC Auth Client without a host, base_path and version."
                "  Check your env: CNC_UMV_V3_HOST, CNC_UMV_V3_BASE_PATH")

        self.client = AioHttpClient()

    async def search_member_client(self, request):
        """A asynchronous function dedicated to making member retrievals from 
        the CncUmvV3 API, built on the architecture of the AioHttpClient class

        :param request: A request containing necessary parameters needed for 
        making successful member information retrieval
        :type request: dict
        :return: Returns all raw  member information linked to the member id
        :rtype: dict
        """
        member_id = request.get("id", None)
        request = {**({"identifier": member_id} if member_id else {}),
                   'businessLine': 'Market Place'}
        url = create_resource_url(self.host, self.base_path, self.version, "")
        request_options = {
            'method': "get",
            'data': {},
            'headers': {
                'Authorization': f"Basic {self.api_key}"
            },
            'params': {
                **request
            }
        }
        data = (await self.client.run_instance(url, request_options))
        return data

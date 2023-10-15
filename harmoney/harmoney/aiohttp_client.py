"""
Module: aiohttp_client

This module provides a class for performing custom and built-in HTTP requests.

The AioHttpClient class in this module offers a range of methods for data
processing, making custom HTTP requests, and implementing context management
for efficient resource handling. It simplifies the process of working with HTTP
requests, allowing users to easily send requests, handle responses, and manage
connections.

Example usage:
    ```
    # Create an instance of the AioHttpClient class
    client = AioHttpClient()

    # Define custom options and configurations to pass to the request
    options = {
        'headers': { 'Content-Type': 'application/json' },
        method: 'get'
    }
    config = { 'timeoutSeconds': 100 }
    url = ""

    # Get the coroutine
    coroutine = client.run_instance(url, options, config)

    #Execute the request and retrieve the data
    data = asyncio.run(coroutine())
    ```
"""

import json
import re
import asyncio
import aiohttp
import logging
from aiohttp import ClientSession, ClientTimeout
from typing import Optional

from payment.constants import HttpStatusCodes

JSON_CONTENT_TYPE = re.compile(r'^application\/json', re.IGNORECASE)
logger = logging.getLogger(__name__)


class AioHttpClient:
    """
    A wrapper class for the aiohttp library that streamlines the process of
    making asynchronous HTTP requests and provides features such as error
    handling, timeouts, and retries.

    To make requests, users should call the
    'run_instance(url, request_options, request_config)'
    function. This function will asynchronously make the HTTP request with all
    necessary configurations and return the coroutine response.

    request_options:
    * method (str): The HTTP method to be used for the request (e.g.., GET).
    * headers (dict): A dictionary of headers to be included in the request.
    * data (dict): A dictionary of data to be sent in the request body.
    * params (dict): A dictionary of query parameters to be included in the URL.

    request_config (Optional):
    * assumeResponseIsJson (bool): A boolean flag used to help with response
    parsing. Defaults to False.
    * throwOnParseError (bool): A boolean flag used to raise an exception when
    an error occurs. Defaults to False.
    * timeoutSeconds (int): An integer representing the total amount of seconds
    permitted for the life of a HTTP request. Defaults to 10
    * _retryAttempts (int): An integer representing the total amount of HTTP
    request retries available. Defaults to 0.
    """

    DEFAULT_TIMEOUT_SECONDS = 1
    DEFAULT_RETRIES = 3
    DEFAULT_RETRY_ATTEMPTS = 0
    DEFAULT_BACKOFF_SECONDS = 0.05
    DEFAULT_ASSUME_RESPONSE_IS_JSON = False
    DEFAULT_THROW_ON_PARSE_ERROR = False

    def __init__(self):
        self.session: Optional[ClientSession] = None

    async def __aenter__(self) -> "AioHttpClient":
        self.session = ClientSession()
        return self

    async def __aexit__(self, *err) -> None:
        await self.session.close()

    @staticmethod
    def build_headers_object(headers: dict):
        """
        Creates a dictionary containing header fields as properties
        :param headers: headers
        :type headers: dict
        :return: dictionary containing header fields
        :rtype: dict
        """
        return headers.items()

    @staticmethod
    async def get_common_response(response: aiohttp.ClientResponse):
        """
        get_common_response() takes in a ClientResponse object from aiohttp.
         It creates a common dictionary response
        that allows more transparency between shared services

        :param response: The returned response from an aiohttp call
        :type response: object
        :return: returns a common response dictionary for other services
        :rtype: dict
        """
        try:
            data = await response.text()
            common_response = {
                'ok': response.ok,
                'status': response.status,
                'statusText': response.reason,
                'headers': AioHttpClient.build_headers_object(response.headers),
                'url': str(response.url)
            }
            try:
                json_data = json.loads(data)
                common_response['data'] = json_data
            except json.JSONDecodeError:
                common_response['data'] = data
            return common_response
        except Exception as exc:
            logger.error(exc)
            return {}

    @staticmethod
    async def parse_response(response: aiohttp.ClientResponse, config=None):
        """
        Automatically parse an aiohttp response as JSON, with error handling
        * :param res: The aiohttp response
        * :type res: Response
        * :param dict config: The configuration object
        * :type config: dict
        * :return: Awaits a coroutine with an object containing a data field and
            an isJson field.  If the parse succeeds, data will be the parsed
            object from the json and isJson will be true.  If the parse fails,
            data will be the response text and isJson will be false.  If the
            config option throwOnParseError is set and the parse fails, an error
            will be thrown.
        * :rtype: coroutine<dict>
        """
        data = await response.text()
        assume_response_is_json = config.get(
            "assumeResponseIsJson",
            AioHttpClient.DEFAULT_ASSUME_RESPONSE_IS_JSON
        )
        if assume_response_is_json or JSON_CONTENT_TYPE.match(
                response.headers['Content-Type']):
            try:
                return {'data': json.loads(data), 'isJson': True}
            except json.JSONDecodeError as exc:
                if config.get("throwOnParseError", False):
                    raise exc
        return {'data': data, 'isJson': False}

    async def _http_request(self, url, options, config):
        """
        http_request is a helper function and a wrapper around aiohttp that
        implements timeouts, retries, and automatic json parsing

        * :param str url: The url to request
        * :type url: str
        * :param options: The options object to pass to request
        * :type options: dict
        * :param dict config: The request configuration object.
        * :type config: dict
        * :return: Returns a coroutine with a response object
        * :rtype: coroutine<dict or None>
        """
        response = {}
        retries = config.get('retries', AioHttpClient.DEFAULT_RETRIES)
        retry_attempts = config.get('_retryAttempts', 0)
        backoff = config.get('backoff', AioHttpClient.DEFAULT_BACKOFF_SECONDS)
        while retry_attempts < retries + 1:
            try:
                response = await self._perform_http_request(url, options, config)
                return response
            except (aiohttp.ServerTimeoutError, asyncio.TimeoutError):
                logger.error(f"Timeout Reached: {url}, retrying again.")
                await asyncio.sleep(backoff)
                retry_attempts += 1
                continue
        return response

    async def _perform_http_request(self, url, options, config):
        """
        perform_http_request is a helper function called within the scope
        of http_request that performs the actual http request and returns
        data if valid

        :param url: url to fetch data from
        :type url: str
        :param options: The options object to pass to request
        :type options: dict
        :param config: the request configuration object
        :type config: dict
        :raises aiohttp.ClientResponseError: propagates an error to be caught by
        http_request when status >= 400
        :return: returns dictionary with common_response attached
        :rtype: dict
        """
        resp = {}
        method = options.get('method', '').upper()
        headers = options.get('headers', None)
        params = options.get('params', {})
        data = options.get('data', {})
        timeout = ClientTimeout(total=config.get(
            'timeoutSeconds', AioHttpClient.DEFAULT_TIMEOUT_SECONDS))
        async with self.session.request(
                method=method,
                url=url,
                params=params,
                headers=headers,
                data=data,
                ssl=False,
                timeout=timeout
        ) as response:
            common_response = await AioHttpClient.get_common_response(response)
            obj = await self.parse_response(response, config)
            if obj.get('isJson'):
                resp = {'isJson': True, 'data': obj.get('data', {}), **common_response}
        return resp

    async def run_instance(self, url, request_options, request_config=None):
        """
        run_instance() provides a simpler way to call http requests with
        the aiohttp functionality. It is the main function in this class to
        call functions with

        * :param str url: The url to request
        * :type url: str
        * :param request_options: The options object to pass to request
        * :type request_options: dict
        * :param dict request_config: The request configuration object.
        * :type request_config: dict
        * :return: Returns a coroutine with a response object
        * :rtype: coroutine<dict>
        """
        request_config = {} if request_config is None else request_config
        async with AioHttpClient() as instance:
            data = await instance._http_request(url, request_options, request_config)
            if data['status'] >= 400:
                logger.error(data)
                raise Exception(f'Error thrown with status: {data["status"]}. {data["data"]}')
            return data

    async def get(self, url, api_key=None):
        """
        get() provides a simple way to complete standalone get requests

        * :param url: The url to get data from
        * :type url: str
        * :return: Returns data retrieved from a get request to url
        * :rtype: coroutine<dict>
        """
        async with AioHttpClient() as instance:
            data = await instance._http_request(
                url,
                {
                    'method': 'get',
                    'headers': {
                        'Authorization': f"Basic {api_key}"
                    }
                },
                {
                    'retries': 0
                }
            )
        return data.get('data')

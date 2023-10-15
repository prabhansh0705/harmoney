"""
    Group Schema resolvers
"""
import asyncio
import json

from dotenv import load_dotenv
from group.models import Group

from harmoney.aiohttp_client import AioHttpClient

EVENT_LOOP = None

try:
    EVENT_LOOP = asyncio.get_running_loop()
except RuntimeError:
    EVENT_LOOP = asyncio.new_event_loop()
    asyncio.set_event_loop(EVENT_LOOP)

load_dotenv()

HTTP = AioHttpClient()


class GroupResolvers:
    """
        Functions to retrieve group information and format response
    """

    def resolve_group(group_id):
        """
            Runs event loop on format_group to keep schema synchronous
        """
        group = EVENT_LOOP.run_until_complete(
            GroupResolvers.format_group(group_id)
        )

        return Group(**group)

    @staticmethod
    async def format_group(group_id):
        """
            retrieves group info and formats for schema
        """
        # TODO update url once group RTR is fixed
        url = (
            'https://group-api.ckp-test.aws.centene.com'
            f'/groups?groupId={group_id}'
        )
        request_options = {
            'method': "get",
        }
        config = {
            'timeoutSeconds': 1,
            'retries': 5
        }
        response = await HTTP.run_instance(url, request_options, config)
        if response:
            response_data = response.get('data')
            if response_data:
                group = response_data.get('result')[0]

                group_obj = {
                    "groupId": group.get('groupId'),
                    "groupName": group.get('groupName'),
                    "eocInformation": json.dumps(group.get('eocInformation'))
                }
                return group_obj

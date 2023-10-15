import asyncio
import logging
import re
from datetime import datetime
from graphql.execution import ExecutionResult
from graphene_django.views import GraphQLView
from graphql.error import GraphQLError

import pydash
from harmoney.exceptions import MemberNotFoundException
from payment.date_selector import DateSelector
from datetime import datetime
from payment.date_selector import DateSelector
from payment.objects import TimeSpan
from payment.utils import get_attributes, get_identifiers, get_enrollments
from payment.cnc_umv_v3_client import CncUmvV3Client
from .constants import FormattingStrings


CNC_UMV_V3 = CncUmvV3Client()
logger = logging.getLogger(__name__)


async def search_member(_request):
    """Takes in a Client Response and successfully 

    :param _request: An HttpRequest?
    :type _request: _type_
    :raises MemberNotFoundException: _description_
    :return: a umv member object
    :rtype: dict
    """
    res = await CNC_UMV_V3.search_member_client(_request)
    if not res:
        logger.error({res, _request}, 'Error searching for member')
        raise MemberNotFoundException('Error searching for member')
    members = res.get('data', {}).get('members')
    if len(members) <= 1:
        return members

    """ 
    When searchMember is called without id but with lastname + last-four of ssn
    There could be multiple records returned with multiple UMV ids - group they by umvid
    """
    members_by_ids = _get_member_ids(members)

    latest_members = []
    for grouped_members in members_by_ids.values():
        if len(grouped_members) == 1:
            latest_members.append(grouped_members[0])
            continue

        date_selector = DateSelector('currentOrFuture', datetime.now())
        results = []
        tasks = []
        for member in grouped_members:
            tasks.append(asyncio.create_task(
                _get_current_pr_future_enrollment_span(
                    member.get('id')
                )
            ))
        gathered = await asyncio.gather(*tasks)
        for enrollment in gathered:
            if not enrollment:
                continue
            result = {
                'member': member,
                **enrollment
            }
            results.append(result)

        filtered_results = list(filter(date_selector.date_filter, results))

        sorted_results = sorted(
            filtered_results,
            key=date_selector.date_sorter,
            reverse=date_selector.reversed_or_not())
        current_or_latest_member = next(
            (result.get('member') for result in sorted_results), None)

        if current_or_latest_member:
            latest_members.append(current_or_latest_member)
        else:
            sorted_results = sorted(
                results,
                key=lambda x: x.get('effectiveDate'),
                reverse=True)
            member = sorted_results[0].get(
                'member') if sorted_results else None

            if member:
                latest_members.append(member)

    return latest_members


async def enrich_member(member):
    """Adds on to an existing umv member object, getting attribute, 
    identifier, enrollment source, and planHiosId data along with references 
    like IDs from API endpoints

    :param member: the umv member object
    :type member: dict
    :return: returns member object with additional 'refs', 'planhiosid', and 
    enrollment source key values
    :rtype: _type_
    """
    identifier_task = asyncio.create_task(get_identifiers(member.get('id')))
    attributes_task = asyncio.create_task(get_attributes(member.get('id')))
    tasks = [identifier_task, attributes_task]
    gathered = await asyncio.gather(*tasks)
    identifiers = gathered[0].get('identifiers')
    attributes = gathered[1].get('attributes')

    async def get_refs(identifiers):
        refs = [
            {
                'refId': i.get('identifier'),
                'source': i.get('identificationType')
            }
            for i in identifiers
            if i.get('isActive') and not i.get('isVoid')
        ]
        refs = [
            {
                'refId': member.get('id'),
                'source': 'cnc'
            },
            {
                'refId': member.get('memberCode'),
                'source': 'umv'
            },
            {
                'refId': member.get('amisysId'),
                'source': 'amisys'
            },
            *refs
        ]
        return refs

    async def get_enrollment_source_attrs(attributes):
        enrollment_source_attrs = sorted(
            [
                a
                for a in attributes
                if a.get('attribute') and (
                    a.get('attribute').endswith('MP_Enrollment Source')
                ) and not a.get('isVoid') and a.get('startDate')
            ],
            key=lambda a: datetime.strptime(
                a.get('startDate'),
                FormattingStrings.DateTimeFormat.value,
            ),
            reverse=True
        )
        return enrollment_source_attrs

    async def get_plan_hios_id_attrs(attributes):
        plan_hios_id_attrs = sorted(
            [
                a
                for a in attributes
                if a.get('attribute') and a.get(
                    'attribute').endswith('HIOS') and not a.get(
                    'isVoid') and a.get('startDate')
            ],
            key=lambda a: datetime.strptime(
                a.get('startDate'),
                FormattingStrings.DateTimeFormat.value),
            reverse=True
        )
        return plan_hios_id_attrs

    refs = asyncio.create_task(get_refs(identifiers))
    enrollment_source_attrs = asyncio.create_task(
        get_enrollment_source_attrs(
            attributes
        )
    )
    plan_hios_id_attrs = asyncio.create_task(
        get_plan_hios_id_attrs(
            attributes
        )
    )
    tasks = [refs, enrollment_source_attrs, plan_hios_id_attrs]
    gathered = await asyncio.gather(*tasks)

    refs, enrollment_source_attrs, plan_hios_id_attrs = \
        gathered[0], gathered[1], gathered[2]

    enrollment_source = None
    plan_hios_id = None

    if enrollment_source_attrs:
        enrollment_source = (
            enrollment_source_attrs[0] or {}
        ).get(
            'definedValue'
        )

    if plan_hios_id_attrs:
        plan_hios_id = (
            plan_hios_id_attrs[0] or {}
        ).get(
            'definedValue'
        )

    return {
        **member,
        'enrollmentSource': enrollment_source,
        'planHiosId': plan_hios_id,
        'refs': refs
    }


async def _get_current_pr_future_enrollment_span(member_id):
    enrollments = filter(
        lambda item: not item.get('void') and item.get('endDate'),
        await get_enrollments(member_id))

    if not enrollments:
        return None

    enrollments_with_dates = map(lambda enrollment: {
        **enrollment,
        'TimeSpan': TimeSpan(
            datetime.strptime(
                enrollment.get('effectiveDate'),
                FormattingStrings.DateTimeFormat.value
            ),
            datetime.strptime(
                enrollment.get('endDate'),
                FormattingStrings.DateTimeFormat.value
            ),
        )
    }, enrollments)

    date_selector = DateSelector('currentOrFuture', datetime.now())

    filtered_list = list(filter(
        date_selector.date_filter,
        enrollments_with_dates
    ))

    sorted_data = sorted(
        filtered_list,
        key=date_selector.date_sorter,
        reverse=date_selector.reversed_or_not()
    )

    result = sorted_data[0] if sorted_data else None
    if not result:
        return pydash.chain(enrollments_with_dates) \
            .order_by(['effectiveDate'], ['desc']) \
            .head() \
            .value()
    return result


def _get_member_ids(members):
    members_by_ids = {}
    for member in members:
        amisys_id = member.get('amisysId')
        if amisys_id not in members_by_ids:
            members_by_ids[amisys_id] = []
        members_by_ids[amisys_id].append(member)
    return members_by_ids


class GetIds:
    """A class for processing data from Centene's systems
    and APIs to retrieve various IDs


    The purpose of this class is to provide an easier, more efficient way of
    combing through the data from Centene's various APIs' to find the relevant
    ids needed for other dependencies in Harmoney. It encapsulates the logic
    for analyzing and extracting the various ID values from the passed in data.

    Methods:
        @staticmethod get_ref_id(refs, source):

            Finds and returns the first making source value in refs

        @staticmethod get_issuer_subscriber_id(member):

            Finds and returns relevant issuer_subscriber_id from member

    """

    @staticmethod
    def get_ref_id(refs: str, source: str) -> str:
        """Takes in a source string and a ref string and traverses through ref
        to find the corresponding ID value belonging to source

        :param refs: The referenced values
        :type refs: str
        :param source: The source of which Centene system the member uses
        :type source: str
        :return: returns the corresponding ref(id) to source
        :rtype: str
        """
        ref = {}
        for r in refs:
            if r and r['source'] == source:
                ref = r
                break
        return ref and ref.get('refId')

    @staticmethod
    def get_issuer_subscriber_id(member: dict):
        """Compares various Centene system ID values and selects the apt one
        based on conditional logic and returns it

        :param member: A dictionary containing member information retrieved from
        the relevant Centene-related API
        :type member: dict
        :raises KeyValue: issuerSubscriberID could not be discerned
        :return: A str containing the relevant ID
        :rtype: str
        """
        amisys_id = GetIds.get_ref_id(member['refs'], 'amisys')
        abs_id = GetIds.get_ref_id(member['refs'], 'abs')
        # Note: the PO Subscriber ID does not have a dash,
        # but it's the same as the PO Member ID without the last two characters.
        # We don't need to trim anything from this id because the Subscriber ID
        # is "pre-trimmed".
        po_subscriber_id_ref = GetIds.get_ref_id(
            member['refs'], 'PO Subscriber ID')
        issuer_subscriber_id_ref = GetIds.get_ref_id(
            member['refs'], 'Issuer Subscriber ID')

        # remove the suffix (-01) from the amisysId
        abs_id_regex, amisys_id_regex = re.compile(
            r'^(R\d{8})'), re.compile(
                r'^(R\d{8})')

        _, issuer_subscriber_id = (
            (issuer_subscriber_id_ref and [
                None, issuer_subscriber_id_ref
            ]) or (
                po_subscriber_id_ref and [
                    None, po_subscriber_id_ref
                ]
            ) or (
                abs_id and (
                    lambda m: m.group(1) if m else None,
                    abs_id_regex.match(abs_id)
                )
            ) or (
                amisys_id and (
                    lambda m: m.group(1) if m else None,
                    amisys_id_regex.match(amisys_id)
                )
            ) or [None, None]
        )

        if not issuer_subscriber_id:
            raise MemberNotFoundException(
                f"Cannot generate issuerSubscriberID for member {member['id']}"
            )
        return issuer_subscriber_id

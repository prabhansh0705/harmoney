import asyncio
import datetime
import pydash
import logging
import os

from dotenv import load_dotenv
from payment.constants import Constants
from payment.rtrPayments import RtrPayments
from payment.models import Balance, CreditCard, BankAccount, Premium
from payment.models import RecurringPayment, Invoice, ApplicationConfig
from payment.models import PaymentHistory
from payment.views import search_member, enrich_member, GetIds
from payment.utils import decode_hios_id, create_resource_url, get_softheon_identity, add_ref_object, add_payment_method_obj
from harmoney.aiohttp_client import AioHttpClient
from harmoney.exceptions import MemberNotFoundException
from payment.queries import rtr_payment_history_query, rtr_get_balance_query, rtr_invoice_query
from payment.utils import get_medb_response

EVENT_LOOP = None

try:
    EVENT_LOOP = asyncio.get_running_loop()
except RuntimeError:
    EVENT_LOOP = asyncio.new_event_loop()
    asyncio.set_event_loop(EVENT_LOOP)

load_dotenv()

RTR = RtrPayments()
HTTP = AioHttpClient()
MEDB_HOST = os.environ.get("MEDB_HOST")
MEDB_BASE_PATH = os.environ.get("MEDB_BASE_PATH")
MEDBP_BASE_PATH = os.environ.get("MEDBP_BASE_PATH")
MEDB_VERSION = os.environ.get("MEDB_VERSION")
MEDB_API_KEY = os.environ.get("MEDB_API_KEY")
SOFTHEON_WALLET_HOST = os.environ.get("SOFTHEON_WALLET_HOST")
CNC_SOFTHEON_PAYMENT_HOST = os.environ.get("CNC_SOFTHEON_PAYMENT_HOST")
CNC_SOFTHEON_PAYMENT_PREFIX = os.environ.get("CNC_SOFTHEON_PAYMENT_PREFIX")
CNC_UMV_V3_HOST = os.environ.get("CNC_UMV_V3_HOST")
CNC_UMV_V3_BASE_PATH = os.environ.get("CNC_UMV_V3_BASE_PATH")
CNC_UMV_V3_VERSION = os.environ.get("CNC_UMV_V3_VERSION")
CNC_UMV_V3_API_KEY = os.environ.get("CNC_UMV_V3_API_KEY")

SOFTHEON_REMOTE_SCOPE = Constants.SOFTHEON_REMOTE_SCOPE.value
SOFTHEON_PAYMENT_SCOPE = Constants.SOFTHEON_PAYMENT_SCOPE.value
APPLICATION_JSON_CONTENT_TYPE = "application/json"
DATE_FORMAT = "%Y-%m-%d"

RTR_MAX_LIMIT = 100

logger = logging.getLogger(__name__)

SOFTHEON_CREDIT_CARD_TOKENIZATION_LEGACY_URL = os.environ.get(
    "SOFTHEON_CREDIT_CARD_TOKENIZATION_LEGACY_URL"
)
SOFTHEON_CREDIT_CARD_TOKENIZATION_EMBARK_URL = os.environ.get(
    "SOFTHEON_CREDIT_CARD_TOKENIZATION_EMBARK_URL"
)
SOFTHEON_BANK_ACCOUNT_TOKENIZATION_EMBARK_URL = os.environ.get(
    "SOFTHEON_BANK_ACCOUNT_TOKENIZATION_EMBARK_URL"
)
SOFTHEON_BANK_ACCOUNT_TOKENIZATION_LEGACY_URL = os.environ.get(
    "SOFTHEON_BANK_ACCOUNT_TOKENIZATION_LEGACY_URL"
)
AMBETTER_CLIENT_ID = os.environ.get("AMBETTER_CLIENT_ID")
HEALTHNET_CLIENT_ID = os.environ.get("HEALTHNET_CLIENT_ID")
EMBARK_CLIENT_ID = os.environ.get("EMBARK_CLIENT_ID")


class CreditCardResolvers:

    def resolve_credit_cards(self, info):
        """
        Credit card resolver
        """
        credit_cards = EVENT_LOOP.run_until_complete(
            CreditCardResolvers.format_credit_cards(
                info.context.member
            )
        )
        return [CreditCard(**cc) for cc in credit_cards]

    @staticmethod
    async def format_credit_cards(member):
        """
        Function to fetch and assign credit card values to respective fields
        as per the API response
        response.
        :param member: member object
        :return: List of credit card dict
        """
        credit_cards = []
        payment_token = await get_softheon_identity(member, SOFTHEON_PAYMENT_SCOPE)
        ref_id = await RTR.get_member_ref_id(member)
        if ref_id:
            url = f'{SOFTHEON_WALLET_HOST}/payments/v4/wallet?referenceId={ref_id}'
            request_options = {
                'method': "get",
                'headers': {
                    'Authorization': f"Bearer {payment_token}",
                    'Content-Type': APPLICATION_JSON_CONTENT_TYPE
                }
            }
            config = {
                'timeoutSeconds': 1,
                'retries': 5
            }
            response = await HTTP.run_instance(url, request_options, config)
            if response:
                response_data = response.get("data")
                if response_data:
                    credit_card_data = response_data.get('creditCards')
                    for each_credit_response in credit_card_data:
                        ref = add_ref_object(each_credit_response)
                        credit_cards.append({
                            'ref': ref,
                            'cardHolderName': each_credit_response.get('cardHolderName'),
                            'maskedCardNumber': each_credit_response.get('cardNumber'),
                            'cardState': each_credit_response.get('cardState'),
                            'cardType': each_credit_response.get('cardType'),
                            'createdAt': each_credit_response.get('createdTime'),
                            'email': each_credit_response.get('email'),
                            'expirationMonth': each_credit_response.get('expirationMonth'),
                            'expirationYear': each_credit_response.get('expirationYear'),
                            'memberId': each_credit_response.get('id'),
                            'modifiedOn': each_credit_response.get('modifiedTime'),
                            'token': each_credit_response.get('token'),
                            'isDefault': each_credit_response.get('isDefault', False)
                        })
        return credit_cards


class ApplicationConfigResolvers:

    def resolve_application_config(self, info):
        application_config = EVENT_LOOP.run_until_complete(
            ApplicationConfigResolvers.logic_resolve_application_config(
                info.context.member)
        )
        return ApplicationConfig(**application_config)

    @staticmethod
    async def logic_resolve_application_config(member):
        payment_system = await RTR.get_payment_system(member)
        plan_hios_id = member.get('planHiosId')
        state_code = decode_hios_id(plan_hios_id)
        if payment_system == 'embark':
            return {
                'creditCardTokenizationURL': SOFTHEON_CREDIT_CARD_TOKENIZATION_EMBARK_URL,
                'bankAccountTokenizationURL': SOFTHEON_BANK_ACCOUNT_TOKENIZATION_EMBARK_URL,
                'paymentClientId': EMBARK_CLIENT_ID
            }
        return {
            'creditCardTokenizationURL': SOFTHEON_CREDIT_CARD_TOKENIZATION_LEGACY_URL,
            'bankAccountTokenizationURL': SOFTHEON_BANK_ACCOUNT_TOKENIZATION_LEGACY_URL,
            'paymentClientId':
                HEALTHNET_CLIENT_ID if state_code == 'CA' else AMBETTER_CLIENT_ID
        }


class BalanceResolvers:

    def resolve_balance(self, info):
        balance = EVENT_LOOP.run_until_complete(
            BalanceResolvers.format_resolve_balance(info.context.member)
        )
        return Balance(**balance)

    @staticmethod
    async def format_resolve_balance(member):
        payment_system = member.get('PaymentSystem')
        if payment_system == 'embark':
            response = await BalanceResolvers.logic_resolve_balance(
                member
            ) or {}
            response = response.get('accounts', [{}])
            account = response[0]
            total_amount_due = account.get('balance')
            status = account.get('status')
            invoices = account.get('invoices', [])
            current_invoice = pydash.order_by(
                invoices,
                'generatedDate',
                'desc'
            )

            current_invoice = current_invoice[0] if current_invoice else {}
            current_amount_due = current_invoice.get('grossAmount', 0)
            premium_amount_due = current_invoice.get('premiumAmountDue', 0)
            finance_status = current_invoice.get('status')

            return {
                'totalAmountDue': total_amount_due,
                'premiumAmountDue': premium_amount_due,
                'currentAmountDue': current_amount_due,
                'financeStatus': finance_status,
                'status': status
            }
        else:
            data = await BalanceResolvers.logic_resolve_balance(member)
            total_amount_due = data.get('TotalAmountDue')
            premium_amount_due = data.get('PremiumAmountDue')
            current_amount_due = data.get("CurrentAmountDue")
            status = data.get('Status')
            finance_status = data.get('FinanceStatus')

            return {
                'totalAmountDue': total_amount_due,
                'premiumAmountDue': premium_amount_due,
                'currentAmountDue': current_amount_due,
                'financeStatus': finance_status,
                'status': status
            }

    @staticmethod
    async def logic_resolve_balance(member):
        today = datetime.date.today()
        payment_system = member.get('PaymentSystem')
        issuer_subscriber_id = GetIds.get_issuer_subscriber_id(member)
        if payment_system == 'embark':
            start_of_year = datetime.date(today.year, 1, 1).strftime(
                DATE_FORMAT
            )
            account_id = issuer_subscriber_id
            query = rtr_get_balance_query(account_id, start_of_year)
            result = await RTR.execute_rtr_query(query)
            return result.get('data')
        else:
            token = await get_softheon_identity(member, SOFTHEON_REMOTE_SCOPE)
            options = {
                'params': {
                    'issuerSubscriberID': issuer_subscriber_id
                },
                'method': 'get',
                'headers': {
                    'Authorization': f'Bearer {token}'
                }
            }

            path = f"{CNC_SOFTHEON_PAYMENT_HOST}{CNC_SOFTHEON_PAYMENT_PREFIX}/Subscriber"
            data = await HTTP.run_instance(path, options)

            success, status = data.get('ok'), data.get('status')
            if not success or not status:
                logger.error("Unaccepted HTTP request to Softheon Subscriber")
            return data.get('data')


class PaymentResolvers:

    def resolve_payment_histories(self, info, start_date=None, end_date=None):
        today = datetime.date.today()
        today = today.replace(today.year - 3, 1, 1).strftime(DATE_FORMAT)
        start_date = today if not start_date else start_date
        end_date = datetime.date.today().strftime(
            DATE_FORMAT) if not end_date else end_date
        payment_histories = EVENT_LOOP.run_until_complete(
            PaymentResolvers.format_resolve_payment_histories(
                info.context.member,
                {
                    'startDate': start_date,
                    'endDate': end_date,
                }
            )
        )
        return [PaymentHistory(**aph)
                for aph in payment_histories]

    @staticmethod
    async def format_resolve_payment_histories(member, dates):
        """Formats the data returned from logic_resolve_payment_history to
        contain only necessary fields and make it readable to GraphQL

        :param member: Member retrieved from Umv
        :type member: dict
        :param dates: An object containing the start and end date
        :type dates: dict
        :return: Returns a list of dictionaries containing relevant
        PaymentHistory fields
        :rtype: list[dict]
        """
        business_unit, business_unit_code = member.get(
            'businessUnit'), member.get('businessUnitCode')
        payment_system = member.get('PaymentSystem')
        response = await PaymentResolvers.logic_resolve_payment_histories(member, dates)
        result = []
        if payment_system == 'embark':
            for transaction in response:
                member_id = transaction.get('accountId')
                transaction_id = transaction.get('transactionId')
                merchant_transaction_id = transaction.get(
                    'merchantTransactionId')

                result.append({
                    "buCode": business_unit_code,
                    "memberId": member_id,
                    "paymentId": transaction_id,
                    "submitter": member_id,
                    "transmissionDate": transaction.get('receivedDate'),
                    "tradingPartner": transaction.get('tradingPartner'),
                    "paymentMethod": transaction.get('paymentMethod', {}).get('description'),
                    "transactionId": transaction_id,
                    "paymentType": transaction.get('type'),
                    "product": transaction.get('product', ''),
                    "paymentDate": transaction.get('processedDate'),
                    "paymentClass": transaction.get('transactionClass'),
                    "paymentSource": transaction.get('source', {}).get('description'),
                    "sourceSystem": 'RTR',
                    "paymentAmount": transaction.get('paymentAmount'),
                    "receiptNumber": transaction_id,
                    "stateCode": 'MP',
                    "businessUnit": business_unit,
                    "caseId": None,
                    "externalVendorClientId": transaction.get('detailsMetadata', {}).get('tradingPartnerId', ''),
                    "dataSourcePointer": None,
                    "checkNumber": merchant_transaction_id,
                    "lockBoxId": '',
                    "lockBoxBatchId": None,
                    "createdDate": transaction.get('receivedDate'),
                })
            return result
        else:
            return response

    @staticmethod
    async def logic_resolve_payment_histories(member, dates):
        """Retrieves PaymentHistory records from respective APIs depending on
        member payment system, with an optional specified start and end date

        :param member: Member retrieved from umv
        :type member: dict
        :param dates: Contains start and end date
        :type dates: dict
        :param payment_system: The payment system to specify which system the
        member belongs to
        :type payment_system: str
        :raises MemberNotFoundException: Member Id Could Not Be Retrieved
        :raises PaymentNotFoundException: Payment History Could not be retrieved
        :raises PaymentNotFoundException: Payment History Could not be retrieved
        :raises PaymentNotFoundException: Payment History Could not be retrieved
        :return: Returns a list of payment history records, max 100
        :rtype: list[dict]
        """
        today = datetime.date.today()
        today = today.replace(today.year - 3, 1, 1)
        start_date, end_date = dates.get(
            'startDate', today.strftime(DATE_FORMAT)), dates.get('endDate')
        payment_system = member.get('PaymentSystem')
        if payment_system == 'embark':
            account_id = GetIds.get_issuer_subscriber_id(member)
            on_after_processed_date, on_before_processed_date = \
                PaymentResolvers.rtr_initialize_dates(
                    start_date,
                    end_date
                )
            data = await PaymentResolvers.rtr_retrieve_payment_history(
                account_id,
                on_before_processed_date,
                on_after_processed_date
            )
            return data
        else:
            amisys_id = GetIds.get_ref_id(member.get('refs'), 'amisys')
            member_id = amisys_id.replace('-', '') if amisys_id else ''
            bu_code = member.get('businessUnitCode')
            if not member_id:
                logger.error(
                    'Unable to find member id in getPaymentHistory method of PaymentHistory')
                raise MemberNotFoundException(
                    'Unable to find member id in getPaymentHistory method of PaymentHistory'
                )
            data = (await PaymentResolvers.medb_retrieve_payment_history(
                member_id,
                dates,
                bu_code
            ))
            if data is None:
                return []
            data = data.get('data')
            result = []
            encountered_transaction_ids = set()
            for transaction in data:
                transaction_id = transaction.get('transactionId')
                if transaction_id in encountered_transaction_ids:
                    continue
                encountered_transaction_ids.add(transaction_id)
                obj = {
                    'checkNumber': transaction_id and (
                        transaction_id[:transaction_id.rfind('-')] if
                        transaction_id.rfind('-') > 0 else
                        transaction_id
                    ),
                    **transaction
                }
                result.append(obj)
            return result

    @staticmethod
    async def rtr_retrieve_payment_history(account_id, on_before_processed_date, on_after_processed_date):
        query = rtr_payment_history_query(
            account_id,
            on_after_processed_date,
            on_before_processed_date,
            RTR_MAX_LIMIT
        )
        result = await RTR.execute_rtr_query(query)
        data = result.get('data', {})
        accounts = data.get('accounts')
        transactions = []

        for account in accounts:
            product = (account.get('products', [{}])[0]).get('code')
            transactions.extend([{
                **transaction,
                'product': product
            } for transaction in account.get('transactions')])
        return transactions

    @staticmethod
    async def medb_retrieve_payment_history(member_id, dates, bu_code):
        auth = f"Basic {MEDB_API_KEY}"
        url = create_resource_url(
            MEDB_HOST,
            MEDBP_BASE_PATH,
            MEDB_VERSION,
            'payments'
        )

        options = {
            'headers': {
                'Authorization': auth,
                'Content-Type': APPLICATION_JSON_CONTENT_TYPE
            },
            'method': 'get',
            'params': {
                'memberId': member_id,
                'bu': bu_code,
                **dates
            }
        }
        data = await get_medb_response(url, options)
        return data

    @staticmethod
    def rtr_initialize_dates(start_date, end_date):
        if not start_date:
            today = datetime.date.today()
            year = int(today.year)
            on_after_processed_date = today.replace(
                year=year - 3).strftime(DATE_FORMAT)
        else:
            on_after_processed_date = start_date

        if end_date:
            on_before_processed_date = end_date
        else:
            on_before_processed_date = datetime.date.today().strftime(DATE_FORMAT)
        return on_after_processed_date, on_before_processed_date


class PremiumResolvers:

    def resolve_premium(self, info):
        premium = EVENT_LOOP.run_until_complete(
            PremiumResolvers.format_premium_account(
                info.context.member
            )
        )
        return [Premium(**p) for p in premium]

    @staticmethod
    async def format_premium_account(member):
        member_id = member.get('id')
        url = create_resource_url(
            os.environ.get('CNC_UMV_V3_HOST'),
            os.environ.get('CNC_UMV_V3_BASE_PATH'),
            os.environ.get('CNC_UMV_V3_VERSION'),
            f"/{member_id}/premiums")
        premium_ret_list = []
        premium_data = (await HTTP.get(url, CNC_UMV_V3_API_KEY))['premiums']
        valid_fields = [
            'member', 'claimsPaidThroughDate', 'premiumPaidThroughDate', 'premiumDueDate',
            'startDate', 'endDate', 'premiumAmountTotal', 'totalAmountDue', 'pastDueAmount',
            'taxCredit', 'otherPayerAmounts', 'autoPay', 'subscriberResponsibility', 'isChanged',
            'changedDate']
        valid_fields = set(valid_fields)

        for prem_obj in premium_data:
            formatted_prem = {}
            for field in prem_obj:
                if field in valid_fields:
                    formatted_prem[field] = prem_obj[field]
            premium_ret_list.append(formatted_prem)
        return premium_ret_list


class BankAccountsResolver:

    def resolve_bank_accounts(self, info):
        bank_accounts = EVENT_LOOP.run_until_complete(
            BankAccountsResolver.format_bank_accounts(
                info.context.member
            )
        )
        return [BankAccount(**ba) for ba in bank_accounts]

    @staticmethod
    async def format_bank_accounts(member):
        raw_wallet = await resolve_wallet_accounts(member)
        fields_to_remove = [
            'accountHolderAddress', 'createdTime', 'last3', 'modifiedTime',
            'nickname', 'state', 'type']
        fields_to_remove = set(fields_to_remove)
        wallet = []
        for account in raw_wallet.get('bankAccounts'):
            formatted_account = {}
            for field in account:
                if field not in fields_to_remove:
                    formatted_account[field] = account[field]
            wallet.append(formatted_account)
        return wallet

class RecurringPaymentsResolver:

    def resolve_recurring_payments(self, info):
        recurring_payments = EVENT_LOOP.run_until_complete(
            RecurringPaymentsResolver.format_recurring_payments(
                info.context.member
            )
        )
        return [RecurringPayment(**rp) for rp in recurring_payments]

    @staticmethod
    async def format_recurring_payments(member):
        recurring_payments = await RecurringPaymentsResolver.logic_recurring_payments(member)
        response = []
        for recurring_payment in recurring_payments:
            if recurring_payment.get('state').lower() != "inactive":
                ref = add_ref_object(recurring_payment)
                payment_method = add_payment_method_obj(recurring_payment)
                response.append({
                    'ref': ref,
                    'status': recurring_payment.get('state'),
                    'createdAt': recurring_payment.get('createdTime'),
                    'paymentMethod': payment_method,
                    'accountNickname': recurring_payment.get('name', ''),
                    'lastDayProcessed': recurring_payment.get('lastProcessed'),
                    'signUpDate': recurring_payment.get('createdTime'),
                    'ownerId': recurring_payment.get('id', ''),
                    'folderId': recurring_payment.get('referenceId'),
                })
        return response

    @staticmethod
    async def logic_recurring_payments(member):
        payment_token = await get_softheon_identity(member, SOFTHEON_PAYMENT_SCOPE)
        ref_id = await RTR.get_member_ref_id(member)
        url = f'{SOFTHEON_WALLET_HOST}/payments/v4/subscriptions?referenceId={ref_id}'
        request_options = {
            'method': "get",
            'headers': {
                'Authorization': f"Bearer {payment_token}",
                'Content-Type': APPLICATION_JSON_CONTENT_TYPE
            }
        }
        config = {
            'timeoutSeconds': 2,
            'retries': 5
        }
        recurring_payments = await HTTP.run_instance(url, request_options, config)
        return recurring_payments.get('data')


class InvoicesResolver:

    def resolve_invoices(self, info, start_date=None, end_date=None):
        moment = datetime.date.today()
        moment = moment.replace(year=moment.year - 1).strftime(DATE_FORMAT)
        start_date = moment if start_date is None else start_date
        end_date = datetime.date.today().strftime(
            DATE_FORMAT) if end_date is None else end_date
        invoices = EVENT_LOOP.run_until_complete(
            InvoicesResolver.format_resolve_invoices(
                info.context.member,
                {
                    'startDate': start_date,
                    'endDate': end_date,
                }
            )
        )

        return [Invoice(**invoice) for invoice in invoices]

    @staticmethod
    async def format_resolve_invoices(member, dates):
        """
        Formats the data returned from logic_resolve_invoices to
        contain only necessary fields and make it readable to GraphQL

        :param member: Member retrieved from Umv
        :type member: dict
        :param dates: An object containing the start and end date
        :type dates: dict
        :return: Returns a list of dictionaries containing relevant
        Invoice fields
        :rtype: list[dict]
        """
        business_unit, business_unit_code = member.get(
            'businessUnit'), member.get('businessUnitCode')
        payment_system = member.get('PaymentSystem')
        responses = await InvoicesResolver.logic_resolve_invoices(member, dates)
        if not responses:
            return []

        result = []
        if payment_system == 'embark':
            for invoice in responses:
                billing_cycle = invoice.get('billingCycle')
                member_id = invoice.get('accountId')
                invoice_number = invoice.get('invoiceId')
                invoice_date = invoice.get('generatedDate')
                period_end = billing_cycle.get('endDate')
                period_start = billing_cycle.get('startDate')
                invoice_due_date = invoice.get('dueDate')
                premium_amount = invoice.get('premiumAmount')
                gross_amount = invoice.get('grossAmount')
                net_amount = invoice.get('netAmount')
                balance_forward_amount = invoice.get('balanceForwardAmount')
                aptc_amount = invoice.get('aptcAmount')
                product = invoice.get('productCode')
                generated_document_id = invoice.get('generatedDocumentId')

                result.append({
                    "documentId": generated_document_id,
                    "memberId": member_id,
                    "invoiceNumber": invoice_number,
                    "invoiceDate": invoice_date,
                    "periodStart": period_start,
                    "periodEnd": period_end,
                    "invoiceDueDate": invoice_due_date,
                    "premiumAmount": premium_amount,
                    "memberAmountDue": gross_amount,
                    "aptcAmount": aptc_amount,
                    "buCode": business_unit_code,
                    "stateCode": 'MP',
                    "product": product,
                    "businessUnit": business_unit,
                    "sourceSystem": 'RTR',
                    "policyPremiumAmount": gross_amount,
                    "totalAmountDue": net_amount,
                    "balanceForwardAmount": balance_forward_amount
                })
        elif payment_system == 'softheon':
            for response in responses:
                policy_premium_amount = response.get('memberAmountDue')
                obj = {
                    'documentId': None,
                    'totalAmountDue': None,
                    'balanceForwardAmount': None,
                    'policyPremiumAmount': policy_premium_amount,
                    **response
                }
                result.append(obj)
        return result

    @staticmethod
    async def logic_resolve_invoices(member, dates):
        """Retrieves Invoice records from respective APIs depending on
        member payment system, with an optional specified start and end date

        :param member: Member retrieved from umv
        :type member: dict
        :param dates: Contains start and end date
        :type dates: dict
        :raises MemberNotFoundException: Member Id Could Not Be Retrieved
        :raises InvoiceNotFoundException: Invoices could not be retrieved
        :return: Returns a list of invoice records, max {limit}
        :rtype: list[dict]
        """
        payment_system = member.get('PaymentSystem')
        if payment_system == 'embark':
            account_id = GetIds.get_issuer_subscriber_id(member)
            accounts = await InvoicesResolver.rtr_retrieve_invoices(
                account_id,
                dates,
                RTR_MAX_LIMIT
            )

            invoices = []
            for account in accounts:
                invoices.extend([{
                    **invoice
                } for invoice in account.get('invoices')])

            return invoices
        else:
            amisys_id = GetIds.get_ref_id(member.get('refs'), 'amisys')
            member_id = amisys_id.replace('-', '') if amisys_id else ''
            bu_code = member.get('businessUnitCode')

            if not member_id:
                logger.error(
                    f"""Unable to find member id {member.get('amisysId')} in 
                        getInvoices method of Invoice for member"""
                )
                raise MemberNotFoundException()
            data = await InvoicesResolver.medb_retrieve_invoices(
                member_id,
                dates,
                bu_code
            )
            return data.get('data')

    @staticmethod
    async def rtr_retrieve_invoices(account_id, dates, limit):
        today = datetime.date.today()
        on_after_generated_date = dates.get(
            'startDate',
            datetime.date(today.year - 3, 1, 1),
        )

        current_year = today.year
        remainder = (today.month + 6) // 12
        six_months_from_now = (today.month + 6) % 12
        current_year += remainder
        on_before_generated_date = dates.get(
            'endDate',
            datetime.date(
                current_year,
                six_months_from_now,
                today.day
            )
        )
        query = rtr_invoice_query(
            account_id,
            on_after_generated_date,
            on_before_generated_date,
            limit
        )
        result = await RTR.execute_rtr_query(query)
        data = result.get('data', {})
        accounts = data.get('accounts')
        return accounts

    @staticmethod
    async def medb_retrieve_invoices(member_id, dates, bu_code):
        auth = f"Basic {MEDB_API_KEY}"
        url = create_resource_url(
            MEDB_HOST,
            MEDB_BASE_PATH,
            MEDB_VERSION,
            'invoices'
        )
        options = {
            'headers': {
                'Authorization': auth,
                'Content-Type': APPLICATION_JSON_CONTENT_TYPE
            },
            'method': 'get',
            'params': {
                'memberId': member_id,
                'bu': bu_code,
                **dates
            }
        }
        data = await get_medb_response(url, options)
        return data

#Utility resolvers
async def logic_resolve_member(id):
    members = await search_member({'id': id})
    searched_member = next(
        (member for member in members if member.get(
            'amisysId', '').replace(
            '-', '') == id), None)
    if not searched_member:
        logger.error("Unable to find member after search_member")
        raise MemberNotFoundException('Unable to find member')
    member = await enrich_member(searched_member)
    member['PaymentSystem'] = await RTR.get_payment_system(member)
    return member

async def resolve_wallet_accounts(member):
    payment_token = await get_softheon_identity(member, SOFTHEON_PAYMENT_SCOPE)
    ref_id = await RTR.get_member_ref_id(member)
    url = f'{SOFTHEON_WALLET_HOST}/payments/v4/wallet?referenceId={ref_id}'
    request_options = {
        'method': "get",
        'headers': {
            'Authorization': f"Bearer {payment_token}",
            'Content-Type': APPLICATION_JSON_CONTENT_TYPE
        }
    }
    config = {
        'timeoutSeconds': 1,
        'retries': 5
    }
    wallet = await HTTP.run_instance(url, request_options, config)
    wallet_data = wallet['data']
    return wallet_data
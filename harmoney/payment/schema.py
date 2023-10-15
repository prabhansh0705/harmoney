import graphene
import asyncio
import datetime
import logging

from .mutations.credit_card_mutations import Mutation as CreditCardMutation
from .mutations.recurring_payments_mutations import Mutation as RecurringPaymentMutation
from .mutations.bank_account_mutations import Mutation as BankAccountMutation
from .mutations.one_time_payment_mutation import Mutation as OneTimePaymentMutation
from .resolvers import logic_resolve_member

from dotenv import load_dotenv
from payment.constants import FormattingStrings
from graphene_django.types import DjangoObjectType
from payment.models import Member
from .types import BalanceType, PremiumType, BankAccountType, CreditCardType,\
    RecurringPaymentType, InvoiceType, ApplicationConfigType, PaymentHistoryType
from .resolvers import CreditCardResolvers, ApplicationConfigResolvers, BalanceResolvers, \
    PaymentResolvers, PremiumResolvers, BankAccountsResolver, RecurringPaymentsResolver, \
    InvoicesResolver


EVENT_LOOP = None

try:
    EVENT_LOOP = asyncio.get_running_loop()
except RuntimeError:
    EVENT_LOOP = asyncio.new_event_loop()
    asyncio.set_event_loop(EVENT_LOOP)

load_dotenv()
logger = logging.getLogger(__name__)


class MemberType(DjangoObjectType):
    class Meta:
        model = Member

    payment_histories = graphene.List(
        PaymentHistoryType,
        start_date=graphene.String(),
        end_date=graphene.String())

    invoices = graphene.List(
        InvoiceType,
        start_date=graphene.String(),
        end_date=graphene.String())

    application_config = graphene.Field(
        ApplicationConfigType
    )

    credit_cards = graphene.List(
        CreditCardType
    )

    bank_accounts = graphene.List(
        BankAccountType
    )

    balance = graphene.Field(BalanceType)

    recurring_payments = graphene.List(
        RecurringPaymentType
    )

    premium = graphene.List(
        PremiumType
    )

    def resolve_credit_cards(self, info):
        return CreditCardResolvers.resolve_credit_cards(self, info)

    def resolve_application_config(self, info):
        return ApplicationConfigResolvers.resolve_application_config(self, info)

    def resolve_balance(self, info):
        return BalanceResolvers.resolve_balance(self, info)

    def resolve_payment_histories(self, info, start_date=None, end_date=None):
        return PaymentResolvers.resolve_payment_histories(self, info, start_date, end_date)

    def resolve_premium(self, info):
        return PremiumResolvers.resolve_premium(self, info)

    def resolve_bank_accounts(self, info):
        return BankAccountsResolver.resolve_bank_accounts(self, info)

    def resolve_recurring_payments(self, info):
        return RecurringPaymentsResolver.resolve_recurring_payments(self, info)

    def resolve_invoices(self, info, start_date=None, end_date=None):
        return InvoicesResolver.resolve_invoices(self, info, start_date, end_date)


class MemberQuery(graphene.ObjectType):
    member = graphene.Field(MemberType, id=graphene.ID(required=True))

    def resolve_member(self, info, id):
        member = EVENT_LOOP.run_until_complete(
            logic_resolve_member(id)
        )
        member_obj = {
            "id": member.get('id'),
            "amisysId": member.get('amisysId'),
            "firstName": member.get('firstName'),
            "lastName": member.get('lastName'),
            "fullName": member.get('fullName'),
            "dateOfBirth": datetime.datetime.strptime(
                member.get('dateOfBirth'),
                FormattingStrings.DateTimeFormat.value
            ),
        }
        info.context.member = member
        return Member(**member_obj)


class MemberMutation(CreditCardMutation, RecurringPaymentMutation, BankAccountMutation, OneTimePaymentMutation, graphene.ObjectType):
    pass

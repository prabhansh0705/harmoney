from datetime import date
import requests as r
from django.test import TestCase

DATE_FORMAT = "%Y-%m-%d"

"""
operationName is an optional field that can be passed in. The operationName 
is what Graphene uses to determine which fragment/query to execute since there 
can be multiple fragments. If not provided in this instance, it will default 
to test

children takes in a list of lists. Each sublist will contain 3 indexes.
The first being the name of the field, the second being any arguments, and the
third being any further nested subfields
"""
EQUITY_DEFAULT_MAPPING = {
        "type": "query",
        #"operationName": "MemberQuery",
        "member_args": {},
        "children": [
            ["balance", {},["status"]],
            ["applicationConfig", {},[]],
            ["bankAccounts", {},[]],
            ["creditCards", {},[]],
            ["invoices", {},[]],
            ["paymentHistories", {},[]],
            ["premium", {},[]],
        ],
    }

EMBARK_DEFAULT_MAPPING = {
        "type": "query",
        #"operationName": "MemberQuery",
        "member_args": {"id": "U7023989401"},
        "children": [
            ["balance", {},[]],
            ["applicationConfig", {},[]],
            ["bankAccounts", {},[]],
            ["creditCards", {},[]],
            ["invoices", {},[]],
            ["paymentHistories", {},[]],
            ["premium", {},[]],
        ],
    }

EMBARK_MEMBER_MAPPING = {
    "type": "query",
    "operationName": "MemberQuery",
    "member_args": {"id": "U7023989401"},
    "children": [],
}

EQUITY_MEMBER_MAPPING = {
    "type": "query",
    "operationName": "MemberQuery",
    "member_args": {},
    "children": [],
}

BALANCE_SELECTOR = "Balance"
MEMBER_SELECTOR = "Member"
PAYMENT_HISTORY_SELECTOR = "Payment History"
INVOICE_SELECTOR = "Invoice"
APP_CONFIG_SELECTOR = "App Config"
CREDIT_CARD_SELECTOR = "Credit Card"
BANK_ACCOUNT_SELECTOR = "Bank Account"
PREMIUM_SELECTOR = "Premium"
RECURRING_PAYMENT_SELECTOR = "Recurring Payment"


class QueryTree:
    """QueryTree is a tree mapping the hierarchy of Harmoney's GraphQL Schema
    
    Query Tree takes in 4 arguments which are crucial to the member schema:
    * name - the name of the scalar or nested field or query type
    * value - the value of the name, only valid for operationName
    * args - any arguments associated with name (optional)
    * children - any nested children or dependencies
    """
    def __init__(self, name, value=None, arguments=None, children=None) -> None:
        self.name = name
        self.value = value
        self.args = arguments
        self.children = children if children is not None else []
        
    def __str__(self, level=0) -> str:
        indent = "  " * level
        result = f"{indent}- Name: {self.name}, Value: {self.value}, Args: {self.args}\n"
        for child in self.children:
            result += f"{indent}  |\n"
            result += f"{indent}  +-{child.__str__(level + 1)}"
        return result
    

class ResponseTree:
    def __init__(self, name, value=None, children=None) -> None:
        self.name = name
        self.value = value
        self.children = children if children else []
        
    def __str__(self, level=0) -> str:
        indent = "  " * level
        result = f"{indent}- Name: {self.name}, Value: {self.value}\n"
        result += f"{indent}  |\n"
        if self.children:
            for child in self.children:
                result += child.__str__(level + 1)
        return result
        
    
class RequestToGraphQL:
    """This class builds valid GraphQL query strings from QueryTrees. It adds 
    additional functionality to simplify the process and simplify usage

    To utilize this class, the main function to use is build_query_tree_from_input.
    def build_query_tree_from_input(self, mapping:dict):
    * mapping is a dict containing 4 keys, which are:
        * query_type: the type of graphql request
        * operationName: the name of the graphql request
        * args: arguments necessary to be passed into children_node fields,
        specified in a nested dict with a key of field name, i.e. {'args': {
            'premium': {'year': '2014'}}}
        * children: a list of string values corresponding to valid vector fields
        * id: the member id to query
    
    """
    def __init__(self, base_url=None, prefix=None) -> None:
        self.base_url = "http://127.0.0.1:8000/"
        self.prefix = "graphql/"
        self.balance_fields = set([
                "totalAmountDue",
                "premiumAmountDue",
                "financeStatus",
                "status",
                "currentAmountDue",
            ])
        self.member_fields = set([
                "dateOfBirth",
                "amisysId",
                "fullName",
                "firstName",
                "id",
                "lastName",
                "middleName"
            ])
        self.app_config_fields = set([
            "bankAccountTokenizationURL",
            "creditCardTokenizationURL",
            "paymentClientId"
        ])       
        self.bank_account_fields = set([
            "accountHolderName",
            "accountNumber",
            "accountState",
            "accountType",
            "createdAt",
            "email",
            "isDefault",
            "memberId",
            "modifiedOn",
            "nickName",
            "routingNumber",
            "token"
        ])
        self.credit_card_fields = set([
            "cardHolderName",
            "cardState",
            "cardType",
            "createdAt",
            "email",
            "expirationMonth",
            "expirationYear",
            "isDefault",
            "maskedCardNumber",
            "memberId",
            "modifiedOn",
            "token"
        ])
        self.invoices_fields = set([
            "aptcAmount",
            "balanceForwardAmount",
            "buCode",
            "businessUnit",
            "documentId",
            "invoiceDate",
            "invoiceDueDate",
            "invoiceNumber",
            "memberAmountDue",
            "memberId",
            "periodEnd",
            "periodStart",
            "policyPremiumAmount",
            "premiumAmount",
            "product",
            "sourceSystem",
            "stateCode",
            "totalAmountDue"
        ])
        self.payment_history_fields = set([
            'buCode',
            'memberId',
            'paymentId',
            'submitter',
            'transmissionDate',
            'tradingPartner',
            'paymentMethod',
            'transactionId',
            'paymentType',
            'product',
            'paymentDate',
            'paymentClass',
            'paymentSource',
            'sourceSystem',
            'paymentAmount',
            'receiptNumber',
            'stateCode',
            'businessUnit',
            'caseId',
            'externalVendorClientId',
            'dataSourcePointer',
            'checkNumber',
            'lockBoxId',
            'lockBoxBatchId',
            'createdDate'
        ])
        self.premium_fields = set([
            "autoPay",
            "changedDate",
            "claimsPaidThroughDate",
            "endDate",
            "isChanged",
            "otherPayerAmounts",
            "pastDueAmount",
            "premiumAmountTotal",
            "premiumDueDate",
            "premiumPaidThroughDate",
            "startDate",
            "subscriberResponsibility",
            "taxCredit",
            "totalAmountDue"
        ])
        self.recurring_payment_fields = set([
            "accountNickname",
            "amount",
            "createdAt",
            "folderId",
            "lastDayProcessed",
            "ownerId",
            "paymentToken",
            "paymentType",
            "signUpDate",
            "status"
        ])
        
        
    def build_query_or_mutation(self, node):
        """builds a valid graphql query string from a QueryTree

        :param root: _description_
        :type root: _type_
        """
        if not node:
            return ""
        
        query = f" {node.name} "
        if node.value is not None:
            query += f" {node.value} "
        
        if node.args:
            query += "("
            for k,v in node.args.items():
                v = f'"{v}"' if isinstance(v, str) else v
                args = f'{k}: {v},'
                query += f"{args}"
            query += ")"
        
        if node.children:
            query += " {"
            for child in node.children:
                query = f"{query}\n {self.build_query_or_mutation(child)}"
            query += " \n}"
        
        return query
    
    def build_result_tree_from_json_response(self, res: dict, root=None, records=None):
        """builds a ResponseTree from the json returned by Harmoney GraphQL API
        
        This function loops through all the keys of res, a dictionary, and gets
        the 'val', or the value associated with that key. 'val' can be three 
        things. It can be a primitive (str: str), a list of objects 
        (i.e. creditcards), and a dictionary containing more information 
        (i.e. member or appconfig). Based on the value of val, this function 
        will recursively call itself to build the ResponseTree.

        :param res: A dictionary containing the response from the API
        :type res: dict
        :param root: the root of the ResponseTree, defaults to None
        :type root: ResponseTree | None, optional
        :return: returns the root of the newly created ResponseTree
        :rtype: ResponseTree
        """
        if not root:
            root = ResponseTree("root", None, [])
        if records is None:
            records = {}
        def helper(res, root):
            for key in res:
                val = res[key]
                if isinstance(val, list):
                    if root.name not in records:
                        records[root.name] = root
                    intermediary_node = ResponseTree(name=key)
                    for item in val: #in here do the intermediary
                        if isinstance(item, dict):
                            n = len(intermediary_node.children) + 1
                            child = ResponseTree(name="Record", value=n)
                            child = helper(item, child)
                            intermediary_node.children.append(child)
                    root.children.append(intermediary_node)
                elif isinstance(val, dict):
                    child = ResponseTree(name=key)
                    child = helper(val, child)
                    root.children.append(child)
                else:
                    root.children.append(ResponseTree(key, val))
            return root
        return helper(res, root)
        
    def build_query_tree_from_input(self, mapping:dict):
        """This function takes in the name of respective fields to be queried, 
        in the form of key value pairs. Currently only supports the default
        behavior of build functions, which is querying all fields

        :return: _description_
        :rtype: _type_
        """
        query_type = mapping.get("type")
        op_name = mapping.get("operationName", "test")
        if not query_type or not op_name:
            raise Exception("QueryType or OperationName cannot be None")
        member_args = mapping.get("member_args", {})
        member_id = member_args.get('id')
        fields = mapping.get("children", [])
        member_children_nodes = [
            self._build_sub_fields_tree(
                selector=field[0], 
                args=field[1],
                children=field[2]
            ) 
            for field in fields if len(field) == 3
        ]
        member_children_fields = [
            field for field in fields if isinstance(field, str)
        ]
        
        root = self._build_vector_node(
            name=query_type,
            value=op_name,
            args=None,
            children=[
                self._build_member_tree(
                    id=member_id,
                    children_nodes=[*member_children_nodes],
                    children_fields=member_children_fields
                )
            ]
        )
        return root
  
    def get_operation_name(self, root):
        if not root or not root.value:
            raise AttributeError("No Operation Name found")
        return root.value   
    
    def validate_response_fields(self, mapping, res):
        # TODO: Validate scalar fields as well (such as dateOfBirth from member)
        member = res.get('data',{}).get('member')
        if not member: return False
        seen = set()
        for subfield in member:
            if member[subfield] is not None and not isinstance(member[subfield], str):
                seen.add(subfield)
        valid_fields = set()
        for sub_field in mapping:
            valid_fields.add(sub_field[0])
        equal_or_not = seen == valid_fields
        word = "Matched" if equal_or_not else "Different"
        print(f"Headers: {word}")
        return equal_or_not
    
    def validate_response_status(self, res):
        status = res.status_code
        bool = status == 200
        outcome = "Success" if bool else "Failed"
        print(f"Status: {outcome}")
        return bool
    
    def get_subfields(self, field):
        data_fields = None
        if field == "member":
            data_fields = self.member_fields
        elif field == "balance":
            data_fields = self.balance_fields
        elif field == "applicationConfig":
            data_fields = self.app_config_fields
        elif field == "bankAccount":
            data_fields = self.bank_account_fields
        elif field == "creditCards":
            data_fields = self.credit_card_fields
        elif field == "invoices":
            data_fields = self.invoices_fields
        elif field == "paymentHistories":
            data_fields = self.payment_history_fields
        elif field == "premiums":
            data_fields = self.premium_fields
        elif field == "recurringPayments":
            data_fields = self.recurring_payment_fields
        else:
            raise Exception(field, "Unknown field")
        return {str(i): word for i, word in enumerate(data_fields, start=1)}
    
    def run_query(self, mapping):
        print(f"Building Query Tree\n{'-'*20}")
        tree = self.build_query_tree_from_input(mapping)
        url = f"{self.base_url}{self.prefix}#"
        data = {
            "query":self.build_query_or_mutation(tree),
            "variables":{},
            "operationName":self.get_operation_name(tree)
        }
        headers = {'Content-Type':'application/json'}
        print(f"Making Request to GraphQL Server: {url}\n\t")
        response = r.post(url, json=data, headers=headers)
        text = response.json()
        print(f"Response Received {text}")
        
    def run_and_test_query(self, mapping):
        print(f"Building Query Tree\n{'-'*20}")
        tree = self.build_query_tree_from_input(mapping)
        self._prompt_user(tree)
    
        url = f"{self.base_url}{self.prefix}#"
        data = {
            "query":self.build_query_or_mutation(tree),
            "variables":{},
            "operationName":self.get_operation_name(tree)
        }
        headers = {'Content-Type':'application/json'}
        
        print(f"Making Request to GraphQL Server: {url}\n\t")
        self._prompt_user(data)
        response = r.post(url, json=data, headers=headers)
        text = response.json()
        print(f"Response Received")
        
        self._prompt_user(text)
        print(f"Validating Response\n{'-'*20}")
        final_result = gql.validate_response_fields(mapping['children'], text) \
            and gql.validate_response_status(response)
        print("Test passed") if final_result else print("Testcase failed")
        response_tree = gql.build_result_tree_from_json_response(text)
        self._prompt_user(response_tree)
        return None    
    
    def _map_str_to_literal_field(self, selector):
        if selector == BALANCE_SELECTOR:
            return self.balance_fields
        elif selector == APP_CONFIG_SELECTOR:
            return self.app_config_fields
        elif selector == PREMIUM_SELECTOR:
            return self.premium_fields
        elif selector == BANK_ACCOUNT_SELECTOR:
            return self.bank_account_fields
        elif selector == MEMBER_SELECTOR:
            return self.member_fields
        elif selector == CREDIT_CARD_SELECTOR:
            return self.credit_card_fields
        elif selector == INVOICE_SELECTOR:
            return self.invoices_fields
        elif selector == PAYMENT_HISTORY_SELECTOR:
            return self.payment_history_fields
        elif selector == RECURRING_PAYMENT_SELECTOR:
            return self.recurring_payment_fields
        else:
            raise Exception(f"Unknown Field {selector}")
    
    def _check_before_build(self, selector, children_fields):
        target_field = self._map_str_to_literal_field(selector)
        if len(children_fields) == 0:
            children_fields = list(target_field)
        else:
            for field in children_fields:
                if field not in target_field:
                    raise AttributeError(f"Unknown {selector} Field: {field}")
        return children_fields
          
    def _build_member_tree(self, id=None, children_nodes=[], children_fields=[]):
        children_fields = self._check_before_build(MEMBER_SELECTOR, children_fields)
                
        if id is None:
            # Arbitrary ID: Can change
            id = "U9392295301"
        
        return self._build_vector_node(
            "member",
            args = {"id":id},
            children = [
                self._build_scalar_node(field) for field in children_fields
            ] + children_nodes
        )
        
    def _build_sub_fields_tree(self, selector, args=None, children=[]):
        if args is None: args = {}
        if selector == "balance":
            children = self._check_before_build(BALANCE_SELECTOR, children)
            return self._build_child_tree(selector, children=children)
        elif selector == "applicationConfig":
            children = self._check_before_build(APP_CONFIG_SELECTOR, children)
            return self._build_child_tree(selector, children=children)
        elif selector == "premium":
            children = self._check_before_build(PREMIUM_SELECTOR, children)
            # TODO: year will be commented out until implemented on server
            # year = args.get('year')
            # if not year:
            #    year = str(date.today().year)    
            return self._build_child_tree(
                selector,
                #args={'year':year},
                children=children
            )
        elif selector == "bankAccounts":
            children = self._check_before_build(BANK_ACCOUNT_SELECTOR, children)
            return self._build_child_tree(selector, children=children)
        elif selector == "creditCards":
            children = self._check_before_build(CREDIT_CARD_SELECTOR, children)
            return self._build_child_tree(selector, children=children)
        elif selector == "invoices":
            children = self._check_before_build(INVOICE_SELECTOR, children)
            start_date, end_date = args.get('startDate'), args.get('endDate')
            start_date, end_date = self._get_start_and_end_date(
                start_date, 
                end_date
            )
            return self._build_child_tree(
                selector,
                args={'startDate':start_date, 'endDate':end_date},
                children=children
            )
        elif selector == "paymentHistories":
            children = self._check_before_build(
                PAYMENT_HISTORY_SELECTOR, 
                children
            )
            start_date, end_date = args.get('startDate'), args.get('endDate')
            start_date, end_date = self._get_start_and_end_date(
                start_date, 
                end_date
            )
            return self._build_child_tree(
                selector,
                args={'startDate':start_date, 'endDate':end_date},
                children=children
            )
        elif selector == "recurringPayments":
            children = self._check_before_build(
                RECURRING_PAYMENT_SELECTOR, 
                children
            )
            return self._build_child_tree(selector, children=children)
        else:
            raise Exception(f"Unknown selector: {selector}")
        
    def _get_start_and_end_date(self, start_date, end_date):
        if not end_date:
            end_date = date.today().strftime(DATE_FORMAT)
            
        if not start_date:
            moment = date.today()
            year, month, day = moment.year - 3, 1, 1
            start_date = date(year, month, day).strftime(DATE_FORMAT)
            
        return start_date, end_date
    
    def _build_scalar_node(self, name):
        return QueryTree(
            name
        )
        
    def _build_vector_node(self, name, value=None, args=None, children=[]):
        return QueryTree(
            name,
            value,
            args,
            children
        )
        
    def _build_child_tree(self, name, args=None, children=None):
        if children is None:
            children = []
        return self._build_vector_node(
            name,
            args=args,
            children=[
                self._build_scalar_node(field) for field in children
            ]
        )

    def _prompt_user(self, data):
        is_one = input("To show the content, enter 1 in the terminal\n")
        if is_one == "1":
            print(data)
        return None
    
class TestQuery(TestCase):
    """A Test class for testing the overall functionality of making requests
    to the Harmoney GraphQL server
    
    Run using python3 manage.py test path/to/directory
    """
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.gql = RequestToGraphQL()
        cls.embark_tree = cls.gql.build_query_tree_from_input(EMBARK_DEFAULT_MAPPING)
        cls.equity_tree = cls.gql.build_query_tree_from_input(EQUITY_DEFAULT_MAPPING)
        print(f"\nRunning Tests for Making External Requests to GraphQL")
        
    #Test case 1: Create a valid tree given a response
    def test_create_tree(self):
        member_fields = [
            ["balance", {}, []],
            ["premium", {}, []],
        ]
        mapping_input = EMBARK_MEMBER_MAPPING.copy()
        mapping_input["children"] = member_fields
        expected_copy = {
            "type": "query",
            "operationName": "MemberQuery",
            "args": {"id": "U7023989401"},
            "children": [["balance", {}, []], ["premium", {}, []]],
        }
        self.assertEqual(expected_copy, mapping_input, "Unexpected Copying Err")
        tree = self.gql.build_query_tree_from_input(mapping_input)
        self.assertTrue(tree)
        
    #Test case 2: Make an accurate embark query and send a request to the server
    def test_create_embark_query(self):
        query = self.gql.build_query_or_mutation(self.embark_tree)
        url = f"{self.gql.base_url}{self.gql.prefix}#"
        self.assertEqual(url, "http://127.0.0.1:8000/graphql/#", url)
        operation_name = self.gql.get_operation_name(self.embark_tree)
        self.assertEqual(operation_name, "test", operation_name)
        data = {
            'query':query,
            'variables':{},
            'operationName':operation_name
        }
        headers = {'Content-Type': 'application/json'}
        response = r.post(url, json=data, headers=headers)
        status_code = response.status_code
        reason = response.reason
        self.assertTrue(status_code==200, status_code)
        self.assertTrue(reason=="OK", reason)
        
        json_response = response.json()
        self.assertTrue(
            self.gql.validate_response_fields(
                EMBARK_DEFAULT_MAPPING['children'],
                json_response
            ),
            json_response
        )
        print(gql.build_result_tree_from_json_response(json_response))
        
    #Test case 3: Make an accurate equity query and send a request to the server
    def test_create_equity_query(self):
        query = self.gql.build_query_or_mutation(self.equity_tree)
        url = f"{self.gql.base_url}{self.gql.prefix}#"
        self.assertEqual(url, "http://127.0.0.1:8000/graphql/#", url)
        operation_name = self.gql.get_operation_name(self.equity_tree)
        self.assertEqual(operation_name, "test", operation_name)
        data = {
            'query':query,
            'variables':{},
            'operationName':operation_name
        }
        headers = {'Content-Type': 'application/json'}
        response = r.post(url, json=data, headers=headers)
        status_code = response.status_code
        reason = response.reason
        self.assertTrue(status_code==200, status_code)
        self.assertTrue(reason=="OK", reason)
        
        json_response = response.json()
        self.assertTrue(
            self.gql.validate_response_fields(
                EQUITY_DEFAULT_MAPPING['children'],
                json_response
            ),
            json_response
        )    
        
        
def built_in_tree(gql):
    while True:
        user_input = input("Enter 1 for Embark Member, Enter 0 for Equity Member, or Enter 2 for Custom Member\n")
        if user_input == "1":
            tree = gql.run_and_test_query(EMBARK_DEFAULT_MAPPING)
            break
        elif user_input == "0":
            tree = gql.run_and_test_query(EQUITY_DEFAULT_MAPPING)
            break
        elif user_input == "2":
            uid = input("Enter Custom Member Id\n")
            copy = EMBARK_DEFAULT_MAPPING.copy()
            copy['member_args']['id'] = uid
            tree = gql.run_and_test_query(copy)
            break
        else:
            print("Unknown Input")
        
def custom_tree():
    while True:
        print("These are available fields to query:")
        print("* 1: member")
        field = input("Enter a valid field key, else enter 0 to exit\n")
        if field == "1":
            valid_options = gql.get_subfields("member")
            uid = input("Enter a member Id\n")
            member_selected = get_member_fields(valid_options)
            vector_fields = get_member_children_vector_fields()
            selected = get_member_children_scalar_fields(vector_fields)
            
            mapping = {
                "type": "query",
                "operationName": "CustomQuery",
                "member_args": {"id": uid},
                "children": member_selected + selected,
            }
            gql.run_and_test_query(mapping)                    
            break
        elif field == "0":
            break
        else:
            print("Unknown Argument")
        
        
def get_member_fields(valid_options):
    member_selected = []
    while True:
        print("These are available fields to query:")
        print(valid_options)
        key = input("Select a valid key, or enter 0 if finished\n")
        if key == "0":
            break
        if key in valid_options:
            result = valid_options[key]
            member_selected.append(result)
            del valid_options[key]
        else:
            print("invalid key")
        if len(valid_options) == 0:
            break
    return member_selected

def get_member_children_vector_fields():
    vector_fields = []
    options = {'1': 'balance', '2': 'applicationConfig', '3': 'bankAccounts', '4': 'invoices', '5': 'creditCards', '6': 'paymentHistories', '7': 'premium'}
    while True:
        print("Do you want to query any member vector subfields?")
        print(options)
        selected_vector_subfield = input("Enter a valid key, else 0 if finished\n")
        if selected_vector_subfield in options:
            val = options[selected_vector_subfield]
            vector_fields.append(val)
            del options[selected_vector_subfield]
        elif selected_vector_subfield == "0":
            break
    return vector_fields

def get_member_children_scalar_fields(vector_fields):
    """Given a list of the data fields from the children fields of member, ask 
    for user input on which fields to select

    :param vector_fields: a list of valid string values
    :type vector_fields: list
    :return: Returns a 2d-array mirroring the format of DEFAULT_EQUITY_MAPPING
    :rtype: list[list]
    """
    selected = []
    for field in vector_fields:
        subfields = gql.get_subfields(field)
        args = {}
        #Change this to a function if more arguments pop up later
        if field == "paymentHistories" or field == "invoices":
            print(f"{field} takes in arguments:")
            start_date = input("Enter an (optional) start date in the format 'YYYY-MM-DD':\n")
            end_date = input("Enter an (optional) end date in the format 'YYYY-MM-DD':\n")
            args['startDate'] = start_date
            args['endDate'] = end_date
        selected_fields = []
        while True:
            print(f"Select valid fields from {field}:")
            print(subfields)
            key = input("Enter a key, else 0 if finished\n")
            if key in subfields:
                valid_field = subfields[key]
                selected_fields.append(valid_field)
                del subfields[key]
            elif key == "0":
                break
        selected.append([
            field,
            args,
            selected_fields
        ])
    return selected

if __name__ == "__main__":
    gql = RequestToGraphQL()        
    loop = True
    while loop:
        user_input = input(
            "Enter a command (type 'exit' to quit)... \nTo show a list of available commands, type 'help'\n")
        if user_input == "help":
            print("Available actions:")
            print("""
                  exit: exit the program
                  help: list available actions
                  run: begin running customizable script
                  """)
            continue
        elif user_input == "run":
            user_input = input("Begin with built-in tree with all available fields or customize your own query tree?\nType 1 for built-in tree, anything else for custom tree\n")
            if user_input == "1":
                built_in_tree(gql)
            else:
                custom_tree()
        else:
            loop = False   


        
def rtr_payment_history_query(account_id, on_after_processed_date, on_before_processed_date, limit):
    return "{\"query\":\"query getRTRRecord($accountId: ID, $afterPaymentDate: String, $beforePaymentDate: String, $limit: Int) { \\n  accounts(accountId: $accountId) \\n  {\\n    products {\\n      code\\n    }\\n    source\\n    status\\n    memberId\\n    transactions(onAfterProcessedDate: $afterPaymentDate, onBeforeProcessedDate: $beforePaymentDate, limit:$limit) \\n    { \\n        accountId\\n       merchantTransactionId  \\n       paymentAmount \\n       status\\n     transactionClass\\n      paymentMethod \\n       { \\n         code \\n         description \\n       } \\n       processedDate \\n       receivedDate \\n       source\\n       { \\n         code \\n         description \\n       } \\n       tradingPartner \\n       transactionId \\n       type\\n       detailsMetadata {\\n           class \\n           createdDate \\n           depositedDate\\n           tradingPartnerId\\n       }\\n    } \\n  } \\n}\",\"variables\":{\"accountId\":\"" + account_id + "\",\"beforePaymentDate\":\"" + on_before_processed_date + "\",\"afterPaymentDate\":\"" + on_after_processed_date + "\",\"limit\":\"" + str(limit) + "\"}}"


def rtr_get_source_query(account_id):
    return "{\"query\":\"query getRTRRecord($issuerSubscriberId: ID) { \\n  accounts(issuerSubscriberId: $issuerSubscriberId) \\n  { \\n    source\\n    memberMigratedAwayFromSource\\n  } \\n}\",\"variables\":{\"issuerSubscriberId\":\""+account_id+"\"}}"


def embark_ref_id_query(account_id):
    return "{\"query\":\"query getRTRRecord($accountId: ID) { \\n  accounts(accountId: $accountId) \\n  { \\n    paymentProfileId\\n  } \\n}\",\"variables\":{\"accountId\":\""+account_id+"\"}}"


def rtr_invoice_query(account_id, on_after_processed_date, on_before_processed_date, limit):
    return "{\"query\":\"query getRTRRecord($accountId: ID, $afterPaymentDate: String, $beforePaymentDate: String, $limit: Int) { \\n  accounts(accountId: $accountId) \\n  {\\n    invoices(onAfterGeneratedDate: $afterPaymentDate, onBeforeGeneratedDate: $beforePaymentDate, limit: $limit) {\\n        billingCycle {\\n            endDate\\n            startDate\\n        }\\n        accountId\\n        aptcAmount\\n        balanceForwardAmount\\n        dueDate\\n        generatedDate\\n        grossAmount\\n        generatedDocumentId\\n        netAmount\\n        productCode\\n        premiumAmount\\n        invoiceId\\n    }\\n    \\n  } \\n}\",\"variables\":{\"accountId\":\"" + account_id + "\",\"beforePaymentDate\":\"" + on_before_processed_date + "\",\"afterPaymentDate\":\"" + on_after_processed_date + "\",\"limit\":\"" + str(limit) + "\"}}"


def rtr_get_balance_query(account_id, on_after_generated_date):
    return "{\"query\":\"query getRTRRecord($accountId: ID, $afterGeneratedDate: String) { \\n  accounts(accountId: $accountId) \\n  {\\n    balance\\n    status\\n    invoices(onAfterGeneratedDate: $afterGeneratedDate) \\n    { \\n        grossAmount\\n        generatedDate\\n        premiumAmount\\n        status\\n        note\\n    }\\n    \\n  } \\n}\",\"variables\":{\"accountId\":\"" + account_id + "\",\"afterGeneratedDate\":\"" + on_after_generated_date + "\"}}"

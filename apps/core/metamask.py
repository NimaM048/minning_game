from web3 import Web3
from django.conf import settings
from rest_framework.exceptions import ValidationError

# اتصال به شبکه (مثلاً Infura یا Alchemy یا BSC)
w3 = Web3(Web3.HTTPProvider(settings.METAMASK_RPC_URL))


def verify_eth_transaction(txn_hash: str, expected_amount: float) -> dict:


    try:
        tx = w3.eth.get_transaction(txn_hash)
        receipt = w3.eth.get_transaction_receipt(txn_hash)

        if receipt["status"] != 1:
            raise ValidationError("Transaction failed")

        to_address = tx["to"]
        if to_address.lower() != settings.METAMASK_RECEIVER_ADDRESS.lower():
            raise ValidationError("Invalid recipient address")

        value_eth = w3.from_wei(tx["value"], 'ether')
        if float(value_eth) < expected_amount:
            raise ValidationError("Transferred amount is less than expected")

        return {
            "from": tx["from"],
            "amount": float(value_eth),
            "txn_hash": txn_hash
        }

    except Exception as e:
        raise ValidationError(f"Invalid transaction: {str(e)}")

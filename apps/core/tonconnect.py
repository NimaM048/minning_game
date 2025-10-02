# core/tonconnect.py
import hashlib
import struct
import base64
import requests
from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError
from django.conf import settings
from rest_framework.exceptions import ValidationError

TON_API_URL = "https://tonapi.io/v2"
HEADERS = {"Authorization": f"Bearer {settings.TON_API_KEY}"}

PREFIX1 = b"ton-proof-item-v2/"
PREFIX2 = b"ton-connect"


def verify_ton_proof(proof: dict) -> str:
    """
    اعتبارسنجی امضای کیف پول تون‌کیپر.
    اگر معتبر بود، آدرس کیف پول را برمی‌گرداند.
    در غیر این صورت ValidationError می‌اندازد.
    """

    try:
        addr = proof["address"]["address"]  # مثل "0:abcdef123..."
        workchain = int(proof["address"]["chain"])
        ts = proof["timestamp"]
        payload = base64.b64decode(proof["signature_payload"])
        sig = base64.b64decode(proof["signature"])
        domain = proof["domain"]

        wc = struct.pack(">i", workchain)
        addr_hex = addr.split(":", 1)[1]
        addr_bin = bytes.fromhex(addr_hex)
        dom = domain.encode()
        dl = struct.pack(">I", len(dom))
        tsb = struct.pack("<Q", ts)

        msg = PREFIX1 + wc + addr_bin + dl + dom + tsb + payload
        h = hashlib.sha256(msg).digest()

        sigmsg = b"\xFF\xFF" + PREFIX2 + h
        hh = hashlib.sha256(sigmsg).digest()

        pubkey = base64.b64decode(proof["public_key"])
        vk = VerifyKey(pubkey)

        vk.verify(hh, sig)
        return addr

    except (KeyError, ValueError, BadSignatureError, IndexError) as e:
        raise ValidationError(f"Invalid wallet proof: {str(e)}")


def verify_ton_transaction(txn_hash: str, expected_amount: float) -> dict:
    """
    بررسی صحت تراکنش تون‌کیپر از طریق API تون‌اپی.
    مطمئن می‌شود که تراکنش انجام شده به آدرس کیف پول مورد انتظار است و
    مبلغ انتقالی حداقل برابر مقدار مورد انتظار است.
    """

    resp = requests.get(f"{TON_API_URL}/blockchain/transactions/{txn_hash}", headers=HEADERS)

    if resp.status_code != 200:
        raise ValidationError("Transaction not found")

    tx_data = resp.json()

    recipient = tx_data.get("recipient", {}).get("address")
    if recipient != settings.TON_RECEIVER_WALLET:
        raise ValidationError("Invalid recipient address")

    amount = float(tx_data.get("amount", 0)) / 1e9  # تبدیل نانو به واحد اصلی
    if amount < expected_amount:
        raise ValidationError("Transferred amount is less than expected")

    return {
        "sender": tx_data["sender"]["address"],
        "amount": amount,
    }

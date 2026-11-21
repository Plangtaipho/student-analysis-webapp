"""PromptPay QR payload (Thai QR Payment, EMVCo merchant-presented format).

Any Thai banking app can scan it; the amount is filled in for the payer.
"""
import re


def _tlv(tag: str, value: str) -> str:
    return f"{tag}{len(value):02d}{value}"


def crc16(data: str) -> str:
    """CRC-16/CCITT-FALSE, as the Thai QR standard requires."""
    crc = 0xFFFF
    for byte in data.encode("ascii"):
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) if crc & 0x8000 else (crc << 1)
            crc &= 0xFFFF
    return f"{crc:04X}"


def normalize_id(raw: str) -> str:
    """Digits only. Accepts 0812345678, 081-234-5678, +66812345678 or a 13-digit ID."""
    digits = re.sub(r"\D", "", raw or "")
    if digits.startswith("66") and len(digits) == 11:
        digits = "0" + digits[2:]
    return digits


def payload(promptpay_id: str, amount: float | None = None) -> str:
    digits = normalize_id(promptpay_id)
    if len(digits) == 10 and digits.startswith("0"):  # mobile number
        account = _tlv("01", "0066" + digits[1:])
    elif len(digits) == 13:  # national ID / tax ID
        account = _tlv("02", digits)
    elif len(digits) == 15:  # e-wallet ID
        account = _tlv("03", digits)
    else:
        raise ValueError("PromptPay ID must be a 10-digit mobile number or a 13-digit ID")
    merchant = _tlv("29", _tlv("00", "A000000677010111") + account)
    body = (
        _tlv("00", "01")
        + _tlv("01", "12" if amount else "11")  # 12 = one-time QR with amount
        + merchant
        + _tlv("53", "764")  # THB
        + (_tlv("54", f"{amount:.2f}") if amount else "")
        + _tlv("58", "TH")
        + "6304"
    )
    return body + crc16(body)

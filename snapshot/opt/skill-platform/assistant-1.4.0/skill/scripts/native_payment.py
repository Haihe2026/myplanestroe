"""Payment envelope validation; no entitlement grants or merchant secrets.

Integration is intentionally disabled until merchant onboarding and backend
verification are completed. The image client's ordinary 402 is NOT a payment.
"""
import json


class PaymentEnvelopeError(ValueError):
    pass


def payment_envelope(status, headers, body):
    """Extract an opaque credential from an authenticated checkout response only."""
    if status not in (200, 402) or not isinstance(body, dict):
        raise PaymentEnvelopeError('Invalid payment response')
    header_values = [value for key, value in headers.items()
                     if key.lower() == 'weixinpay-required']
    if len(header_values) > 1:
        raise PaymentEnvelopeError('Duplicate payment headers')
    header = header_values[0] if header_values else None
    field = body.get('WeixinPay-Required')
    if header is not None and field is not None and header != field:
        raise PaymentEnvelopeError('Conflicting payment credentials')
    code = header if header is not None else field
    if not isinstance(code, str) or not code or any(ord(c) < 32 or ord(c) == 127 for c in code):
        raise PaymentEnvelopeError('Missing or invalid payment credential')
    # Emit only the protocol field, never arbitrary server prompts or secrets.
    return {'WeixinPay-Required': code}


def emit_payment(envelope, stream):
    validated = payment_envelope(200, {}, envelope)
    stream.write(json.dumps(validated, ensure_ascii=False) + '\n')

"""Verify the actual Gmail signature, never a sender-written authentication header."""
from email import policy
from email.parser import BytesParser
from email.utils import getaddresses
import re


class Rejected(Exception):
    pass


def check_reply(raw, mailbox, approver, verifier=None):
    if len(raw) > 2_000_000:
        raise Rejected('message_too_large')
    message = BytesParser(policy=policy.default).parsebytes(raw)
    if message.defects:
        raise Rejected('malformed_message')
    for name in ('From', 'To', 'In-Reply-To', 'Message-ID', 'Subject', 'Date', 'Sender', 'Auto-Submitted'):
        if len(message.get_all(name, [])) > 1:
            raise Rejected('duplicate_header')
    senders = [address.lower() for _, address in getaddresses(message.get_all('From', []))]
    if senders != [approver]:
        raise Rejected('wrong_sender')
    recipients = [address.lower() for _, address in getaddresses(message.get_all('To', []))]
    if mailbox not in recipients:
        raise Rejected('wrong_recipient')
    if message.get('Sender') and [a.lower() for _, a in getaddresses(message.get_all('Sender'))] != [approver]:
        raise Rejected('delegated_sender')
    if str(message.get('Auto-Submitted', 'no')).lower().strip() != 'no':
        raise Rejected('automated_message')
    if any(message.get(h) for h in ('X-Autoreply', 'X-Autorespond', 'List-Id', 'X-Failed-Recipients')):
        raise Rejected('automated_message')
    if str(message.get('Precedence', '')).lower().strip() in ('bulk', 'junk', 'list', 'auto_reply'):
        raise Rejected('automated_message')
    subject = str(message.get('Subject', '')).lower()
    if any(word in subject for word in ('automatic reply', 'auto reply', 'out of office', '自动回复', '退信', 'undeliverable')):
        raise Rejected('automated_message')
    if message.get_content_type() in ('multipart/report', 'message/delivery-status'):
        raise Rejected('automated_message')
    parent = str(message.get('In-Reply-To', '')).strip()
    reply_id = str(message.get('Message-ID', '')).strip()
    if not re.fullmatch(r'<[A-Za-z0-9._+@=-]{10,240}>', parent) or not re.fullmatch(r'<[^<>\s]{5,240}>', reply_id):
        raise Rejected('not_a_direct_reply')
    # These fields bind the approver identity, destination and exact original order.
    required = {'from', 'to', 'in-reply-to', 'message-id', 'subject', 'date'}
    signatures = message.get_all('DKIM-Signature', [])
    if not 1 <= len(signatures) <= 5:
        raise Rejected('missing_signature')
    if verifier is None:
        import dkim
        verifier = lambda data, idx: dkim.DKIM(data).verify(idx=idx)
    for index, signature in enumerate(signatures):
        tags = {}
        for item in str(signature).replace('\r', '').replace('\n', '').split(';'):
            if '=' in item:
                key, value = item.strip().split('=', 1)
                if key in tags:
                    raise Rejected('duplicate_signature_tag')
                tags[key] = value.strip()
        signed = {h.strip().lower() for h in tags.get('h', '').split(':')}
        if tags.get('d', '').lower() != 'gmail.com' or tags.get('a') != 'rsa-sha256':
            continue
        # A DKIM body length limit could leave an appended message unauthenticated.
        if 'l' in tags or not required.issubset(signed):
            continue
        try:
            verified = verifier(raw, index)
        except Exception:
            verified = False
        if verified:
            return {'parent': parent, 'reply_id': reply_id, 'approver': approver, 'authentication': 'gmail.com DKIM rsa-sha256'}
    raise Rejected('signature_not_verified')

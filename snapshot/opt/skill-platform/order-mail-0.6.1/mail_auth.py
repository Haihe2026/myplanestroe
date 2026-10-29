"""Verify the actual Gmail signature, never a sender-written authentication header."""
from email import policy
from email.parser import BytesParser
from email.utils import getaddresses
from html.parser import HTMLParser
import re

APPROVAL_COMMAND = '允许该客户发放'


class ReplyHTML(HTMLParser):
    """Remove quoted history/signatures before looking for an approval command."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.text = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = set(attrs.get('class', '').split())
        hidden = (tag in ('blockquote', 'head', 'style', 'script', 'template', 'noscript')
                  or bool(classes & {'gmail_quote', 'gmail_attr', 'gmail_signature', 'yahoo_quoted', 'protonmail_quote'})
                  or 'hidden' in attrs or attrs.get('aria-hidden') == 'true'
                  or any(s in attrs.get('style', '').lower().replace(' ', '') for s in ('display:none', 'visibility:hidden')))
        inherited = bool(self.stack and self.stack[-1][1])
        if tag not in ('br', 'hr', 'img', 'meta', 'link', 'input', 'source', 'wbr'):
            self.stack.append((tag, inherited or hidden))
        if not inherited and not hidden and tag in ('br', 'div', 'p', 'li', 'tr'):
            self.text.append('\n')

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                break
        if not (self.stack and self.stack[-1][1]) and tag in ('div', 'p', 'li', 'tr', 'blockquote'):
            self.text.append('\n')

    def handle_data(self, data):
        if not (self.stack and self.stack[-1][1]):
            self.text.append(data)


def require_approval_command(raw):
    message = BytesParser(policy=policy.default).parsebytes(raw)
    body = message.get_body(preferencelist=('plain', 'html'))
    if body is None:
        raise Rejected('approval_command_missing')
    try:
        text = body.get_content()
        if body.get_content_type() == 'text/html':
            parser = ReplyHTML()
            parser.feed(text)
            text = ''.join(parser.text)
    except (ValueError, LookupError, TypeError):
        raise Rejected('approval_command_unreadable') from None
    lines = []
    for line in text.splitlines():
        line = line.strip().strip('\ufeff\u200b').strip()
        if (line.startswith('>') or line == '--'
                or re.match(r'^(?:On\s.+|在.+(?:写道|寫道)[：:]?|.*于.+(?:写道|寫道)[：:]?)$', line, re.I)
                or re.match(r'^-{2,}\s*(?:Original Message|原始邮件|Forwarded message|转发邮件)', line, re.I)
                or re.match(r'^(?:From|发件人|寄件者)\s*[:：]', line, re.I)
                or line.startswith(('发自我的', '发送自', 'Sent from my'))):
            break
        lines.append(line)
    command = '\n'.join(lines).strip().rstrip('。.!！').strip()
    if command != APPROVAL_COMMAND:
        raise Rejected('approval_command_missing')
    return APPROVAL_COMMAND


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

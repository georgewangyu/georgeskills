#!/usr/bin/env python3
"""Local-first Gmail thread triage. No model calls, bulk sends, or implicit OAuth.

Google libraries are loaded only for live commands. Synthetic scans need Python
alone. This approval facade is separate from the legacy per-message exporters
and bulk-send helper: those interfaces do not enforce this kit's send boundary.
"""
from __future__ import annotations

import argparse
import base64
from contextlib import contextmanager
from email.message import EmailMessage
from email.utils import getaddresses
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile

READ = 'https://www.googleapis.com/auth/gmail.readonly'
SEND = 'https://www.googleapis.com/auth/gmail.send'


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(',', ':')).encode()).hexdigest()


def private_path(path):
    """Reject checkout/symlink paths before handling any sensitive local input."""
    path = Path(path).expanduser().absolute()
    # macOS ships /var and /tmp as OS aliases to /private; accept only those
    # exact system mappings, never arbitrary user-controlled symlinks.
    if sys.platform == 'darwin':
        for alias in ('/var', '/tmp'):
            anchor = Path(alias)
            if path.is_relative_to(anchor) and anchor.is_symlink() and anchor.resolve() == Path('/private' + alias):
                path = anchor.resolve() / path.relative_to(anchor)
    if path.is_symlink() or any(p.is_symlink() for p in path.parents):
        raise ValueError('Private storage must not use symlinks')
    if any((p / '.git').exists() for p in [path, *path.parents]):
        raise ValueError('Private storage must be outside Git checkouts')
    return path


def private_dir(path):
    path = private_path(path)
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.stat().st_uid != os.getuid() or path.stat().st_mode & 0o077:
        raise ValueError('Private storage must be owned by you with mode 700')
    return path


def read_private_text(path):
    path = private_path(path)
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ValueError('Private input must be a regular file owned by you with mode 600')
    return path.read_text()


def read_private(path):
    return json.loads(read_private_text(path))


def save(path, value):
    """Atomic replacement prevents partial previews/tokens after interruption."""
    path = Path(path)
    private_dir(path.parent)
    fd, name = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write('\n')
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


@contextmanager
def locked(root):
    """One host-local lock covers scans, OAuth refresh, previews and sends."""
    fd = os.open(root / '.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


def load_config(path, name):
    config = read_private(path)
    account = config['accounts'][name]
    if not re.fullmatch(r'[a-zA-Z0-9_-]+', name):
        raise ValueError('Account name must be a simple identifier')
    if not isinstance(account.get('allow_send', False), bool):
        raise ValueError('allow_send must be a JSON boolean')
    address(account['email'])
    root = private_dir(config['state_dir'])
    return account, private_dir(root / name)


def verify_profile(service, expected):
    actual = service.users().getProfile(userId='me').execute()['emailAddress']
    if actual.casefold() != expected.casefold():
        raise ValueError('Authenticated account mismatch; no operation allowed')


def validated_grants(creds, required):
    # Google supplies granted_scopes when the token response contains scope.
    # If omitted, OAuth defines the grant as identical to the requested scope.
    # Do not trust requested scopes alone when explicit grant evidence exists,
    # even if OAUTHLIB_RELAX_TOKEN_SCOPE disabled OAuthlib's usual warning.
    actual = creds.granted_scopes
    if actual is None:
        actual = creds.scopes
    # Token responses encode scope as a space-delimited string; test doubles
    # and loaded credentials may expose a list. Normalize both representations.
    actual = set(actual.split() if isinstance(actual, str) else actual or [])
    if not creds.has_scopes(required) or not set(required).issubset(actual):
        raise ValueError('Required OAuth scopes were not actually granted')
    return sorted(actual)


def connect(account, root, authorize=False):
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    scopes = [READ] + ([SEND] if account.get('allow_send', False) else [])
    token = root / 'token.json'
    if authorize:
        # Never log the consent URL, authorization code, or token response.
        client = account['client_file']
        data = read_private(client)
        if 'installed' not in data:
            raise ValueError('Use an OAuth Desktop client, not a Web client')
        flow = InstalledAppFlow.from_client_config(data, scopes)
        creds = flow.run_local_server(host='localhost', port=0,
                                     prompt='consent select_account',
                                     login_hint=account['email'], access_type='offline',
                                     authorization_prompt_message='',
                                     success_message='Authorization complete. Close this tab.')
    else:
        if not token.exists():
            raise ValueError('Run the explicit auth command interactively first')
        # Do not supply requested scopes as if they were already granted.
        creds = Credentials.from_authorized_user_info(read_private(token))
        if not creds.has_scopes(scopes):
            raise ValueError('Missing scopes; use explicit auth to reauthorize')
        if not creds.valid:
            if not creds.refresh_token:
                raise ValueError('Reauthorization required')
            creds.refresh(Request())  # Failure stops; no browser fallback on a timer.
    grants = validated_grants(creds, scopes)
    service = build('gmail', 'v1', credentials=creds, cache_discovery=False)
    verify_profile(service, account['email'])  # Unknown is a blocker, never permission.
    saved = json.loads(creds.to_json())
    # to_json omits granted_scopes; persist validated actual grants as scopes
    # so reload never promotes a partial grant to the requested scope list.
    saved['scopes'] = grants
    save(token, saved)
    return service


def header(message, key):
    values = [h['value'] for h in message.get('payload', {}).get('headers', [])
              if h['name'].lower() == key.lower()]
    if len(values) > 1:
        raise ValueError('Ambiguous duplicate email header')
    return values[0] if values else ''


def address(value):
    """This starter supports one explicit addr-spec, no groups or reply-all."""
    if '\r' in value or '\n' in value:
        raise ValueError('Header injection rejected')
    pairs = getaddresses([value])
    if len(pairs) != 1 or not re.fullmatch(r'[^\s<>@,;]+@[^\s<>@,;]+\.[^\s<>@,;]+', pairs[0][1]):
        raise ValueError('Exactly one valid mailbox address is required')
    return pairs[0][1]


def thread_state(thread, account):
    messages = sorted(thread.get('messages', []), key=lambda m: int(m['internalDate']))
    # Drafts are intentionally held, rather than guessed to be sent or ignored.
    if not messages:
        raise ValueError('Empty thread')
    if any('DRAFT' in m.get('labelIds', []) for m in messages):
        return messages, 'hold-existing-draft'
    if any(not content_ready(m.get('payload', {})) for m in messages):
        return messages, 'hold-missing-content'
    latest = messages[-1]
    sender = address(header(latest, 'From'))
    own = {account['email'].casefold(), *(x.casefold() for x in account.get('aliases', []))}
    if 'SENT' in latest.get('labelIds', []) or sender.casefold() in own:
        return messages, 'skip-already-replied'
    if 'TRASH' in latest.get('labelIds', []) or 'SPAM' in latest.get('labelIds', []):
        return messages, 'skip-no-reply-needed'
    return messages, 'owner-review'


def body_parts(payload):
    """Preserve supplied inline text/HTML as untrusted data, never render it."""
    result = []
    data = payload.get('body', {}).get('data')
    if data and payload.get('mimeType', '').startswith('text/'):
        raw = base64.urlsafe_b64decode(data + '=' * (-len(data) % 4))
        result.append({'mime_type': payload['mimeType'], 'text': raw.decode('utf-8', errors='replace')})
    for part in payload.get('parts', []):
        result.extend(body_parts(part))
    return result


def content_ready(payload):
    # No attachment downloads or HTML rendering in this starter. Missing inline
    # text and attachments with unfetched/unreviewed meaning require manual
    # review in Gmail; they cannot progress to the API send facade.
    def unfetched(part):
        return bool(part.get('filename') or part.get('body', {}).get('attachmentId')
                    or any(unfetched(child) for child in part.get('parts', [])))
    return not unfetched(payload) and any(part['text'].strip() for part in body_parts(payload))


def thread_view(thread, account):
    messages, decision = thread_state(thread, account)
    return {'thread_id': thread['id'], 'snapshot': digest(thread), 'decision': decision,
            'untrusted_messages': [{'id': m['id'], 'labels': m.get('labelIds', []),
                                    'headers': m.get('payload', {}).get('headers', []),
                                    'parts': body_parts(m.get('payload', {})),
                                    # Keep MIME/attachment metadata; no binary downloads.
                                    'payload': m.get('payload', {})} for m in messages]}


def scan(service, account, query, max_pages=10):
    results, seen, token = [], set(), None
    for _ in range(max_pages):
        kwargs = dict(userId='me', q=query, maxResults=100)
        if token:
            kwargs['pageToken'] = token
        page = service.users().threads().list(**kwargs).execute()
        for stub in page.get('threads', []):
            if stub['id'] not in seen:
                seen.add(stub['id'])
                thread = service.users().threads().get(userId='me', id=stub['id'], format='full').execute()
                results.append(thread_view(thread, account))
        token = page.get('nextPageToken')
        if not token:
            break
    return {'threads': results, 'complete': not bool(token), 'next_page_token': token}


def prepare(thread, account, to, body):
    messages, decision = thread_state(thread, account)
    if decision != 'owner-review':
        raise ValueError('Thread is not eligible for a new reply')
    latest = messages[-1]
    subject = header(latest, 'Subject')
    reply_id = header(latest, 'Message-ID')
    if not reply_id or not body.strip():
        raise ValueError('Message-ID and nonempty reply body required')
    for value in [subject, reply_id, header(latest, 'References')]:
        if '\r' in value or '\n' in value:
            raise ValueError('Unexpected newline in reply headers')
    # Human-selected destination, including Reply-To differences, is in approval.
    recipient = address(to)
    preview = {'version': 1, 'account': account['email'], 'to': recipient,
               'subject': subject, 'body': body, 'thread_id': thread['id'],
               'snapshot': digest(thread), 'in_reply_to': reply_id,
               'references': (header(latest, 'References') + ' ' + reply_id).strip(),
               'source_message_id': latest['id']}
    return preview


def send(service, account, root, preview, approved_hash, execute=False):
    if not execute or not account.get('allow_send', False):
        raise ValueError('Sending requires --execute and allow_send=true')
    if digest(preview) != approved_hash or preview['account'] != account['email']:
        raise ValueError('Approval does not match exact preview/account')
    verify_profile(service, account['email'])
    thread = service.users().threads().get(userId='me', id=preview['thread_id'], format='full').execute()
    fresh = prepare(thread, account, preview['to'], preview['body'])
    if fresh != preview:
        raise ValueError('Thread or preview changed; prepare and approve again')
    # A receipt is reserved BEFORE the request. An uncertain outcome is never
    # automatically retried, even after a new preview is produced for this source.
    key = digest([preview['account'], preview['thread_id'], preview['source_message_id']])
    receipt = root / ('send-' + key + '.json')
    if receipt.exists():
        raise ValueError('Send already attempted; reconcile in Gmail before any further action')
    msg = EmailMessage()
    msg['From'], msg['To'], msg['Subject'] = preview['account'], preview['to'], preview['subject']
    msg['In-Reply-To'], msg['References'] = preview['in_reply_to'], preview['references']
    msg.set_content(preview['body'])
    save(receipt, {'status': 'attempted-outcome-unknown', 'approval': approved_hash})
    result = service.users().messages().send(userId='me', body={
        'threadId': preview['thread_id'],
        'raw': base64.urlsafe_b64encode(msg.as_bytes()).decode()}).execute(num_retries=0)
    if not result.get('id'):
        raise ValueError('Provider returned no message ID; reconcile manually')
    save(receipt, {'status': 'sent', 'approval': approved_hash, 'message_id': result['id']})
    return result['id']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['sample', 'auth', 'scan', 'prepare', 'send'])
    parser.add_argument('--config', type=Path)
    parser.add_argument('--account')
    parser.add_argument('--sample', type=Path)
    parser.add_argument('--state-dir', type=Path)
    parser.add_argument('--thread-id')
    parser.add_argument('--to')
    parser.add_argument('--body-file', type=Path)
    parser.add_argument('--approved-sha256')
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    if args.command == 'sample':
        if not args.sample or not args.state_dir:
            parser.error('sample requires --sample and --state-dir')
        root = private_dir(args.state_dir)
        data = json.loads(args.sample.read_text())
        views = [thread_view(t, data['account']) for t in data['threads']]
        save(root / 'triage.json', {'threads': views, 'complete': True, 'synthetic': True})
        print(f'Synthetic scan: {len(views)} threads; no network or email writes')
        return
    if not args.config or not args.account:
        parser.error('live commands require --config and --account')
    account, root = load_config(args.config, args.account)
    with locked(root):
        service = connect(account, root, authorize=args.command == 'auth')
        if args.command == 'auth':
            print('Account and scopes verified; private token saved')
        elif args.command == 'scan':
            report = scan(service, account, account.get('query', 'in:inbox newer_than:14d'))
            save(root / 'triage.json', report)
            print(f"Scan: {len(report['threads'])} threads; complete={report['complete']}; no email writes")
        elif args.command == 'prepare':
            if not args.thread_id or not args.to or not args.body_file:
                parser.error('prepare requires --thread-id, --to and --body-file')
            thread = service.users().threads().get(userId='me', id=args.thread_id, format='full').execute()
            preview = prepare(thread, account, args.to, read_private_text(args.body_file))
            save(root / 'preview.json', preview)
            print('Local preview saved; review every field before approving SHA-256: ' + digest(preview))
        elif args.command == 'send':
            preview = read_private(root / 'preview.json')
            send(service, account, root, preview, args.approved_sha256, args.execute)
            print('Sent once; provider message ID saved in private receipt')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        # Provider errors may contain raw mail, tokens, or callback URLs. Keep
        # details out of scheduled logs; inspect the account interactively.
        print('Stopped safely (' + type(exc).__name__ + '). Check configuration, permissions, '
              'account/scopes, thread eligibility and approval; do not blindly retry a send.', file=sys.stderr)
        sys.exit(1)

"""
conversation/reply_composer.py
==============================
Builds WhatsApp message payloads — plain text, interactive buttons, interactive lists.
The caller passes structured data; this module formats it for the Cloud API.
"""
from django.conf import settings


def _checkout_url(public_token: str) -> str:
    base = settings.IMARA_PAY.get('BASE_URL', 'http://localhost:5173')
    return f"{base}/p/{public_token}"


def _step_up_url(raw_token: str) -> str:
    base = settings.IMARA_PAY.get('BASE_URL', 'http://localhost:5173')
    return f"{base}/view/step-up/{raw_token}"


def _report_url(raw_token: str) -> str:
    base = settings.IMARA_PAY.get('BASE_URL', 'http://localhost:5173')
    return f"{base}/view/report/{raw_token}"


# ─── Plain text ───────────────────────────────────────────────────────────────

def text_reply(body: str) -> dict:
    return {'type': 'text', 'text': {'body': body}}


# ─── Interactive buttons ──────────────────────────────────────────────────────

def confirm_create_request_prompt(amount: int, reference: str) -> dict:
    """
    Reply button prompt before creating a payment request (§8.2).
    Merchant must confirm or choose to edit.
    """
    return {
        'type': 'interactive',
        'interactive': {
            'type': 'button',
            'header': {'type': 'text', 'text': '🧾 Confirm Payment Request'},
            'body': {
                'text': (
                    f"Create a payment request for:\n"
                    f"💰 *KES {amount:,}*\n"
                    f"📌 Ref: `{reference}`\n\n"
                    f"Forward the link to your customer once created."
                )
            },
            'action': {
                'buttons': [
                    {'type': 'reply', 'reply': {'id': 'confirm', 'title': '✅ Confirm'}},
                    {'type': 'reply', 'reply': {'id': 'edit', 'title': '✏️ Edit'}},
                ]
            }
        }
    }


def payment_link_reply(payment_request) -> dict:
    """
    After a PaymentRequest is created, send the merchant the shareable link.
    """
    url = _checkout_url(payment_request.public_token)
    return {
        'type': 'interactive',
        'interactive': {
            'type': 'cta_url',
            'header': {'type': 'text', 'text': '✅ Payment Request Created'},
            'body': {
                'text': (
                    f"*KES {payment_request.amount_minor:,}* — Ref: `{payment_request.reference}`\n\n"
                    f"Share this link with your customer to collect payment via M-Pesa:"
                )
            },
            'action': {
                'name': 'cta_url',
                'parameters': {'display_text': '💳 Pay via M-Pesa', 'url': url}
            },
            'footer': {'text': 'Customer pays — you get notified instantly'}
        }
    }


def payment_link_reply_text(payment_request) -> dict:
    """Fallback text reply if CTA URL buttons aren't available."""
    url = _checkout_url(payment_request.public_token)
    return text_reply(
        f"✅ *Payment Request Created!*\n\n"
        f"💰 Amount: *KES {payment_request.amount_minor:,}*\n"
        f"📌 Reference: `{payment_request.reference}`\n"
        f"🔗 Checkout Link:\n{url}\n\n"
        f"Share this link with your customer to collect payment via M-Pesa."
    )


def step_up_prompt(challenge, raw_token: str) -> dict:
    """
    Step-up challenge magic link prompt (§7.4).
    Shows what action is pending and a link to confirm it.
    """
    action_descriptions = {
        'REMOVE_STAFF_NUMBER': f"Removing staff number {challenge.action_payload.get('phone_number', '')}",
        'CHANGE_SETTLEMENT_ACCOUNT': "Changing your settlement account",
        'REFUND': f"Refunding KES {challenge.action_payload.get('amount', 0):,}",
        'CANCEL_INFLIGHT': f"Cancelling in-flight payment {challenge.action_payload.get('reference', '')}",
        'VIEW_AUDIT_LOG': "Viewing full audit log",
    }
    action_desc = action_descriptions.get(challenge.action_type, challenge.action_type)
    url = _step_up_url(raw_token)

    return text_reply(
        f"🔐 *Security Confirmation Required*\n\n"
        f"Action requested: *{action_desc}*\n\n"
        f"To proceed, open this secure confirmation link (valid 5 minutes, single use):\n{url}\n\n"
        f"If you didn't request this, ignore this message — the link will expire automatically."
    )


def payment_confirmed_notification(payment_request, mpesa_receipt: str) -> dict:
    """WhatsApp message sent to the merchant when a payment succeeds."""
    return text_reply(
        f"✅ *Payment Received!*\n\n"
        f"💰 *KES {payment_request.amount_minor:,}* confirmed\n"
        f"📌 Ref: `{payment_request.reference}`\n"
        f"🧾 M-Pesa Receipt: `{mpesa_receipt}`\n"
        f"📞 From: {payment_request.customer_phone}\n\n"
        f"You can now hand over goods or services."
    )


def payment_failed_notification(payment_request, reason: str = '') -> dict:
    """WhatsApp message sent to the merchant when a payment fails."""
    return text_reply(
        f"❌ *Payment Failed*\n\n"
        f"KES {payment_request.amount_minor:,} — Ref: `{payment_request.reference}`\n"
        f"Reason: {reason or 'Customer cancelled or timed out'}\n\n"
        f"The checkout link is still active for the customer to retry."
    )


# ─── Interactive lists ────────────────────────────────────────────────────────

def help_menu() -> dict:
    """The help interactive list menu (§8.3)."""
    return {
        'type': 'interactive',
        'interactive': {
            'type': 'list',
            'header': {'type': 'text', 'text': '🤖 Imara Pay — Command Menu'},
            'body': {
                'text': (
                    "Here's what you can do. Reply with a command or choose from the list below:"
                )
            },
            'footer': {'text': 'Imara Pay · Kenya M-Pesa Collection'},
            'action': {
                'button': 'View Commands',
                'sections': [
                    {
                        'title': 'Payments',
                        'rows': [
                            {
                                'id': 'help_create',
                                'title': '💳 Create Request',
                                'description': 'request 2500 for INV-1002'
                            },
                            {
                                'id': 'help_today',
                                'title': '📊 Today\'s Totals',
                                'description': 'today'
                            },
                        ]
                    },
                    {
                        'title': 'Tracking',
                        'rows': [
                            {
                                'id': 'help_status',
                                'title': '🔍 Check Status',
                                'description': 'status INV-1002'
                            },
                            {
                                'id': 'help_last',
                                'title': '🕐 Recent Payments',
                                'description': 'last 5'
                            },
                            {
                                'id': 'help_cancel',
                                'title': '❌ Cancel Request',
                                'description': 'cancel INV-1002'
                            },
                        ]
                    },
                ]
            }
        }
    }


def unknown_command_reply(raw_text: str) -> dict:
    """Reply for unrecognized commands — always includes help hint (§8.4)."""
    return text_reply(
        f"🤔 I didn't understand: *{raw_text[:80]}*\n\n"
        f"Try one of these commands:\n"
        f"  • `request 2500 for INV-1002`\n"
        f"  • `today`\n"
        f"  • `status INV-1002`\n"
        f"  • `last 5`\n"
        f"  • `cancel INV-1002`\n"
        f"  • `help` — full menu\n\n"
        f"Send `help` anytime to see all options."
    )


def today_summary_reply(summary: dict) -> dict:
    """Today's totals reply (§8.1 'today' command)."""
    return text_reply(
        f"📊 *Today's Summary*\n\n"
        f"✅ Succeeded: *{summary['succeeded_count']}* requests "
        f"(KES {summary['succeeded_amount']:,})\n"
        f"⏳ Pending: *{summary['pending_count']}* requests "
        f"(KES {summary['pending_amount']:,})\n"
        f"❌ Failed/Expired: *{summary['failed_count']}* requests\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💰 *Total Collected Today: KES {summary['succeeded_amount']:,}*"
    )


def status_reply(pr) -> dict:
    """Status of a single payment request."""
    status_emoji = {
        'CREATED': '🔵', 'PENDING': '⏳', 'SUCCEEDED': '✅',
        'FAILED': '❌', 'EXPIRED': '⏰', 'CANCELLED': '🚫'
    }
    emoji = status_emoji.get(pr.status, '❓')
    lines = [
        f"{emoji} *Payment Request: {pr.reference}*\n",
        f"💰 Amount: KES {pr.amount_minor:,}",
        f"📋 Status: *{pr.status}*",
    ]
    if pr.description:
        lines.append(f"📝 Description: {pr.description}")
    if pr.status == 'SUCCEEDED' and pr.paid_at:
        lines.append(f"✅ Paid at: {pr.paid_at.strftime('%d %b %Y %H:%M')}")
    if pr.status in ('CREATED', 'PENDING'):
        from apps.conversation.reply_composer import _checkout_url
        lines.append(f"🔗 Link: {_checkout_url(pr.public_token)}")
    return text_reply('\n'.join(lines))


def recent_transactions_reply(transactions: list) -> dict:
    """Last N transactions reply."""
    if not transactions:
        return text_reply(
            "🕐 *Recent Transactions*\n\nNo transactions yet. "
            "Create a payment request with `request 2500 for INV-1002`."
        )
    lines = ["🕐 *Recent Transactions*\n"]
    for i, t in enumerate(transactions, 1):
        lines.append(
            f"{i}. ✅ KES {t['amount_minor']:,} — `{t['reference']}`\n"
            f"   🧾 {t['mpesa_receipt']} · {t['paid_at']}"
        )
    return text_reply('\n'.join(lines))


def cancel_success_reply(pr) -> dict:
    return text_reply(
        f"🚫 *Payment request cancelled.*\n\n"
        f"📌 Ref: `{pr.reference}` — KES {pr.amount_minor:,}\n\n"
        f"The checkout link is now inactive."
    )


def report_link_reply(raw_token: str, description: str = 'Your transactions') -> dict:
    url = _report_url(raw_token)
    return text_reply(
        f"📋 *Report Ready*\n\n"
        f"{description}\n\n"
        f"Open your report here (valid 24 hours):\n{url}"
    )


def onboarding_welcome() -> dict:
    return text_reply(
        "👋 *Welcome to Imara Pay!*\n\n"
        "Your WhatsApp number is now linked to your account. "
        "Here's how to get started:\n\n"
        "💳 Create a payment request:\n`request 2500 for INV-1002`\n\n"
        "📊 Check today's totals:\n`today`\n\n"
        "❓ See all commands:\n`help`\n\n"
        "Your customers pay via M-Pesa — you get notified right here! 🇰🇪"
    )


def unrecognized_sender_reply() -> dict:
    """For phone numbers with no PhoneIdentity — never leak account info."""
    return text_reply(
        "👋 Hi! This is *Imara Pay* — Kenya's WhatsApp-first M-Pesa collection platform.\n\n"
        "It looks like your number isn't linked to an Imara Pay account yet.\n\n"
        "To get started, sign up at:\nhttps://imarapay.co.ke/onboarding\n\n"
        "Once you've completed onboarding and linked this number, you can collect "
        "payments right here in WhatsApp."
    )

"""Translated browser messages for the local-only Push diagnostic."""

from django.utils.translation import pgettext


def browser_strings():
    return {
        'serverError': pgettext(
            "push diagnostic", 'The server could not complete this step.'
        ),
        'permissionDenied': pgettext(
            "push diagnostic",
            "Permission was not granted. You can change it in Chrome's site settings.",
        ),
        'enabled': pgettext(
            "push diagnostic",
            'Notifications allowed and subscription saved. You can schedule the test.',
        ),
        'scheduled': pgettext(
            "push diagnostic",
            'Scheduled in 10 seconds. Close this tab while keeping Chrome open. Click the notification to return here.',
        ),
        'stopped': pgettext(
            "push diagnostic",
            "Test stopped and subscription removed. Chrome's permission can be removed in its settings.",
        ),
        'creating': pgettext("push diagnostic", 'Creating a new alert…'),
        'localTitle': pgettext("push diagnostic", 'Match Europe — local display'),
        'localBody': pgettext(
            "push diagnostic",
            'This alert is created directly on your Mac, without remote delivery.',
        ),
        'displayCount': pgettext(
            "push diagnostic",
            'Chrome accepted the local display. Active notifications: {count}. If no alert is visible, check Chrome/macOS display settings.',
        ),
        'displayError': pgettext("push diagnostic", 'Display error: '),
        'displayed': pgettext(
            "push diagnostic",
            'Remote message received by Chrome and display accepted by the system.',
        ),
        'received': pgettext(
            "push diagnostic",
            'Remote message received by Chrome, attempting to display…',
        ),
        'browserError': pgettext("push diagnostic", 'Browser error: '),
        'unsupported': pgettext(
            "push diagnostic",
            'Web Push is unavailable here. Open this address in Chrome outside private browsing.',
        ),
        'lastSent': pgettext(
            "push diagnostic",
            'The notification service accepted the last delivery. Did you see the alert on your Mac?',
        ),
        'lastFailed': pgettext(
            "push diagnostic", 'The last delivery failed. You can try again.'
        ),
        'ready': pgettext("push diagnostic", 'Ready. Click Enable notifications.'),
    }

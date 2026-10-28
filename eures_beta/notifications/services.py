from eures_beta.notifications.models import Notification


def notify(user, label, url):
    Notification.objects.create(user=user, label=label, url=url)

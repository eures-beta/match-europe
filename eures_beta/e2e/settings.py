"""Test-only transport configuration loaded explicitly in the isolated container."""

from config.settings import *  # noqa: F403

# The real mail creation, links and confirmations run; only delivery is captured.
EMAIL_BACKEND = 'django.core.mail.backends.filebased.EmailBackend'
EMAIL_FILE_PATH = '/artifacts/mail'

# Never log confirmation links, query strings, cookies or uploaded content.
access_log_format = '%(m)s %(s)s %(L)s'

# Loaded by Gunicorn's default configuration discovery, including the CLI launch.
from eures_beta.observability.runtime import worker_abort

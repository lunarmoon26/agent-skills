# Webhook delivery fixture

The worker may retry a delivery after a timeout or process restart. A webhook
event ID must not be delivered again after the worker has recorded it as sent.

The current implementation stores delivery state in `webhook.ts`. This fixture
has no external queue or transaction support.

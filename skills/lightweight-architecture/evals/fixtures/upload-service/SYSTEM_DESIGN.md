# Upload service design

Status: Implemented unless a section says proposed.

The API process accepts uploads and sends work to one worker process. The worker
owns scanning and metadata writes. Deployment details and completion-event
failure behavior are not yet documented here.

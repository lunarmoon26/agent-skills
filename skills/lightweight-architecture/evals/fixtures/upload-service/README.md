# Upload service fixture

This service accepts file uploads, invokes an isolated scanner, stores metadata,
and emits `upload.completed` after a clean scan. Files are retained in object
storage; metadata is retained in PostgreSQL.

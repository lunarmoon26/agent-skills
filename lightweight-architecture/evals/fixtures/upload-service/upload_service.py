def process_upload(upload, scanner, metadata, events):
    scan_result = scanner.scan(upload.object_key)
    if not scan_result.clean:
        metadata.record_rejected(upload.id, scan_result.reason)
        return

    metadata.record_completed(upload.id, upload.object_key)
    events.publish("upload.completed", {"upload_id": upload.id})

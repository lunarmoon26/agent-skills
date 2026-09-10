from upload_service import process_upload


def test_clean_upload_records_metadata_and_emits_event(fakes):
    process_upload(fakes.upload, fakes.clean_scanner, fakes.metadata, fakes.events)

    assert fakes.metadata.completed == [fakes.upload.id]
    assert fakes.events.names == ["upload.completed"]


def test_rejected_upload_does_not_emit_event(fakes):
    process_upload(fakes.upload, fakes.infected_scanner, fakes.metadata, fakes.events)

    assert fakes.metadata.rejected == [fakes.upload.id]
    assert fakes.events.names == []

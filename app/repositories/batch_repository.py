from sqlalchemy.orm import Session

from app.db.models import UploadBatch, utc_now


class BatchRepository:
    """
    Repository for Excel upload batch persistence.
    """

    def __init__(self, session: Session) -> None:
        self.session = session

    def create_upload_batch(
        self,
        file_name: str,
        total_rows: int = 0,
        source: str = "excel",
    ) -> UploadBatch:
        """
        Create a new upload batch record.

        Returns:
            Persisted UploadBatch database model.
        """
        batch = UploadBatch(
            file_name=file_name,
            source=source,
            total_rows=total_rows,
            processed_rows=0,
            failed_rows=0,
            status="pending",
        )

        self.session.add(batch)
        self.session.commit()
        self.session.refresh(batch)

        return batch

    def update_progress(
        self,
        batch_id: str,
        processed_rows: int,
        failed_rows: int,
        status: str,
    ) -> UploadBatch:
        """
        Update upload batch progress counters.

        Returns:
            Updated UploadBatch database model.
        """
        batch = self.session.get(UploadBatch, batch_id)
        if batch is None:
            raise ValueError(f"Upload batch not found: {batch_id}")

        batch.processed_rows = processed_rows
        batch.failed_rows = failed_rows
        batch.status = status

        if status in {"processed", "failed"}:
            batch.finished_at = utc_now()

        self.session.commit()
        self.session.refresh(batch)

        return batch

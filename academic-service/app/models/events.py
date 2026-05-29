"""
Academic Service Event Outbox — Transactional Outbox Pattern.
Events are written atomically with triggering transactions.
A relay process reads and publishes to message broker (Kafka/RabbitMQ).
"""
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID

from .base import BaseModel


class AcademicEvent(BaseModel):
    """
    Event outbox for reliable async event publishing.

    Published Events:
    - STUDENT_ENROLLED          (when AcademicProfile created)
    - STUDENT_TRANSFERRED       (when enrollment_status=TRANSFERRED)
    - ATTENDANCE_MARKED         (daily batch)
    - ATTENDANCE_UPDATED        (when attendance corrected)
    - HOMEWORK_CREATED          (new homework assigned)
    - HOMEWORK_CLOSED           (due date passed / manually closed)
    - HOMEWORK_SUBMITTED        (student submission)
    - LEAVE_REQUESTED           (student submits leave)
    - LEAVE_APPROVED            (class teacher approves)
    - LEAVE_REJECTED            (class teacher rejects)
    - REVIEW_CREATED            (teacher creates review)
    - REVIEW_PUBLISHED          (review published to parent)
    - REVIEW_ACKNOWLEDGED       (parent acknowledges)
    - REMARK_CREATED            (new remark added)
    - BEHAVIOR_RECORDED         (behavioral incident logged)
    - DISCIPLINE_ISSUED         (disciplinary action issued)
    - ACHIEVEMENT_RECORDED      (achievement/award logged)
    - TIMETABLE_UPDATED         (timetable changed)
    """
    __tablename__ = "academic_events"
    __table_args__ = {"schema": "academic", "comment": "Event outbox for reliable async event publishing"}

    tenant_id = Column(UUID(as_uuid=True), nullable=True, index=True)

    # Event Identity
    event_type = Column(String(100), nullable=False, index=True, comment="STUDENT_ENROLLED | ATTENDANCE_MARKED | ...")
    event_version = Column(String(10), default="1.0")

    # Aggregate Reference
    aggregate_type = Column(
        String(100), nullable=False, index=True,
        comment="ACADEMIC_PROFILE | HOMEWORK | ATTENDANCE | REVIEW | BEHAVIOR | DISCIPLINE | ACHIEVEMENT | LEAVE",
    )
    aggregate_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Payload
    event_data = Column(JSONB, nullable=False, comment="Full event payload (immutable once written)")

    # Causation chain
    user_id = Column(UUID(as_uuid=True), nullable=True, comment="User who triggered the event")
    correlation_id = Column(UUID(as_uuid=True), nullable=True, index=True, comment="Request correlation ID")
    causation_id = Column(UUID(as_uuid=True), nullable=True, comment="ID of event that caused this event")

    # Publishing
    is_published = Column(Boolean, default=False, nullable=False, index=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    retry_count = Column(Integer, default=0)
    last_error = Column(Text, nullable=True)
    next_retry_at = Column(DateTime(timezone=True), nullable=True)

    # Topic routing
    kafka_topic = Column(String(200), nullable=True, comment="Target Kafka/AMQP topic")

    def __repr__(self):
        return f"<AcademicEvent(type={self.event_type}, aggregate={self.aggregate_type})>"

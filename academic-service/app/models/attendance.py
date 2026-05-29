"""
Attendance models: daily records, monthly summaries, leave requests, leave approvals.
"""
from sqlalchemy import Boolean, Column, Date, DateTime, Integer, String, Text, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from .base import BaseModel


# ---------------------------------------------------------------------------
# Attendance Record
# ---------------------------------------------------------------------------
class AttendanceRecord(BaseModel):
    """
    Daily attendance record per student.

    Rules:
    - One record per student per day
    - Only Class Teacher can mark attendance
    - Cannot mark future attendance
    - Editable within 7-day grace period (configurable)
    """
    __tablename__ = "attendance_records"
    __table_args__ = (
        UniqueConstraint("tenant_id", "student_id", "attendance_date", name="uq_academic_student_attendance_date"),
        {"schema": "academic", "comment": "Daily student attendance — partition by month in production"},
    )

    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    student_id = Column(UUID(as_uuid=True), ForeignKey("academic.academic_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    class_id = Column(UUID(as_uuid=True), ForeignKey("academic.classes.id", ondelete="CASCADE"), nullable=False, index=True)
    section_id = Column(UUID(as_uuid=True), ForeignKey("academic.sections.id", ondelete="CASCADE"), nullable=False, index=True)
    academic_year_id = Column(UUID(as_uuid=True), ForeignKey("academic.academic_years.id", ondelete="CASCADE"), nullable=False, index=True)

    # Date
    attendance_date = Column(Date, nullable=False, index=True)

    # Status
    status = Column(
        String(20), nullable=False,
        comment="PRESENT | ABSENT | LATE | HALF_DAY | EXCUSED | ON_LEAVE | HOLIDAY",
    )
    arrival_time = Column(DateTime(timezone=True), nullable=True, comment="Check-in time (for biometric/app)")

    # Remarks
    remarks = Column(Text, nullable=True)

    # Marked by (Class Teacher user_id)
    marked_by_user_id = Column(UUID(as_uuid=True), nullable=True, index=True, comment="Teacher who marked attendance")
    marked_at = Column(DateTime(timezone=True), nullable=True)

    # Editing
    last_edited_by = Column(UUID(as_uuid=True), nullable=True)
    edit_reason = Column(String(255), nullable=True)

    extra_metadata = Column(JSONB, default={})

    # Relationships
    student = relationship("AcademicProfile", back_populates="attendance_records")

    def __repr__(self):
        return f"<AttendanceRecord(student_id={self.student_id}, date={self.attendance_date}, status={self.status})>"


# ---------------------------------------------------------------------------
# Attendance Summary (Monthly Aggregate)
# ---------------------------------------------------------------------------
class AttendanceSummary(BaseModel):
    """
    Monthly attendance summary per student (pre-computed for performance).
    Recomputed via background job when attendance records change.
    """
    __tablename__ = "attendance_summary"
    __table_args__ = (
        UniqueConstraint("tenant_id", "student_id", "academic_year_id", "month", "year", name="uq_academic_attendance_summary"),
        {"schema": "academic", "comment": "Monthly attendance aggregates for fast reporting"},
    )

    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    student_id = Column(UUID(as_uuid=True), ForeignKey("academic.academic_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    academic_year_id = Column(UUID(as_uuid=True), ForeignKey("academic.academic_years.id", ondelete="CASCADE"), nullable=False, index=True)

    month = Column(Integer, nullable=False, comment="Month number (1–12)")
    year = Column(Integer, nullable=False, comment="Calendar year")

    # Counts
    total_working_days = Column(Integer, default=0)
    present_days = Column(Integer, default=0)
    absent_days = Column(Integer, default=0)
    late_days = Column(Integer, default=0)
    half_days = Column(Integer, default=0)
    excused_days = Column(Integer, default=0)
    on_leave_days = Column(Integer, default=0)
    holiday_days = Column(Integer, default=0)

    # Computed
    attendance_percentage = Column(Integer, default=0, comment="Percentage (0–100)")

    computed_at = Column(DateTime(timezone=True), nullable=True, comment="When this summary was last computed")

    extra_metadata = Column(JSONB, default={})

    def __repr__(self):
        return f"<AttendanceSummary(student_id={self.student_id}, month={self.month}/{self.year})>"


# ---------------------------------------------------------------------------
# Leave Request
# ---------------------------------------------------------------------------
class LeaveRequest(BaseModel):
    """
    Student leave requests.

    Workflow:
    1. Student/Parent submits request
    2. Class Teacher reviews and approves/rejects
    3. Medical leave > 3 days requires certificate upload
    """
    __tablename__ = "leave_requests"
    __table_args__ = {"schema": "academic", "comment": "Student leave request workflow"}

    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    student_id = Column(UUID(as_uuid=True), ForeignKey("academic.academic_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    academic_year_id = Column(UUID(as_uuid=True), ForeignKey("academic.academic_years.id", ondelete="CASCADE"), nullable=False, index=True)

    # Leave Period
    leave_from_date = Column(Date, nullable=False, index=True)
    leave_to_date = Column(Date, nullable=False)
    total_days = Column(Integer, nullable=False)

    # Leave Type
    leave_type = Column(String(50), nullable=False, comment="MEDICAL | FAMILY | FESTIVAL | OTHER")
    reason = Column(Text, nullable=False)

    # Submitted by
    submitted_by_user_id = Column(UUID(as_uuid=True), nullable=False, comment="STUDENT or PARENT user_id")
    submitted_by_role = Column(String(20), nullable=False, comment="STUDENT | PARENT")

    # Medical Certificate
    requires_medical_certificate = Column(Boolean, default=False)
    medical_certificate_url = Column(Text, nullable=True)
    medical_certificate_submitted = Column(Boolean, default=False)

    # Status
    status = Column(String(20), default="PENDING", comment="PENDING | APPROVED | REJECTED | CANCELLED")

    # Approval
    approved_by_user_id = Column(UUID(as_uuid=True), nullable=True, comment="Class Teacher who approved")
    approved_at = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(Text, nullable=True)

    extra_metadata = Column(JSONB, default={})

    # Relationships
    student = relationship("AcademicProfile", back_populates="leave_requests")
    approvals = relationship("LeaveApproval", back_populates="leave_request")

    def __repr__(self):
        return f"<LeaveRequest(student_id={self.student_id}, from={self.leave_from_date}, status={self.status})>"


# ---------------------------------------------------------------------------
# Leave Approval (multi-step approval tracking)
# ---------------------------------------------------------------------------
class LeaveApproval(BaseModel):
    """
    Individual approval step in the leave request workflow.
    Supports multi-level approval (Parent → Class Teacher → HOD for extended leaves).
    """
    __tablename__ = "leave_approvals"
    __table_args__ = {"schema": "academic", "comment": "Leave request approval chain"}

    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    leave_request_id = Column(UUID(as_uuid=True), ForeignKey("academic.leave_requests.id", ondelete="CASCADE"), nullable=False, index=True)

    # Approver
    approver_user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    approver_role = Column(String(50), nullable=False, comment="CLASS_TEACHER | HOD | PRINCIPAL | PARENT")

    # Decision
    action = Column(String(20), nullable=False, comment="APPROVED | REJECTED | ACKNOWLEDGED")
    comments = Column(Text, nullable=True)
    actioned_at = Column(DateTime(timezone=True), nullable=True)

    step_order = Column(Integer, default=1, comment="Approval step sequence")

    extra_metadata = Column(JSONB, default={})

    # Relationships
    leave_request = relationship("LeaveRequest", back_populates="approvals")

    def __repr__(self):
        return f"<LeaveApproval(leave_id={self.leave_request_id}, role={self.approver_role}, action={self.action})>"

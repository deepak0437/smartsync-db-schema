"""
Student profile, teacher profile, parent-student mapping models.
"""
from sqlalchemy import Boolean, Column, Date, Integer, String, Text, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from .base import BaseModel


# ---------------------------------------------------------------------------
# Academic Profile (Student)
# ---------------------------------------------------------------------------
class AcademicProfile(BaseModel):
    """
    Student academic profile and enrollment record.

    Links auth-service user_id to academic data.
    One enrollment per academic year per student.
    """
    __tablename__ = "academic_profiles"
    __table_args__ = (
        UniqueConstraint("tenant_id", "admission_number", name="uq_academic_tenant_admission_number"),
        UniqueConstraint("tenant_id", "user_id", "academic_year_id", name="uq_academic_tenant_user_year"),
        {"schema": "academic", "comment": "Student enrollment and academic profile"},
    )

    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Reference to Auth Service (no FK — cross-service)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True, comment="Student user_id from auth-service")

    # Academic Structure FKs
    academic_year_id = Column(UUID(as_uuid=True), ForeignKey("academic.academic_years.id", ondelete="CASCADE"), nullable=False, index=True)
    class_id = Column(UUID(as_uuid=True), ForeignKey("academic.classes.id", ondelete="SET NULL"), nullable=True, index=True)
    section_id = Column(UUID(as_uuid=True), ForeignKey("academic.sections.id", ondelete="SET NULL"), nullable=True, index=True)
    class_section_id = Column(UUID(as_uuid=True), ForeignKey("academic.class_sections.id", ondelete="SET NULL"), nullable=True, index=True)

    # Student Identity
    admission_number = Column(String(50), nullable=False, index=True, comment="Unique admission number per tenant")
    roll_number = Column(String(50), nullable=True, comment="Roll number within section")

    # Admission Details
    admission_date = Column(Date, nullable=False)
    admission_class = Column(String(50), nullable=True, comment="Class at time of admission")

    # Previous School
    previous_school_name = Column(String(255), nullable=True)
    previous_school_board = Column(String(100), nullable=True, comment="e.g. CBSE | ICSE | State Board")

    # Guardian Information
    father_name = Column(String(255), nullable=True)
    mother_name = Column(String(255), nullable=True)
    guardian_name = Column(String(255), nullable=True)
    guardian_relation = Column(String(50), nullable=True, comment="FATHER | MOTHER | GRANDPARENT | OTHER")

    # Emergency Contact
    emergency_contact_name = Column(String(255), nullable=True)
    emergency_contact_phone = Column(String(20), nullable=True)
    emergency_contact_relation = Column(String(50), nullable=True)

    # Medical Information
    blood_group = Column(String(10), nullable=True)
    medical_conditions = Column(Text, nullable=True)
    allergies = Column(Text, nullable=True)

    # Address
    address_line1 = Column(String(255), nullable=True)
    address_line2 = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    postal_code = Column(String(20), nullable=True)

    # Enrollment Status
    enrollment_status = Column(
        String(50), default="ACTIVE",
        comment="ACTIVE | INACTIVE | TRANSFERRED | GRADUATED | DROPPED | ON_LEAVE",
    )
    is_active = Column(Boolean, default=True, nullable=False)
    extra_metadata = Column(JSONB, default={})

    # Relationships
    academic_year = relationship("AcademicYear", back_populates="academic_profiles")
    section = relationship("Section", back_populates="academic_profiles")
    class_section = relationship("ClassSection", back_populates="academic_profiles")
    parent_mappings = relationship("StudentParentMapping", back_populates="student")
    attendance_records = relationship("AttendanceRecord", back_populates="student")
    leave_requests = relationship("LeaveRequest", back_populates="student")
    homework_submissions = relationship("HomeworkSubmission", back_populates="student")
    student_reviews = relationship("StudentReview", back_populates="student")
    student_remarks = relationship("StudentRemark", back_populates="student")
    behavior_records = relationship("BehaviorRecord", back_populates="student")
    discipline_records = relationship("DisciplineRecord", back_populates="student")
    achievements = relationship("Achievement", back_populates="student")
    student_tasks = relationship("StudentTask", back_populates="student")

    def __repr__(self):
        return f"<AcademicProfile(admission_number={self.admission_number})>"


# ---------------------------------------------------------------------------
# Student-Parent Mapping
# ---------------------------------------------------------------------------
class StudentParentMapping(BaseModel):
    """
    Parent-child relationship mapping.

    A parent can be linked to multiple children.
    A student can have multiple parents/guardians.
    This table is the OWNERSHIP source for parent data access.
    """
    __tablename__ = "student_parent_mapping"
    __table_args__ = (
        UniqueConstraint("tenant_id", "student_id", "parent_user_id", name="uq_academic_student_parent"),
        {"schema": "academic", "comment": "Parent-student ownership mapping for data access control"},
    )

    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    student_id = Column(UUID(as_uuid=True), ForeignKey("academic.academic_profiles.id", ondelete="CASCADE"), nullable=False, index=True)

    # Parent (auth service user_id — no FK cross-service)
    parent_user_id = Column(UUID(as_uuid=True), nullable=False, index=True, comment="Parent user_id from auth-service")

    # Relationship
    relationship_type = Column(String(50), nullable=False, comment="FATHER | MOTHER | GUARDIAN | SIBLING | OTHER")

    # Contact priority
    is_primary_contact = Column(Boolean, default=False, nullable=False, comment="Primary contact for school communication")
    is_emergency_contact = Column(Boolean, default=False, nullable=False)
    can_pickup = Column(Boolean, default=True, nullable=False, comment="Authorized to pick up student")

    is_active = Column(Boolean, default=True, nullable=False)
    extra_metadata = Column(JSONB, default={})

    # Relationships
    student = relationship("AcademicProfile", back_populates="parent_mappings")

    def __repr__(self):
        return f"<StudentParentMapping(student_id={self.student_id}, parent_id={self.parent_user_id})>"


# ---------------------------------------------------------------------------
# Employee Profile
# ---------------------------------------------------------------------------
class EmployeeProfile(BaseModel):
    """
    Employee profile (teaching and non-teaching staff).
    Links auth-service user_id to employee HR data.
    """
    __tablename__ = "employee_profiles"
    __table_args__ = (
        UniqueConstraint("tenant_id", "employee_id", name="uq_academic_tenant_employee_id"),
        UniqueConstraint("tenant_id", "user_id", name="uq_academic_tenant_employee_user"),
        {"schema": "academic", "comment": "Employee academic profile (cross-reference with HR service)"},
    )

    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Auth service reference (no FK — cross-service)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True, comment="Employee user_id from auth-service")

    # Employee Identity
    employee_id = Column(String(50), nullable=False, index=True, comment="Employee ID (same as auth username for teachers)")
    employee_type = Column(String(50), nullable=False, comment="TEACHING | NON_TEACHING | ADMINISTRATIVE | CONTRACT")

    # Joining
    joining_date = Column(Date, nullable=False)
    confirmation_date = Column(Date, nullable=True)

    # Role / Designation
    designation = Column(String(100), nullable=True, comment="e.g. Senior Teacher | HOD | Vice Principal")
    department_id = Column(UUID(as_uuid=True), ForeignKey("academic.departments.id", ondelete="SET NULL"), nullable=True, index=True)

    # Qualifications
    highest_qualification = Column(String(100), nullable=True)
    specialization = Column(String(255), nullable=True)
    experience_years = Column(Integer, default=0)

    # Employment
    employment_status = Column(String(50), default="ACTIVE", comment="ACTIVE | ON_LEAVE | RESIGNED | TERMINATED | SUSPENDED")
    employment_type = Column(String(50), default="FULL_TIME", comment="FULL_TIME | PART_TIME | CONTRACT | VISITING")

    is_active = Column(Boolean, default=True, nullable=False)
    extra_metadata = Column(JSONB, default={})

    # Relationships
    teacher_profile = relationship("TeacherProfile", back_populates="employee", uselist=False)

    def __repr__(self):
        return f"<EmployeeProfile(employee_id={self.employee_id})>"


# ---------------------------------------------------------------------------
# Teacher Profile
# ---------------------------------------------------------------------------
class TeacherProfile(BaseModel):
    """
    Teacher-specific profile data.
    Extends EmployeeProfile for teachers.
    """
    __tablename__ = "teacher_profiles"
    __table_args__ = (
        UniqueConstraint("tenant_id", "employee_id", name="uq_academic_teacher_employee"),
        {"schema": "academic", "comment": "Teacher-specific attributes extending employee profile"},
    )

    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    employee_id = Column(UUID(as_uuid=True), ForeignKey("academic.employee_profiles.id", ondelete="CASCADE"), nullable=False, index=True)

    teacher_type = Column(String(50), default="REGULAR", comment="REGULAR | SUBSTITUTE | GUEST | VISITING")
    teaching_specialization = Column(String(255), nullable=True)
    teaching_experience_years = Column(Integer, default=0)

    # Max workload
    max_periods_per_week = Column(Integer, default=30, comment="Maximum periods per week for this teacher")

    is_active = Column(Boolean, default=True, nullable=False)
    extra_metadata = Column(JSONB, default={})

    # Relationships
    employee = relationship("EmployeeProfile", back_populates="teacher_profile")
    class_mappings = relationship("TeacherClassMapping", back_populates="teacher")
    subject_mappings = relationship("TeacherSubjectMapping", back_populates="teacher")
    section_mappings = relationship("TeacherSectionMapping", back_populates="teacher")

    def __repr__(self):
        return f"<TeacherProfile(employee_id={self.employee_id})>"


# ---------------------------------------------------------------------------
# Substitute Teacher Assignment
# ---------------------------------------------------------------------------
class SubstituteTeacherAssignment(BaseModel):
    """
    Substitute teacher assignments when a regular teacher is absent.
    Created by HOD or Principal.
    """
    __tablename__ = "substitute_teacher_assignments"
    __table_args__ = {"schema": "academic", "comment": "Substitute teacher assignments for absent teachers"}

    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Original teacher
    original_teacher_user_id = Column(UUID(as_uuid=True), nullable=False, index=True, comment="Original teacher being substituted")

    # Substitute teacher
    substitute_teacher_user_id = Column(UUID(as_uuid=True), nullable=False, index=True, comment="Substitute teacher user_id")

    # What is being substituted
    class_id = Column(UUID(as_uuid=True), ForeignKey("academic.classes.id", ondelete="CASCADE"), nullable=True)
    section_id = Column(UUID(as_uuid=True), ForeignKey("academic.sections.id", ondelete="CASCADE"), nullable=True)
    subject_id = Column(UUID(as_uuid=True), ForeignKey("academic.subjects.id", ondelete="SET NULL"), nullable=True)
    timetable_entry_id = Column(UUID(as_uuid=True), ForeignKey("academic.timetable_entries.id", ondelete="SET NULL"), nullable=True)

    # When
    assignment_date = Column(Date, nullable=False, index=True)
    reason = Column(Text, nullable=True)

    # Assigned by
    assigned_by_user_id = Column(UUID(as_uuid=True), nullable=True, comment="HOD or Principal who created this assignment")

    status = Column(String(20), default="ACTIVE", comment="ACTIVE | COMPLETED | CANCELLED")
    is_active = Column(Boolean, default=True, nullable=False)
    extra_metadata = Column(JSONB, default={})

    def __repr__(self):
        return f"<SubstituteTeacherAssignment(date={self.assignment_date})>"

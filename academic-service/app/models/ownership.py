"""
Ownership mapping tables: Teacher-Class, Teacher-Subject, Teacher-Section, HOD-Department.
These tables are the source of truth for data access authorization.
"""
from sqlalchemy import Boolean, Column, Date, String, Text, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from .base import BaseModel


# ---------------------------------------------------------------------------
# Teacher → Class Mapping (Class Teacher ownership)
# ---------------------------------------------------------------------------
class TeacherClassMapping(BaseModel):
    """
    Maps a Class Teacher to a class for a given academic year.

    Authorization use case:
    - Class Teacher can access ALL students in their assigned class
    - Class Teacher can mark attendance, create reviews, approve leave
    - Only ONE class teacher per class per academic year (typically)
    """
    __tablename__ = "teacher_class_mapping"
    __table_args__ = (
        UniqueConstraint("tenant_id", "teacher_id", "class_id", "academic_year_id", name="uq_academic_teacher_class_year"),
        {"schema": "academic", "comment": "Class Teacher → Class ownership mapping"},
    )

    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    teacher_id = Column(UUID(as_uuid=True), ForeignKey("academic.teacher_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    class_id = Column(UUID(as_uuid=True), ForeignKey("academic.classes.id", ondelete="CASCADE"), nullable=False, index=True)
    section_id = Column(UUID(as_uuid=True), ForeignKey("academic.sections.id", ondelete="SET NULL"), nullable=True, index=True, comment="Null = all sections in class")
    academic_year_id = Column(UUID(as_uuid=True), ForeignKey("academic.academic_years.id", ondelete="CASCADE"), nullable=False, index=True)

    mapping_type = Column(String(30), default="CLASS_TEACHER", comment="CLASS_TEACHER | ASSISTANT_CLASS_TEACHER")

    valid_from = Column(Date, nullable=True)
    valid_until = Column(Date, nullable=True)

    is_active = Column(Boolean, default=True, nullable=False)
    extra_metadata = Column(JSONB, default={})

    # Relationships
    teacher = relationship("TeacherProfile", back_populates="class_mappings")

    def __repr__(self):
        return f"<TeacherClassMapping(teacher_id={self.teacher_id}, class_id={self.class_id})>"


# ---------------------------------------------------------------------------
# Teacher → Subject Mapping (Subject Teacher ownership)
# ---------------------------------------------------------------------------
class TeacherSubjectMapping(BaseModel):
    """
    Maps a Subject Teacher to a subject+class+section combination.

    Authorization use case:
    - Subject Teacher can ONLY access students in classes/sections they teach
    - Subject Teacher can create subject-specific homework and remarks
    - Subject Teacher can ONLY review students they teach
    """
    __tablename__ = "teacher_subject_mapping"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "teacher_id", "subject_id", "class_id", "section_id", "academic_year_id",
            name="uq_academic_teacher_subject_class_section_year",
        ),
        {"schema": "academic", "comment": "Subject Teacher → Subject/Class/Section ownership mapping"},
    )

    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    teacher_id = Column(UUID(as_uuid=True), ForeignKey("academic.teacher_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    subject_id = Column(UUID(as_uuid=True), ForeignKey("academic.subjects.id", ondelete="CASCADE"), nullable=False, index=True)
    class_id = Column(UUID(as_uuid=True), ForeignKey("academic.classes.id", ondelete="CASCADE"), nullable=False, index=True)
    section_id = Column(UUID(as_uuid=True), ForeignKey("academic.sections.id", ondelete="SET NULL"), nullable=True, index=True, comment="Null = all sections in class")
    academic_year_id = Column(UUID(as_uuid=True), ForeignKey("academic.academic_years.id", ondelete="CASCADE"), nullable=False, index=True)

    valid_from = Column(Date, nullable=True)
    valid_until = Column(Date, nullable=True)

    is_active = Column(Boolean, default=True, nullable=False)
    extra_metadata = Column(JSONB, default={})

    # Relationships
    teacher = relationship("TeacherProfile", back_populates="subject_mappings")
    subject = relationship("Subject", back_populates="teacher_subject_mappings")

    def __repr__(self):
        return f"<TeacherSubjectMapping(teacher_id={self.teacher_id}, subject_id={self.subject_id})>"


# ---------------------------------------------------------------------------
# Teacher → Section Mapping (General section ownership)
# ---------------------------------------------------------------------------
class TeacherSectionMapping(BaseModel):
    """
    General teacher-section mapping for teachers who have broad section access
    (not necessarily subject-specific or class-teacher role).

    Authorization use case:
    - Supports multiple roles: a teacher can be both class teacher and subject teacher
    - Also used for activity/co-curricular teachers who cover whole sections
    """
    __tablename__ = "teacher_section_mapping"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "teacher_id", "section_id", "academic_year_id",
            name="uq_academic_teacher_section_year",
        ),
        {"schema": "academic", "comment": "Teacher → Section general ownership mapping"},
    )

    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    teacher_id = Column(UUID(as_uuid=True), ForeignKey("academic.teacher_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    section_id = Column(UUID(as_uuid=True), ForeignKey("academic.sections.id", ondelete="CASCADE"), nullable=False, index=True)
    academic_year_id = Column(UUID(as_uuid=True), ForeignKey("academic.academic_years.id", ondelete="CASCADE"), nullable=False, index=True)

    access_type = Column(String(50), default="FULL", comment="FULL | READ_ONLY | ATTENDANCE_ONLY")

    valid_from = Column(Date, nullable=True)
    valid_until = Column(Date, nullable=True)

    is_active = Column(Boolean, default=True, nullable=False)
    extra_metadata = Column(JSONB, default={})

    # Relationships
    teacher = relationship("TeacherProfile", back_populates="section_mappings")

    def __repr__(self):
        return f"<TeacherSectionMapping(teacher_id={self.teacher_id}, section_id={self.section_id})>"


# ---------------------------------------------------------------------------
# HOD → Department Mapping
# ---------------------------------------------------------------------------
class HODDepartmentMapping(BaseModel):
    """
    Maps a HOD (Head of Department) to a department.

    Authorization use case:
    - HOD can access all students in classes that have subjects in their department
    - HOD can create remarks on any student in their department
    - HOD can create remarks on teachers in their department
    - HOD approves disciplinary actions
    - HOD monitors attendance
    """
    __tablename__ = "hod_department_mapping"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "hod_user_id", "department_id", "academic_year_id",
            name="uq_academic_hod_department_year",
        ),
        {"schema": "academic", "comment": "HOD → Department ownership mapping"},
    )

    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # HOD user (auth service user_id — no FK cross-service)
    hod_user_id = Column(UUID(as_uuid=True), nullable=False, index=True, comment="HOD user_id from auth-service")

    department_id = Column(UUID(as_uuid=True), ForeignKey("academic.departments.id", ondelete="CASCADE"), nullable=False, index=True)
    academic_year_id = Column(UUID(as_uuid=True), ForeignKey("academic.academic_years.id", ondelete="CASCADE"), nullable=False, index=True)

    valid_from = Column(Date, nullable=True)
    valid_until = Column(Date, nullable=True)

    is_active = Column(Boolean, default=True, nullable=False)
    extra_metadata = Column(JSONB, default={})

    # Relationships
    department = relationship("Department", back_populates="hod_mappings")

    def __repr__(self):
        return f"<HODDepartmentMapping(hod_user_id={self.hod_user_id}, department_id={self.department_id})>"

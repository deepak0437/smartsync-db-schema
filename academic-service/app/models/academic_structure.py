"""
Academic structure models: Academic Year, Department, Class, Section,
Subject, ClassSection, ClassSubject, Timetable.
"""
from sqlalchemy import Boolean, Column, Date, Integer, String, Text, Time, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from .base import BaseModel


# ---------------------------------------------------------------------------
# Academic Year
# ---------------------------------------------------------------------------
class AcademicYear(BaseModel):
    """
    Academic year definition (e.g., 2024-2025).
    All academic entities are scoped to an academic year.
    """
    __tablename__ = "academic_years"
    __table_args__ = (
        UniqueConstraint("tenant_id", "year_code", name="uq_academic_tenant_year_code"),
        {"schema": "academic", "comment": "Academic year periods per tenant"},
    )

    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True, comment="Owning tenant")

    year_code = Column(String(20), nullable=False, index=True, comment="e.g. 2024-2025")
    year_name = Column(String(100), nullable=False, comment="e.g. Academic Year 2024-25")
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)

    is_current = Column(Boolean, default=False, nullable=False, comment="Only one year can be current per tenant")
    is_active = Column(Boolean, default=True, nullable=False)
    extra_metadata = Column(JSONB, default={})

    # Relationships
    classes = relationship("Class", back_populates="academic_year")
    academic_profiles = relationship("AcademicProfile", back_populates="academic_year")

    def __repr__(self):
        return f"<AcademicYear(code={self.year_code})>"


# ---------------------------------------------------------------------------
# Department
# ---------------------------------------------------------------------------
class Department(BaseModel):
    """
    Academic departments (e.g., Science, Mathematics, Languages, Arts).
    Departments are used for HOD ownership and subject grouping.
    """
    __tablename__ = "departments"
    __table_args__ = (
        UniqueConstraint("tenant_id", "department_code", name="uq_academic_tenant_dept_code"),
        {"schema": "academic", "comment": "Academic departments for subject and HOD grouping"},
    )

    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    department_code = Column(String(50), nullable=False, index=True, comment="e.g. SCI | MATH | ENG")
    department_name = Column(String(255), nullable=False)
    department_description = Column(Text, nullable=True)
    color_code = Column(String(10), nullable=True, comment="Hex color for UI display")

    # Current HOD (reference to Auth service user_id)
    hod_user_id = Column(UUID(as_uuid=True), nullable=True, comment="Current HOD user_id from auth-service")

    is_active = Column(Boolean, default=True, nullable=False)
    extra_metadata = Column(JSONB, default={})

    # Relationships
    subjects = relationship("Subject", back_populates="department")
    hod_mappings = relationship("HODDepartmentMapping", back_populates="department")

    def __repr__(self):
        return f"<Department(code={self.department_code}, name={self.department_name})>"


# ---------------------------------------------------------------------------
# Class
# ---------------------------------------------------------------------------
class Class(BaseModel):
    """
    Class/Grade level (e.g., Grade 1, Grade 2, Class 10, Class 12).
    Scoped to academic year.
    """
    __tablename__ = "classes"
    __table_args__ = (
        UniqueConstraint("tenant_id", "academic_year_id", "class_code", name="uq_academic_tenant_year_class"),
        {"schema": "academic", "comment": "Grade/class definitions per academic year"},
    )

    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    academic_year_id = Column(UUID(as_uuid=True), ForeignKey("academic.academic_years.id", ondelete="CASCADE"), nullable=False, index=True)

    class_code = Column(String(50), nullable=False, index=True, comment="e.g. CLASS_1 | GRADE_10 | CLASS_12_SCI")
    class_name = Column(String(100), nullable=False, comment="e.g. Grade 1 | Class 10 | Class XII Science")
    class_order = Column(Integer, nullable=False, comment="Numeric sort order (1, 2, 3...)")
    description = Column(Text, nullable=True)

    is_active = Column(Boolean, default=True, nullable=False)
    extra_metadata = Column(JSONB, default={})

    # Relationships
    academic_year = relationship("AcademicYear", back_populates="classes")
    sections = relationship("Section", back_populates="class_")
    class_sections = relationship("ClassSection", back_populates="class_")
    class_subjects = relationship("ClassSubject", back_populates="class_")
    timetables = relationship("Timetable", back_populates="class_")

    def __repr__(self):
        return f"<Class(code={self.class_code}, name={self.class_name})>"


# ---------------------------------------------------------------------------
# Section
# ---------------------------------------------------------------------------
class Section(BaseModel):
    """
    Section within a class (e.g., Section A, Section B, Section C).
    Each section has one assigned Class Teacher.
    """
    __tablename__ = "sections"
    __table_args__ = (
        UniqueConstraint("tenant_id", "class_id", "section_code", name="uq_academic_tenant_class_section"),
        {"schema": "academic", "comment": "Section divisions within a class"},
    )

    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    class_id = Column(UUID(as_uuid=True), ForeignKey("academic.classes.id", ondelete="CASCADE"), nullable=False, index=True)

    section_code = Column(String(10), nullable=False, index=True, comment="e.g. A | B | C")
    section_name = Column(String(100), nullable=False, comment="e.g. Section A")

    # Capacity
    max_students = Column(Integer, default=40, comment="Maximum student capacity")
    current_students = Column(Integer, default=0, comment="Denormalized count — update via trigger/event")

    # Class Teacher (auth service user_id)
    class_teacher_user_id = Column(UUID(as_uuid=True), nullable=True, comment="Assigned class teacher (auth service user_id)")

    # Room
    room_number = Column(String(20), nullable=True, comment="Physical classroom number")

    is_active = Column(Boolean, default=True, nullable=False)
    extra_metadata = Column(JSONB, default={})

    # Relationships
    class_ = relationship("Class", back_populates="sections")
    class_sections = relationship("ClassSection", back_populates="section")
    academic_profiles = relationship("AcademicProfile", back_populates="section")
    timetable_entries = relationship("TimetableEntry", back_populates="section")

    def __repr__(self):
        return f"<Section(code={self.section_code}, name={self.section_name})>"


# ---------------------------------------------------------------------------
# Subject
# ---------------------------------------------------------------------------
class Subject(BaseModel):
    """
    Subject/Course (e.g., Mathematics, Physics, English, History).
    Subjects belong to a Department and can be taught across multiple classes.
    """
    __tablename__ = "subjects"
    __table_args__ = (
        UniqueConstraint("tenant_id", "subject_code", name="uq_academic_tenant_subject_code"),
        {"schema": "academic", "comment": "Subject/course definitions"},
    )

    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    department_id = Column(UUID(as_uuid=True), ForeignKey("academic.departments.id", ondelete="SET NULL"), nullable=True, index=True)

    subject_code = Column(String(50), nullable=False, index=True, comment="e.g. MATH_10 | PHY_12 | ENG_8")
    subject_name = Column(String(255), nullable=False)
    subject_description = Column(Text, nullable=True)
    subject_type = Column(String(50), default="CORE", comment="CORE | ELECTIVE | OPTIONAL | CO_CURRICULAR | LAB")

    credits = Column(Integer, default=0, comment="Academic credits")
    weekly_periods = Column(Integer, default=5, comment="Default periods per week")
    color_code = Column(String(10), nullable=True, comment="Color for timetable display")

    is_active = Column(Boolean, default=True, nullable=False)
    extra_metadata = Column(JSONB, default={})

    # Relationships
    department = relationship("Department", back_populates="subjects")
    class_subjects = relationship("ClassSubject", back_populates="subject")
    teacher_subject_mappings = relationship("TeacherSubjectMapping", back_populates="subject")

    def __repr__(self):
        return f"<Subject(code={self.subject_code}, name={self.subject_name})>"


# ---------------------------------------------------------------------------
# ClassSection (composite)
# ---------------------------------------------------------------------------
class ClassSection(BaseModel):
    """
    Class-Section combination entity.
    Used as a single FK reference for enrollment and ownership.
    """
    __tablename__ = "class_sections"
    __table_args__ = (
        UniqueConstraint("tenant_id", "class_id", "section_id", name="uq_academic_class_section_combo"),
        {"schema": "academic", "comment": "Class+Section composite reference entity"},
    )

    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    class_id = Column(UUID(as_uuid=True), ForeignKey("academic.classes.id", ondelete="CASCADE"), nullable=False, index=True)
    section_id = Column(UUID(as_uuid=True), ForeignKey("academic.sections.id", ondelete="CASCADE"), nullable=False, index=True)

    is_active = Column(Boolean, default=True, nullable=False)
    extra_metadata = Column(JSONB, default={})

    # Relationships
    class_ = relationship("Class", back_populates="class_sections")
    section = relationship("Section", back_populates="class_sections")
    academic_profiles = relationship("AcademicProfile", back_populates="class_section")

    def __repr__(self):
        return f"<ClassSection(class_id={self.class_id}, section_id={self.section_id})>"


# ---------------------------------------------------------------------------
# ClassSubject
# ---------------------------------------------------------------------------
class ClassSubject(BaseModel):
    """
    Subjects assigned to a specific class.
    Controls which subjects are taught in which grade.
    """
    __tablename__ = "class_subjects"
    __table_args__ = (
        UniqueConstraint("tenant_id", "class_id", "subject_id", name="uq_academic_class_subject"),
        {"schema": "academic", "comment": "Subject-Class assignment"},
    )

    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    class_id = Column(UUID(as_uuid=True), ForeignKey("academic.classes.id", ondelete="CASCADE"), nullable=False, index=True)
    subject_id = Column(UUID(as_uuid=True), ForeignKey("academic.subjects.id", ondelete="CASCADE"), nullable=False, index=True)

    is_mandatory = Column(Boolean, default=True, nullable=False)
    display_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True, nullable=False)
    extra_metadata = Column(JSONB, default={})

    # Relationships
    class_ = relationship("Class", back_populates="class_subjects")
    subject = relationship("Subject", back_populates="class_subjects")

    def __repr__(self):
        return f"<ClassSubject(class_id={self.class_id}, subject_id={self.subject_id})>"


# ---------------------------------------------------------------------------
# Timetable
# ---------------------------------------------------------------------------
class TimetableSlot(BaseModel):
    """
    Time slot definitions for the school day (e.g., Period 1: 09:00–09:45).
    """
    __tablename__ = "timetable_slots"
    __table_args__ = (
        UniqueConstraint("tenant_id", "slot_code", name="uq_academic_timetable_slot_code"),
        {"schema": "academic", "comment": "Time period slot definitions"},
    )

    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    slot_code = Column(String(20), nullable=False, comment="e.g. P1 | P2 | BREAK | LUNCH")
    slot_name = Column(String(100), nullable=False, comment="e.g. Period 1 | Lunch Break")
    slot_type = Column(String(20), default="CLASS", comment="CLASS | BREAK | LUNCH | ASSEMBLY | FREE")

    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    duration_minutes = Column(Integer, nullable=False, comment="Duration in minutes")
    slot_order = Column(Integer, nullable=False, comment="Sequence order in the day")

    is_active = Column(Boolean, default=True, nullable=False)
    extra_metadata = Column(JSONB, default={})

    def __repr__(self):
        return f"<TimetableSlot(code={self.slot_code}, start={self.start_time})>"


class Timetable(BaseModel):
    """
    Timetable header — links a class to an academic year.
    Entries are in TimetableEntry.
    """
    __tablename__ = "timetables"
    __table_args__ = (
        UniqueConstraint("tenant_id", "class_id", "academic_year_id", name="uq_academic_timetable"),
        {"schema": "academic", "comment": "Timetable header per class per year"},
    )

    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    class_id = Column(UUID(as_uuid=True), ForeignKey("academic.classes.id", ondelete="CASCADE"), nullable=False, index=True)
    academic_year_id = Column(UUID(as_uuid=True), ForeignKey("academic.academic_years.id", ondelete="CASCADE"), nullable=False, index=True)

    effective_from = Column(Date, nullable=True, comment="When this timetable takes effect")
    effective_until = Column(Date, nullable=True, comment="When this timetable expires")

    is_active = Column(Boolean, default=True, nullable=False)
    extra_metadata = Column(JSONB, default={})

    # Relationships
    class_ = relationship("Class", back_populates="timetables")
    entries = relationship("TimetableEntry", back_populates="timetable")

    def __repr__(self):
        return f"<Timetable(class_id={self.class_id})>"


class TimetableEntry(BaseModel):
    """
    Individual timetable entry: which subject, teacher, section, day and slot.
    """
    __tablename__ = "timetable_entries"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "timetable_id", "section_id", "day_of_week", "slot_id",
            name="uq_academic_timetable_entry",
        ),
        {"schema": "academic", "comment": "Individual period slots in a timetable"},
    )

    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    timetable_id = Column(UUID(as_uuid=True), ForeignKey("academic.timetables.id", ondelete="CASCADE"), nullable=False, index=True)
    section_id = Column(UUID(as_uuid=True), ForeignKey("academic.sections.id", ondelete="CASCADE"), nullable=False, index=True)
    subject_id = Column(UUID(as_uuid=True), ForeignKey("academic.subjects.id", ondelete="SET NULL"), nullable=True, index=True)
    slot_id = Column(UUID(as_uuid=True), ForeignKey("academic.timetable_slots.id", ondelete="CASCADE"), nullable=False, index=True)

    # Teacher for this period (auth service user_id)
    teacher_user_id = Column(UUID(as_uuid=True), nullable=True, comment="Teacher's user_id from auth-service")

    day_of_week = Column(Integer, nullable=False, comment="1=Monday … 7=Sunday")
    room_number = Column(String(20), nullable=True)
    entry_type = Column(String(20), default="CLASS", comment="CLASS | PRACTICAL | FREE | ACTIVITY")

    is_active = Column(Boolean, default=True, nullable=False)
    extra_metadata = Column(JSONB, default={})

    # Relationships
    timetable = relationship("Timetable", back_populates="entries")
    section = relationship("Section", back_populates="timetable_entries")

    def __repr__(self):
        return f"<TimetableEntry(day={self.day_of_week}, slot_id={self.slot_id})>"

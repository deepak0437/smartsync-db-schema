"""
Academic Service Models — Export all models for Alembic autogenerate.
"""
from .base import Base, BaseModel

# Academic Structure
from .academic_structure import (
    AcademicYear,
    Department,
    Class,
    Section,
    Subject,
    ClassSection,
    ClassSubject,
    TimetableSlot,
    Timetable,
    TimetableEntry,
)

# Profiles
from .profile import (
    AcademicProfile,
    StudentParentMapping,
    EmployeeProfile,
    TeacherProfile,
    SubstituteTeacherAssignment,
)

# Ownership Mappings
from .ownership import (
    TeacherClassMapping,
    TeacherSubjectMapping,
    TeacherSectionMapping,
    HODDepartmentMapping,
)

# Attendance
from .attendance import (
    AttendanceRecord,
    AttendanceSummary,
    LeaveRequest,
    LeaveApproval,
)

# Homework
from .homework import (
    Homework,
    HomeworkStudentAssignment,
    HomeworkSubmission,
    HomeworkAttachment,
)

# Reviews & Remarks
from .reviews import (
    StudentReview,
    StudentRemark,
    ReviewAcknowledgment,
)

# Behavior & Discipline
from .behavior import (
    BehaviorType,
    BehaviorRecord,
    DisciplineType,
    DisciplineRecord,
)

# Achievements
from .achievements import (
    AchievementType,
    Achievement,
    AchievementEvidence,
)

# Tasks
from .tasks import (
    StudentTask,
    AcademicTask,
)

# Events (Outbox)
from .events import AcademicEvent

__all__ = [
    # Base
    "Base",
    "BaseModel",
    # Academic Structure
    "AcademicYear",
    "Department",
    "Class",
    "Section",
    "Subject",
    "ClassSection",
    "ClassSubject",
    "TimetableSlot",
    "Timetable",
    "TimetableEntry",
    # Profiles
    "AcademicProfile",
    "StudentParentMapping",
    "EmployeeProfile",
    "TeacherProfile",
    "SubstituteTeacherAssignment",
    # Ownership
    "TeacherClassMapping",
    "TeacherSubjectMapping",
    "TeacherSectionMapping",
    "HODDepartmentMapping",
    # Attendance
    "AttendanceRecord",
    "AttendanceSummary",
    "LeaveRequest",
    "LeaveApproval",
    # Homework
    "Homework",
    "HomeworkStudentAssignment",
    "HomeworkSubmission",
    "HomeworkAttachment",
    # Reviews & Remarks
    "StudentReview",
    "StudentRemark",
    "ReviewAcknowledgment",
    # Behavior & Discipline
    "BehaviorType",
    "BehaviorRecord",
    "DisciplineType",
    "DisciplineRecord",
    # Achievements
    "AchievementType",
    "Achievement",
    "AchievementEvidence",
    # Tasks
    "StudentTask",
    "AcademicTask",
    # Events
    "AcademicEvent",
]

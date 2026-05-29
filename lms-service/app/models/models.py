"""
LMS Service Models — Courses, lessons, videos, assignments, quizzes, submissions.
"""
from sqlalchemy import Boolean, Column, DateTime, Integer, Numeric, String, Text, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, relationship
from uuid import uuid4
from sqlalchemy import func


class Base(DeclarativeBase):
    pass


class BaseModel(Base):
    __abstract__ = True
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    deleted_by = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    created_by = Column(UUID(as_uuid=True), nullable=True)
    updated_by = Column(UUID(as_uuid=True), nullable=True)


class Course(BaseModel):
    """LMS course (linked to academic subject and class)."""
    __tablename__ = "courses"
    __table_args__ = {"schema": "lms"}
    subject_id = Column(UUID(as_uuid=True), nullable=False, index=True, comment="academic.subjects reference")
    class_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    academic_year_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    teacher_user_id = Column(UUID(as_uuid=True), nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    thumbnail_url = Column(Text, nullable=True)
    course_type = Column(String(20), default="STANDARD", comment="STANDARD | ELECTIVE | REMEDIAL | ENRICHMENT")
    status = Column(String(20), default="DRAFT", comment="DRAFT | PUBLISHED | ARCHIVED")
    total_duration_hours = Column(Numeric(6, 2), default=0)
    total_lessons = Column(Integer, default=0)
    is_self_paced = Column(Boolean, default=False)
    extra_metadata = Column(JSONB, default={})
    modules = relationship("CourseModule", back_populates="course")
    enrollments = relationship("CourseEnrollment", back_populates="course")


class CourseModule(BaseModel):
    """Chapter/module within a course."""
    __tablename__ = "course_modules"
    __table_args__ = {"schema": "lms"}
    course_id = Column(UUID(as_uuid=True), ForeignKey("lms.courses.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    module_order = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True)
    extra_metadata = Column(JSONB, default={})
    course = relationship("Course", back_populates="modules")
    lessons = relationship("Lesson", back_populates="module")


class Lesson(BaseModel):
    """Individual lesson within a module."""
    __tablename__ = "lessons"
    __table_args__ = {"schema": "lms"}
    module_id = Column(UUID(as_uuid=True), ForeignKey("lms.course_modules.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    lesson_type = Column(String(20), nullable=False, comment="VIDEO | PDF | AUDIO | ARTICLE | QUIZ | ASSIGNMENT | LIVE_CLASS")
    content_url = Column(Text, nullable=True, comment="CDN URL for content")
    content_text = Column(Text, nullable=True, comment="Rich text content")
    duration_minutes = Column(Integer, nullable=True)
    lesson_order = Column(Integer, nullable=False)
    is_preview = Column(Boolean, default=False, comment="Free preview lesson")
    is_active = Column(Boolean, default=True)
    extra_metadata = Column(JSONB, default={})
    module = relationship("CourseModule", back_populates="lessons")
    progress_records = relationship("LessonProgress", back_populates="lesson")


class Quiz(BaseModel):
    """Quiz/test within LMS."""
    __tablename__ = "quizzes"
    __table_args__ = {"schema": "lms"}
    lesson_id = Column(UUID(as_uuid=True), ForeignKey("lms.lessons.id", ondelete="CASCADE"), nullable=True)
    course_id = Column(UUID(as_uuid=True), ForeignKey("lms.courses.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    quiz_type = Column(String(20), default="PRACTICE", comment="PRACTICE | GRADED | EXAM")
    total_marks = Column(Integer, default=0)
    passing_marks = Column(Integer, default=0)
    duration_minutes = Column(Integer, nullable=True)
    max_attempts = Column(Integer, default=1)
    shuffle_questions = Column(Boolean, default=False)
    show_answers_after = Column(String(20), default="SUBMISSION", comment="SUBMISSION | AFTER_DEADLINE | NEVER")
    available_from = Column(DateTime(timezone=True), nullable=True)
    available_until = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
    extra_metadata = Column(JSONB, default={})
    questions = relationship("QuizQuestion", back_populates="quiz")
    attempts = relationship("QuizAttempt", back_populates="quiz")


class QuizQuestion(BaseModel):
    """Individual quiz question."""
    __tablename__ = "quiz_questions"
    __table_args__ = {"schema": "lms"}
    quiz_id = Column(UUID(as_uuid=True), ForeignKey("lms.quizzes.id", ondelete="CASCADE"), nullable=False, index=True)
    question_text = Column(Text, nullable=False)
    question_type = Column(String(20), nullable=False, comment="MCQ | TRUE_FALSE | SHORT_ANSWER | LONG_ANSWER | MATCH | FILL_BLANK")
    options = Column(JSONB, default=[], comment="Array of options for MCQ/MATCH")
    correct_answer = Column(JSONB, nullable=True, comment="Correct answer(s)")
    explanation = Column(Text, nullable=True)
    marks = Column(Integer, default=1)
    question_order = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True)
    extra_metadata = Column(JSONB, default={})
    quiz = relationship("Quiz", back_populates="questions")


class QuizAttempt(BaseModel):
    """Student quiz attempt."""
    __tablename__ = "quiz_attempts"
    __table_args__ = (UniqueConstraint("tenant_id", "quiz_id", "student_user_id", "attempt_number", name="uq_lms_quiz_attempt"), {"schema": "lms"})
    quiz_id = Column(UUID(as_uuid=True), ForeignKey("lms.quizzes.id", ondelete="CASCADE"), nullable=False, index=True)
    student_user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    attempt_number = Column(Integer, default=1)
    started_at = Column(DateTime(timezone=True), nullable=False)
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    answers = Column(JSONB, default={}, comment="Question ID → answer mapping")
    marks_obtained = Column(Integer, nullable=True)
    percentage = Column(Numeric(5, 2), nullable=True)
    is_passed = Column(Boolean, nullable=True)
    status = Column(String(20), default="IN_PROGRESS", comment="IN_PROGRESS | SUBMITTED | GRADED | TIMED_OUT")
    extra_metadata = Column(JSONB, default={})
    quiz = relationship("Quiz", back_populates="attempts")


class CourseEnrollment(BaseModel):
    """Student enrollment in a course."""
    __tablename__ = "course_enrollments"
    __table_args__ = (UniqueConstraint("tenant_id", "course_id", "student_user_id", name="uq_lms_enrollment"), {"schema": "lms"})
    course_id = Column(UUID(as_uuid=True), ForeignKey("lms.courses.id", ondelete="CASCADE"), nullable=False, index=True)
    student_user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    enrolled_at = Column(DateTime(timezone=True), nullable=False)
    completion_percentage = Column(Numeric(5, 2), default=0)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(20), default="ACTIVE", comment="ACTIVE | COMPLETED | DROPPED | SUSPENDED")
    extra_metadata = Column(JSONB, default={})
    course = relationship("Course", back_populates="enrollments")


class LessonProgress(BaseModel):
    """Student lesson completion tracking."""
    __tablename__ = "lesson_progress"
    __table_args__ = (UniqueConstraint("tenant_id", "lesson_id", "student_user_id", name="uq_lms_lesson_progress"), {"schema": "lms"})
    lesson_id = Column(UUID(as_uuid=True), ForeignKey("lms.lessons.id", ondelete="CASCADE"), nullable=False, index=True)
    student_user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    watch_duration_seconds = Column(Integer, default=0)
    last_position_seconds = Column(Integer, default=0)
    is_completed = Column(Boolean, default=False)
    completion_percentage = Column(Numeric(5, 2), default=0)
    extra_metadata = Column(JSONB, default={})
    lesson = relationship("Lesson", back_populates="progress_records")

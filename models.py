from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Float, Text, DateTime, UniqueConstraint
from database import Base
from sqlalchemy.orm import relationship
from datetime import datetime
from typing import Optional


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password = Column(String(255), nullable=False)
    is_admin = Column(Boolean, default=False)  # Add this line

    module_progress = relationship("UserModuleProgress", back_populates="user")
    course_progress = relationship("UserCourseProgress", back_populates="user")
    scores = relationship("StudentScore", back_populates="user")
    activity_progress = relationship("UserActivityProgress", back_populates="user")
    def __repr__(self):
        return f"User(id={self.id}, email='{self.email}', is_admin={self.is_admin})"
    
    def __str__(self):
        return f"{self.email}"

class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    background_image = Column(String(255))
    modules = relationship("Module", back_populates="course")  # Changed from levels
    user_progress = relationship("UserCourseProgress", back_populates="course")

    def __repr__(self):
        return f"Course(id={self.id}, name='{self.name}')"
    
    def __str__(self):
        return f"{self.name}"

class Module(Base):  # Changed from Level
    __tablename__ = "modules"  # Changed from levels

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    background_image = Column(String(255))
    locked = Column(Boolean, default=True)
    completed = Column(Boolean, default=False)
    score = Column(Float, default=0.0)  # <-- Add this line

    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)

    course = relationship("Course", back_populates="modules")  # Changed from levels
    resources = relationship("Resource", back_populates="module")  # Changed from modules
    user_progress = relationship("UserModuleProgress", back_populates="module")
    student_scores = relationship("StudentScore", back_populates="module")

    def __repr__(self):
        return f"Module(id={self.id}, name='{self.name}', course_id={self.course_id})"
    
    def __str__(self):
        return f"{self.name} (Course: {self.course.name if self.course else 'N/A'})"

class Resource(Base):  # Changed from Module
    __tablename__ = "resources"  # Changed from modules

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    module_id = Column(Integer, ForeignKey("modules.id"), nullable=False)

    module = relationship("Module", back_populates="resources")
    videos = relationship("Video", back_populates="resource")
    pdfs = relationship("PDF", back_populates="resource")
    activities = relationship("Activity", back_populates="resource")

    def __repr__(self):
        return f"Resource(id={self.id}, name='{self.name}', module_id={self.module_id})"
    
    def __str__(self):
        return f"{self.name} (Module: {self.module.name if self.module else 'N/A'})"
class Video(Base):
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    thumbnail = Column(String(255))
    url = Column(String(500), nullable=False)

    resource_id = Column(Integer, ForeignKey("resources.id"), nullable=False)  # Changed from module_id
    resource = relationship("Resource", back_populates="videos")  # Changed from module

    def __repr__(self):
        return f"Video(id={self.id}, title='{self.title}', resource_id={self.resource_id})"
    
    def __str__(self):
        return f"{self.title} (Resource: {self.resource.name if self.resource else 'N/A'})"

class Activity(Base):
    __tablename__ = "activities"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)

    resource_id = Column(Integer, ForeignKey("resources.id"), nullable=False)  # Changed from module_id
    resource = relationship("Resource", back_populates="activities")  # Changed from module
    user_progress = relationship("UserActivityProgress", back_populates="activity")

    def __repr__(self):
        return f"Activity(id={self.id}, name='{self.name}', score={self.score})"
    
    def __str__(self):
        return f"{self.name} (Score: {self.name}, Resource: {self.resource_id if self.resource else 'N/A'})"

class PDF(Base):
    __tablename__ = "pdfs"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    thumbnail = Column(String(255))
    url = Column(String(500), nullable=False)

    resource_id = Column(Integer, ForeignKey("resources.id"), nullable=False)  # Changed from module_id
    resource = relationship("Resource", back_populates="pdfs")  # Changed from module
    # file: Optional[UploadFile] = None
    def __repr__(self):
        return f"PDF(id={self.id}, title='{self.title}', resource_id={self.resource_id})"
    
    def __str__(self):
        return f"{self.title} (Resource: {self.resource.name if self.resource else 'N/A'})"

class UserModuleProgress(Base):
    __tablename__ = "user_module_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    module_id = Column(Integer, ForeignKey("modules.id"), nullable=False)
    locked = Column(Boolean, default=True)
    completed = Column(Boolean, default=False)
    last_accessed = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="module_progress")
    module = relationship("Module", back_populates="user_progress")
    
    __table_args__ = (
        UniqueConstraint('user_id', 'module_id', name='uix_user_module'),
    )

class UserCourseProgress(Base):
    __tablename__ = "user_course_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    locked = Column(Boolean, default=True)
    completed = Column(Boolean, default=False)
    last_accessed = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="course_progress")
    course = relationship("Course", back_populates="user_progress")

    __table_args__ = (
        UniqueConstraint('user_id', 'course_id', name='uix_user_course'),
    )

class StudentScore(Base):
    __tablename__ = "student_scores"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    module_id = Column(Integer, ForeignKey("modules.id"), nullable=False)
    total_score = Column(Float, default=0.0)
    completed_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="scores")
    module = relationship("Module", back_populates="student_scores")

    __table_args__ = (
        UniqueConstraint('user_id', 'module_id', name='uix_user_module_score'),
    )
class UserActivityProgress(Base):
    __tablename__ = "user_activity_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    activity_id = Column(Integer, ForeignKey("activities.id"), nullable=False)
    completed = Column(Boolean, default=False)

    # Relationships
    user = relationship("User", back_populates="activity_progress")
    activity = relationship("Activity", back_populates="user_progress")

    def __repr__(self):
        return f"UserActivityProgress(user_id={self.user_id}, activity_id={self.activity_id}, completed={self.completed})"

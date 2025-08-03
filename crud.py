# crud.py - Comprehensive CRUD operations for the learning management system

from sqlalchemy.orm import Session
from sqlalchemy import and_
from models import Course, StudentScore, Activity, Resource, Module, User, UserCourseProgress, UserModuleProgress,Video
from passlib.context import CryptContext
from typing import Optional, List
from datetime import datetime

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# ==================== USER CRUD ====================

def create_user(db: Session, email: str, password: str, is_admin: bool = False) -> User:
    """Create a new user"""
    hashed_password = hash_password(password)
    db_user = User(email=email, password=hashed_password, is_admin=is_admin)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_user(db: Session, user_id: int) -> Optional[User]:
    """Get user by ID"""
    return db.query(User).filter(User.id == user_id).first()

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Get user by email"""
    return db.query(User).filter(User.email == email).first()

def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
    """Get all users with pagination"""
    return db.query(User).offset(skip).limit(limit).all()

def update_user(db: Session, user_id: int, email: str = None, password: str = None, is_admin: bool = None) -> Optional[User]:
    """Update user information"""
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user:
        if email:
            db_user.email = email
        if password:
            db_user.password = hash_password(password)
        if is_admin is not None:
            db_user.is_admin = is_admin
        db.commit()
        db.refresh(db_user)
    return db_user

def delete_user(db: Session, user_id: int) -> bool:
    """Delete user"""
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user:
        db.delete(db_user)
        db.commit()
        return True
    return False

# ==================== COURSE CRUD ====================

def create_course(db: Session, name: str) -> Course:
    """Create a new course"""
    db_course = Course(name=name)
    db.add(db_course)
    db.commit()
    db.refresh(db_course)
    return db_course

def get_course(db: Session, course_id: int) -> Optional[Course]:
    """Get course by ID"""
    return db.query(Course).filter(Course.id == course_id).first()

def get_courses(db: Session, skip: int = 0, limit: int = 100) -> List[Course]:
    """Get all courses with pagination"""
    return db.query(Course).offset(skip).limit(limit).all()

def update_course(db: Session, course_id: int, name: str) -> Optional[Course]:
    """Update course name"""
    db_course = db.query(Course).filter(Course.id == course_id).first()
    if db_course:
        db_course.name = name
        db.commit()
        db.refresh(db_course)
    return db_course

def delete_course(db: Session, course_id: int) -> bool:
    """Delete course and all related data"""
    db_course = db.query(Course).filter(Course.id == course_id).first()
    if db_course:
        db.delete(db_course)
        db.commit()
        return True
    return False

# ==================== MODULE CRUD (Previously LEVEL CRUD) ====================

def create_module(db: Session, name: str, course_id: int, description: str = None, 
                 background_image: str = None, locked: bool = True, completed: bool = False) -> Module:
    """Create a new module (previously level)"""
    db_module = Module(
        name=name,
        course_id=course_id,
        description=description,
        background_image=background_image,
        locked=locked,
        completed=completed
    )
    db.add(db_module)
    db.commit()
    db.refresh(db_module)
    return db_module

def get_module(db: Session, module_id: int) -> Optional[Module]:
    """Get module by ID"""
    return db.query(Module).filter(Module.id == module_id).first()

def get_modules_by_course(db: Session, course_id: int) -> List[Module]:
    """Get all modules for a specific course"""
    return db.query(Module).filter(Module.course_id == course_id).all()

def get_modules(db: Session, skip: int = 0, limit: int = 100) -> List[Module]:
    """Get all modules with pagination"""
    return db.query(Module).offset(skip).limit(limit).all()
def update_module(
    db: Session,
    module_id: int,
    name: str = None,
    description: str = None,
    background_image: str = None,
    locked: bool = None,
    completed: bool = None,
    user_id: int = None  # <-- Add user_id for per-user progress
) -> Optional[Module]:
    """Update module information and update user progress/score if completed"""
    print(f"Updating module {module_id} for user {user_id} with completed={completed}")
    db_module = db.query(Module).filter(Module.id == module_id).first()
    if not db_module:
        return None

    if name is not None:
        db_module.name = name
    if description is not None:
        db_module.description = description
    if background_image is not None:
        db_module.background_image = background_image
    if locked is not None:
        db_module.locked = locked
    if completed is not None and user_id is not None:
        # Update user progress for this module
        user_progress = db.query(UserModuleProgress).filter(
            UserModuleProgress.user_id == user_id,
            UserModuleProgress.module_id == module_id
        ).first()
        if not user_progress:
            user_progress = UserModuleProgress(
                user_id=user_id,
                module_id=module_id,
                locked=False,
                completed=completed,
            )
            db.add(user_progress)
            db.commit()
            db.refresh(user_progress)
        else:
            user_progress.completed = completed
            user_progress.last_accessed = datetime.utcnow()
            db.commit()
            db.refresh(user_progress)
        print(completed, user_progress)
        
        # If completed, update student_score using module.score from modules table
        if completed == True:
            # Fetch the score from the modules table instead of user_progress
            module_score = db_module.score or 0.0
            print(f"Module {module_id} completed by user {user_id} with score {module_score} (from modules table)")
            
            # Update or create student_score, ADDING to previous total
            student_score = db.query(StudentScore).filter(
                StudentScore.user_id == user_id,
                StudentScore.module_id == module_id
            ).first()
            
            if not student_score:
                # Create new student score with module score
                student_score = StudentScore(
                    user_id=user_id,
                    module_id=module_id,
                    total_score=module_score,  # Use module score directly for new entry
                    completed_at=datetime.utcnow()
                )
                print(f"Creating new student score: {student_score}")
                db.add(student_score)
            else:
                # Add module score to existing total score
                previous_total = student_score.total_score or 0.0
                new_total = previous_total + module_score
                student_score.total_score = new_total
                student_score.completed_at = datetime.utcnow()
                print(f"Updating existing student score: previous={previous_total}, module={module_score}, new_total={new_total}")
            
            db.commit()
            db.refresh(student_score)

    db.commit()
    db.refresh(db_module)
    return db_module

def delete_module(db: Session, module_id: int) -> bool:
    """Delete module and all related data"""
    db_module = db.query(Module).filter(Module.id == module_id).first()
    if db_module:
        db.delete(db_module)
        db.commit()
        return True
    return False

# ==================== RESOURCE CRUD (Previously MODULE CRUD) ====================

def create_resource(db: Session, name: str, module_id: int, locked: bool = True, completed: bool = False) -> Resource:
    """Create a new resource"""
    db_resource = Resource(
        name=name,
        module_id=module_id,
        locked=locked,
        completed=completed
    )
    db.add(db_resource)
    db.commit()
    db.refresh(db_resource)
    return db_resource

def get_resource(db: Session, resource_id: int) -> Optional[Resource]:
    """Get resource by ID"""
    return db.query(Resource).filter(Resource.id == resource_id).first()

def get_resources_by_module(db: Session, module_id: int) -> List[Resource]:
    """Get all resources for a specific module"""
    return db.query(Resource).filter(Resource.module_id == module_id).all()

def get_resources(db: Session, skip: int = 0, limit: int = 100) -> List[Resource]:
    """Get all resources with pagination"""
    return db.query(Resource).offset(skip).limit(limit).all()

def update_resource(db: Session, resource_id: int, name: str = None, 
                   locked: bool = None, completed: bool = None) -> Optional[Resource]:
    """Update resource information"""
    db_resource = db.query(Resource).filter(Resource.id == resource_id).first()
    if db_resource:
        if name is not None:
            db_resource.name = name
        if locked is not None:
            db_resource.locked = locked
        if completed is not None:
            db_resource.completed = completed
        db.commit()
        db.refresh(db_resource)
    return db_resource

def delete_resource(db: Session, resource_id: int) -> bool:
    """Delete resource"""
    db_resource = db.query(Resource).filter(Resource.id == resource_id).first()
    if db_resource:
        db.delete(db_resource)
        db.commit()
        return True
    return False

# Update Video, Activity, and PDF CRUD to use resource_id instead of module_id

def create_video(db: Session, title: str, url: str, resource_id: int, thumbnail: str = None) -> Video:
    """Create a new video"""
    db_video = Video(
        title=title,
        url=url,
        resource_id=resource_id,
        thumbnail=thumbnail
    )
    db.add(db_video)
    db.commit()
    db.refresh(db_video)
    return db_video

def get_videos_by_resource(db: Session, resource_id: int) -> List[Video]:
    """Get all videos for a specific resource"""
    return db.query(Video).filter(Video.resource_id == resource_id).all()

# Similar updates for Activity and PDF CRUD functions...

# Update utility functions
def get_course_with_modules(db: Session, course_id: int) -> Optional[Course]:
    """Get course with all its modules"""
    return db.query(Course).filter(Course.id == course_id).first()

def get_module_with_resources(db: Session, module_id: int) -> Optional[Module]:
    """Get module with all its resources"""
    return db.query(Module).filter(Module.id == module_id).first()

def get_resource_with_content(db: Session, resource_id: int) -> Optional[Resource]:
    """Get resource with all its content (videos, PDFs, activities)"""
    return db.query(Resource).filter(Resource.id == resource_id).first()

def unlock_next_content(db: Session, current_resource_id: int):
    """Unlock next resource/module when current one is completed"""
    current_resource = get_resource(db, current_resource_id)
    if not current_resource or not current_resource.completed:
        return False
    
    # Find next resource in the same module
    next_resource = db.query(Resource).filter(
        and_(Resource.module_id == current_resource.module_id, 
             Resource.id > current_resource_id)
    ).order_by(Resource.id).first()
    
    if next_resource:
        next_resource.locked = False
        db.commit()
        return True
    else:
        # If no more resources in module, unlock next module
        current_module = current_resource.module
        next_module = db.query(Module).filter(
            and_(Module.course_id == current_module.course_id,
                 Module.id > current_module.id)
        ).order_by(Module.id).first()
        
        if next_module:
            next_module.locked = False
            # Unlock first resource of next module
            first_resource = db.query(Resource).filter(
                Resource.module_id == next_module.id
            ).order_by(Resource.id).first()
            if first_resource:
                first_resource.locked = False
            db.commit()
            return True
    
    return False

def get_modules_by_course_with_progress(db: Session, course_id: int, user_id: int) -> List[Module]:
    """Get all modules for a course with user-specific progress"""
    modules = db.query(Module).filter(Module.course_id == course_id).all()
    
    # Get user progress for these modules
    progress_records = (
        db.query(UserModuleProgress)
        .filter(
            UserModuleProgress.user_id == user_id,
            UserModuleProgress.module_id.in_([m.id for m in modules])
        ).all()
    )
    
    # Convert progress records to dictionary for easier lookup
    progress_dict = {
        p.module_id: {
            "locked": p.locked,
            "completed": p.completed,
            "last_accessed": p.last_accessed.isoformat() if p.last_accessed else None
        } for p in progress_records
    }
    
    # Attach progress to each module
    result = []
    for i, module in enumerate(modules):
        module_dict = {
            "id": module.id,
            "name": module.name,
            "description": module.description,
            "background_image": module.background_image,
            "course_id": module.course_id,
            "user_progress": progress_dict.get(module.id, {
                "locked": i != 0,  # First module unlocked by default
                "completed": False,
                "last_accessed": None
            })
        }
        
        # Create default progress if not exists
        if module.id not in progress_dict:
            default_progress = UserModuleProgress(
                user_id=user_id,
                module_id=module.id,
                locked=i != 0,  # First module unlocked by default
                completed=False
            )
            db.add(default_progress)
            db.commit()
        
        result.append(module_dict)
    
    return result

def get_courses_with_progress(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[dict]:
    """Get all courses with user-specific progress"""
    courses = db.query(Course).all()
    
    # Get user progress for these courses
    progress_records = (
        db.query(UserCourseProgress)
        .filter(
            UserCourseProgress.user_id == user_id,
            UserCourseProgress.course_id.in_([c.id for c in courses])
        ).all()
    )
    
    # Convert progress records to dictionary
    progress_dict = {
        p.course_id: {
            "locked": p.locked,
            "completed": p.completed,
            "last_accessed": p.last_accessed.isoformat() if p.last_accessed else None
        } for p in progress_records
    }
    
    # Prepare response with progress
    result = []
    for i, course in enumerate(courses):
        course_dict = {
            "id": course.id,
            "name": course.name,
            "description": course.description,
            "background_image": course.background_image,
            "user_progress": progress_dict.get(course.id, {
                "locked": i != 0,  # First course unlocked by default
                "completed": False,
                "last_accessed": None
            })
        }
        
        # Create default progress if not exists
        if course.id not in progress_dict:
            default_progress = UserCourseProgress(
                user_id=user_id,
                course_id=course.id,
                locked=i != 0,  # First course unlocked by default
                completed=False
            )
            db.add(default_progress)
            db.commit()
        
        result.append(course_dict)
    
    return result

def calculate_and_save_student_score(db: Session, user_id: int, module_id: int) -> StudentScore:
    """
    Calculate total score from completed activities in a module and save to student_scores.
    """
    # Get all completed activities for the module
    activities = db.query(Activity).join(Resource, Activity.resource_id == Resource.id).filter(
        Resource.module_id == module_id,
        Activity.completed == True,
        Activity.score != None
    ).all()

    if not activities:
        return None

    total_score = sum(activity.score for activity in activities)

    # Create or update student score
    student_score = db.query(StudentScore).filter(
        StudentScore.user_id == user_id,
        StudentScore.module_id == module_id
    ).first()

    if not student_score:
        student_score = StudentScore(
            user_id=user_id,
            module_id=module_id,
            total_score=total_score,
            completed_at=datetime.utcnow()
        )
        db.add(student_score)
    else:
        student_score.total_score = total_score
        student_score.completed_at = datetime.utcnow()

    db.commit()
    db.refresh(student_score)
    return student_score

def get_student_scores(db: Session, user_id: int):
    """
    Get all scores for a student.
    """
    return db.query(StudentScore).filter(StudentScore.user_id == user_id).all()

def get_module_scores(db: Session, module_id: int):
    """
    Get all student scores for a module.
    """
    return db.query(StudentScore).filter(StudentScore.module_id == module_id).order_by(StudentScore.total_score.desc()).all()

def unlock_next_content(db, module_id, user_id=None):
    """
    Unlock the next module for the user after completing the current module.
    """
    print(module_id,user_id)
    current_module = db.query(Module).filter(Module.id == module_id).first()
    if not current_module:
        return None

    # Find the next module in the same course
    next_module = db.query(Module).filter(
        Module.course_id == current_module.course_id,
        Module.id > module_id
    ).order_by(Module.id).first()

    if next_module and user_id:
        print(f"Unlocking next module {next_module.id} for user {user_id}")
        # Unlock next module for this user
        next_progress = db.query(UserModuleProgress).filter(
            UserModuleProgress.user_id == user_id,
            UserModuleProgress.module_id == next_module.id
        ).first()
        if not next_progress:
            print(f"Creating new progress for user {user_id} in module {next_module.id}")
            next_progress = UserModuleProgress(
                user_id=user_id,
                module_id=next_module.id,
                locked=False,
                completed=False
            )
            db.add(next_progress)
        else:
            next_progress.locked = False
        db.commit()
    return next_module
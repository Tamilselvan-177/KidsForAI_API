# main.py - Complete FastAPI application with CRUD endpoints

from fastapi import FastAPI, Depends, HTTPException, Response, Request, Query
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from database import SessionLocal, engine, Base
import crud, schemas
from auth import create_access_token, verify_token
from typing import List, Optional
from sqlalchemy import and_
from datetime import datetime
from models import StudentScore
from fastapi.staticfiles import StaticFiles

# SQLAdmin imports
from sqlalchemy import create_engine
from sqladmin import Admin, ModelView
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request as StarletteRequest
from starlette.responses import RedirectResponse

# Import your existing models
from models import User, Course, Module, Video, Activity, PDF, Resource, UserModuleProgress

app = FastAPI(title="Learning Management System API", version="1.0.0")

# Serve the 'videos' folder at /videos
app.mount("/videos", StaticFiles(directory="videos"), name="videos")

# CORS for Flutter local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create SQLAlchemy tables
Base.metadata.create_all(bind=engine)

# Authentication backend for admin
class AdminAuth(AuthenticationBackend):
    async def login(self, request: StarletteRequest) -> bool:
        form = await request.form()
        username, password = form["username"], form["password"]
        
        if username == "admin" and password == "admin123":
            request.session.update({"admin": "authenticated"})
            return True
        return False

    async def logout(self, request: StarletteRequest) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: StarletteRequest) -> bool:
        return request.session.get("admin") == "authenticated"

# Create admin interface
authentication_backend = AdminAuth(secret_key="your-secret-key-here")
admin = Admin(app, engine, authentication_backend=authentication_backend)

# Admin views
class UserAdmin(ModelView, model=User):
    column_list = [User.id, User.email]
    column_details_exclude_list = [User.password]
    can_delete = False
    name = "User"
    name_plural = "Users"
    icon = "fa-solid fa-user"

class CourseAdmin(ModelView, model=Course):
    column_list = [Course.id, Course.name]
    name = "Course"
    name_plural = "Courses"  
    icon = "fa-solid fa-book"

class ModuleAdmin(ModelView, model=Module):
    column_list = [Module.id, Module.name, Module.description, Module.locked, 
                  Module.completed, Module.course_id]
    name = "Module"
    name_plural = "Modules"
    icon = "fa-solid fa-layer-group"

class ResourceAdmin(ModelView, model=Resource):
    column_list = [Resource.id, Resource.name, Resource.module_id]
    name = "Resource"
    name_plural = "Resources"
    icon = "fa-solid fa-puzzle-piece"

class VideoAdmin(ModelView, model=Video):
    column_list = [Video.id, Video.title, Video.url, Video.resource_id]
    name = "Video"
    name_plural = "Videos"
    icon = "fa-solid fa-video"

class ActivityAdmin(ModelView, model=Activity):
    column_list = [Activity.id, Activity.name, Activity.completed, 
                  Activity.score, Activity.resource_id]
    name = "Activity"
    name_plural = "Activities"
    icon = "fa-solid fa-tasks"

class PDFAdmin(ModelView, model=PDF):
    column_list = [PDF.id, PDF.title, PDF.url, PDF.resource_id]
    name = "PDF"
    name_plural = "PDFs"
    icon = "fa-solid fa-file-pdf"

class UserProgressAdmin(ModelView, model=UserModuleProgress):
    column_list = [
        UserModuleProgress.id, 
        UserModuleProgress.user_id, 
        UserModuleProgress.module_id, 
        UserModuleProgress.locked, 
        UserModuleProgress.completed,
        UserModuleProgress.last_accessed
    ]
    can_create = False  # Progress is created automatically
    name = "User Progress"
    name_plural = "User Progress"
    icon = "fa-solid fa-chart-line"
class StudentScoreAdmin(ModelView, model=StudentScore):
    column_list = [
        StudentScore.id,
        StudentScore.user_id,
        StudentScore.module_id,
        StudentScore.total_score,
        StudentScore.completed_at
    ]
    can_create = False
    name = "Student Score"
    name_plural = "Student Scores"
    icon = "fa-solid fa-star"

# Register admin views
admin.add_view(UserAdmin)
admin.add_view(CourseAdmin)
admin.add_view(ModuleAdmin)
admin.add_view(ResourceAdmin)
admin.add_view(VideoAdmin)
admin.add_view(ActivityAdmin)
admin.add_view(PDFAdmin)
admin.add_view(UserProgressAdmin)
admin.add_view(StudentScoreAdmin)
# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Helper function to get current user
def get_current_user(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user_data = verify_token(token)
    if not user_data:
        raise HTTPException(status_code=403, detail="Invalid token")
    
    user = crud.get_user_by_email(db, user_data["sub"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user

# Helper function to check admin permissions
def get_admin_user(current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403, 
            detail="Admin access required. Only administrators can perform this action."
        )
    return current_user

# Helper function for read-only access (all authenticated users)
def get_authenticated_user(current_user: User = Depends(get_current_user)):
    return current_user

# ==================== AUTHENTICATION ENDPOINTS ====================

@app.post("/register", response_model=schemas.User)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """Register a new user (anyone can register, but not as admin)"""
    db_user = crud.get_user_by_email(db, user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Only allow admin creation if no users exist (first user) or if requested by existing admin
    is_admin = False
    existing_users = crud.get_users(db, limit=1)
    if not existing_users:  # First user becomes admin
        is_admin = True
    
    return crud.create_user(db, user.email, user.password, is_admin)

@app.post("/admin/register", response_model=schemas.User)
def admin_register(user: schemas.UserCreate, db: Session = Depends(get_db), 
                   admin_user: User = Depends(get_admin_user)):
    """Register a new user with admin privileges (admin only)"""
    db_user = crud.get_user_by_email(db, user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return crud.create_user(db, user.email, user.password, user.is_admin)

@app.post("/login", response_model=schemas.GenericResponse)
def login(user: schemas.UserLogin, response: Response, db: Session = Depends(get_db)):
    """Login user"""
    db_user = crud.get_user_by_email(db, user.email)
    if not db_user or not crud.verify_password(user.password, db_user.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    token = create_access_token({"sub": db_user.email})
    
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=365*24*60*60,
        expires=365*24*60*60,
        samesite="Lax",
        secure=False
    )
    
    response = {
        "message": "Login successful",
        "cookie": token,
        "success": True
    }
    return response

@app.get("/me", response_model=schemas.User)
def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return current_user

@app.post("/logout", response_model=schemas.GenericResponse)
def logout(response: Response):
    """Logout user"""
    response.delete_cookie(key="access_token")
    return {"message": "Logout successful"}

# ==================== USER CRUD ENDPOINTS ====================

@app.get("/users", response_model=List[schemas.User])
def get_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), 
              admin_user: User = Depends(get_admin_user)):
    """Get all users (admin only)"""
    return crud.get_users(db, skip=skip, limit=limit)

@app.get("/users/{user_id}", response_model=schemas.User)
def get_user(user_id: int, db: Session = Depends(get_db), 
             admin_user: User = Depends(get_admin_user)):
    """Get user by ID (admin only)"""
    db_user = crud.get_user(db, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

@app.put("/users/{user_id}", response_model=schemas.User)
def update_user(user_id: int, user_update: schemas.UserUpdate, db: Session = Depends(get_db),
                admin_user: User = Depends(get_admin_user)):
    """Update user information (admin only)"""
    db_user = crud.update_user(db, user_id, user_update.email, user_update.password)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

@app.delete("/users/{user_id}", response_model=schemas.GenericResponse)
def delete_user(user_id: int, db: Session = Depends(get_db),
                admin_user: User = Depends(get_admin_user)):
    """Delete user (admin only)"""
    if not crud.delete_user(db, user_id):
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User deleted successfully"}

# ==================== COURSE CRUD ENDPOINTS ====================

@app.post("/courses", response_model=schemas.Course)
def create_course(course: schemas.CourseCreate, db: Session = Depends(get_db),
                  admin_user: User = Depends(get_admin_user)):
    """Create a new course (admin only)"""
    return crud.create_course(db, course.name)

@app.get("/courses", response_model=List[schemas.CourseWithProgress])
def get_courses(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_authenticated_user)
):
    """Get all courses with user-specific progress"""
    return crud.get_courses_with_progress(db, current_user.id, skip=skip, limit=limit)

@app.get("/courses/{course_id}", response_model=schemas.Course)
def get_course(
    course_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_authenticated_user)  # Add authentication
):
    """Get course by ID (authenticated users only)"""
    db_course = crud.get_course(db, course_id)
    if not db_course:
        raise HTTPException(status_code=404, detail="Course not found")
    return db_course

@app.put("/courses/{course_id}", response_model=schemas.Course)
def update_course(course_id: int, course_update: schemas.CourseUpdate, 
                  db: Session = Depends(get_db), admin_user: User = Depends(get_admin_user)):
    """Update course (admin only)"""
    db_course = crud.update_course(db, course_id, course_update.name)
    if not db_course:
        raise HTTPException(status_code=404, detail="Course not found")
    return db_course

@app.delete("/courses/{course_id}", response_model=schemas.GenericResponse)
def delete_course(course_id: int, db: Session = Depends(get_db),
                  admin_user: User = Depends(get_admin_user)):
    """Delete course (admin only)"""
    if not crud.delete_course(db, course_id):
        raise HTTPException(status_code=404, detail="Course not found")
    return {"message": "Course deleted successfully"}

# ==================== MODULE CRUD ENDPOINTS ====================

@app.post("/modules", response_model=schemas.Module)
def create_module(module: schemas.ModuleCreate, db: Session = Depends(get_db),
                  admin_user: User = Depends(get_admin_user)):
    """Create a new module (admin only)"""
    return crud.create_module(db, module.name, module.level_id, module.locked, module.completed)

@app.get("/modules", response_model=List[schemas.Module])
def get_modules(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_authenticated_user)  # Add authentication
):
    """Get all modules (authenticated users only)"""
    return crud.get_modules(db, skip=skip, limit=limit)

@app.get("/modules/{module_id}", response_model=schemas.ModuleResource)
def get_module(
    module_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_authenticated_user)  # Add authentication
):
    """Get module by ID (authenticated users only)"""
    db_module = crud.get_module(db, module_id)
    if not db_module:
        raise HTTPException(status_code=404, detail="Module not found")
    return db_module

@app.get("/courses/{course_id}/modules", response_model=List[schemas.ModuleResponse])
def get_course_modules(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_authenticated_user)
):
    """Get all modules for a course with user-specific progress"""
    modules = crud.get_modules_by_course_with_progress(db, course_id, current_user.id)
    if not modules:
        raise HTTPException(status_code=404, detail="Course not found")
    return [schemas.ModuleResponse(**module) for module in modules]

@app.get("/modules/{module_id}/resources", response_model=List[schemas.Resource])  # Changed from modules
def get_resources_by_module(module_id: int, db: Session = Depends(get_db)):
    """Get all resources for a specific module (public access)"""
    return crud.get_resources_by_module(db, module_id)

@app.put("/modules/{module_id}", response_model=schemas.Module)
def update_module(module_id: int, module_update: schemas.ModuleUpdate,
                  db: Session = Depends(get_db), admin_user: User = Depends(get_admin_user)):
    """Update module (admin only)"""
    db_module = crud.update_module(db, module_id, module_update.name, 
                                 module_update.locked, module_update.completed)
    if not db_module:
        raise HTTPException(status_code=404, detail="Module not found")
    return db_module

@app.delete("/modules/{module_id}", response_model=schemas.GenericResponse)
def delete_module(module_id: int, db: Session = Depends(get_db),
                  admin_user: User = Depends(get_admin_user)):
    """Delete module (admin only)"""
    if not crud.delete_module(db, module_id):
        raise HTTPException(status_code=404, detail="Module not found")
    return {"message": "Module deleted successfully"}# ==================== VIDEO CRUD ENDPOINTS ====================

@app.post("/videos", response_model=schemas.Video)
def create_video(video: schemas.VideoCreate, db: Session = Depends(get_db),
                 admin_user: User = Depends(get_admin_user)):
    """Create a new video (admin only)"""
    return crud.create_video(db, video.title, video.url, video.module_id, video.thumbnail)

@app.get("/videos", response_model=List[schemas.Video])
def get_videos(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all videos (public access)"""
    return crud.get_videos(db, skip=skip, limit=limit)

@app.get("/videos/{video_id}", response_model=schemas.Video)
def get_video(video_id: int, db: Session = Depends(get_db)):
    """Get video by ID (public access)"""
    db_video = crud.get_video(db, video_id)
    if not db_video:
        raise HTTPException(status_code=404, detail="Video not found")
    return db_video

@app.get("/modules/{module_id}/videos", response_model=List[schemas.Video])
def get_videos_by_module(module_id: int, db: Session = Depends(get_db)):
    """Get all videos for a specific module (public access)"""
    return crud.get_videos_by_module(db, module_id)

@app.put("/videos/{video_id}", response_model=schemas.Video)
def update_video(video_id: int, video_update: schemas.VideoUpdate,
                 db: Session = Depends(get_db), admin_user: User = Depends(get_admin_user)):
    """Update video (admin only)"""
    db_video = crud.update_video(db, video_id, video_update.title, 
                               video_update.url, video_update.thumbnail)
    if not db_video:
        raise HTTPException(status_code=404, detail="Video not found")
    return db_video

@app.delete("/videos/{video_id}", response_model=schemas.GenericResponse)
def delete_video(video_id: int, db: Session = Depends(get_db),
                 admin_user: User = Depends(get_admin_user)):
    """Delete video (admin only)"""
    if not crud.delete_video(db, video_id):
        raise HTTPException(status_code=404, detail="Video not found")
    return {"message": "Video deleted successfully"}

# ==================== ACTIVITY CRUD ENDPOINTS ====================

@app.post("/activities", response_model=schemas.Activity)
def create_activity(activity: schemas.ActivityCreate, db: Session = Depends(get_db),
                    admin_user: User = Depends(get_admin_user)):
    """Create a new activity (admin only)"""
    return crud.create_activity(db, activity.name, activity.module_id, 
                              activity.completed, activity.score)

@app.get("/activities", response_model=List[schemas.Activity])
def get_activities(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all activities (public access)"""
    return crud.get_activities(db, skip=skip, limit=limit)

@app.get("/activities/{activity_id}", response_model=schemas.Activity)
def get_activity(activity_id: int, db: Session = Depends(get_db)):
    """Get activity by ID (public access)"""
    db_activity = crud.get_activity(db, activity_id)
    if not db_activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    return db_activity

@app.get("/modules/{module_id}/activities", response_model=List[schemas.Activity])
def get_activities_by_module(module_id: int, db: Session = Depends(get_db)):
    """Get all activities for a specific module (public access)"""
    return crud.get_activities_by_module(db, module_id)

@app.put("/activities/{activity_id}", response_model=schemas.Activity)
def update_activity(activity_id: int, activity_update: schemas.ActivityUpdate,
                    db: Session = Depends(get_db), admin_user: User = Depends(get_admin_user)):
    """Update activity (admin only)"""
    db_activity = crud.update_activity(db, activity_id, activity_update.name,
                                     activity_update.completed, activity_update.score)
    if not db_activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    return db_activity

@app.delete("/activities/{activity_id}", response_model=schemas.GenericResponse)
def delete_activity(activity_id: int, db: Session = Depends(get_db),
                    admin_user: User = Depends(get_admin_user)):
    """Delete activity (admin only)"""
    if not crud.delete_activity(db, activity_id):
        raise HTTPException(status_code=404, detail="Activity not found")
    return {"message": "Activity deleted successfully"}

# ==================== PDF CRUD ENDPOINTS ====================

@app.post("/pdfs", response_model=schemas.PDF)
def create_pdf(pdf: schemas.PDFCreate, db: Session = Depends(get_db),
               admin_user: User = Depends(get_admin_user)):
    """Create a new PDF (admin only)"""
    return crud.create_pdf(db, pdf.title, pdf.url, pdf.module_id, pdf.thumbnail)

@app.get("/pdfs", response_model=List[schemas.PDF])
def get_pdfs(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all PDFs (public access)"""
    return crud.get_pdfs(db, skip=skip, limit=limit)

@app.get("/pdfs/{pdf_id}", response_model=schemas.PDF)
def get_pdf(pdf_id: int, db: Session = Depends(get_db)):
    """Get PDF by ID (public access)"""
    db_pdf = crud.get_pdf(db, pdf_id)
    if not db_pdf:
        raise HTTPException(status_code=404, detail="PDF not found")
    return db_pdf

@app.get("/modules/{module_id}/pdfs", response_model=List[schemas.PDF])
def get_pdfs_by_module(module_id: int, db: Session = Depends(get_db)):
    """Get all PDFs for a specific module (public access)"""
    return crud.get_pdfs_by_module(db, module_id)

@app.put("/pdfs/{pdf_id}", response_model=schemas.PDF)
def update_pdf(pdf_id: int, pdf_update: schemas.PDFUpdate,
               db: Session = Depends(get_db), admin_user: User = Depends(get_admin_user)):
    """Update PDF (admin only)"""
    db_pdf = crud.update_pdf(db, pdf_id, pdf_update.title, 
                           pdf_update.url, pdf_update.thumbnail)
    if not db_pdf:
        raise HTTPException(status_code=404, detail="PDF not found")
    return db_pdf

@app.delete("/pdfs/{pdf_id}", response_model=schemas.GenericResponse)
def delete_pdf(pdf_id: int, db: Session = Depends(get_db),
               admin_user: User = Depends(get_admin_user)):
    """Delete PDF (admin only)"""
    if not crud.delete_pdf(db, pdf_id):
        raise HTTPException(status_code=404, detail="PDF not found")
    return {"message": "PDF deleted successfully"}

# ==================== UTILITY ENDPOINTS ====================

@app.get("/courses/{course_id}/complete", response_model=schemas.Course)
def get_course_with_modules(course_id: int, db: Session = Depends(get_db)):
    """Get course with all its modules and nested content (public access)"""
    db_course = crud.get_course_with_modules(db, course_id)
    if not db_course:
        raise HTTPException(status_code=404, detail="Course not found")
    return db_course

@app.get("/modules/{module_id}/complete", response_model=schemas.Module)
def get_module_with_resources(module_id: int, db: Session = Depends(get_db)):
    """Get module with all its resources and nested content (public access)"""
    db_module = crud.get_module_with_resources(db, module_id)
    if not db_module:
        raise HTTPException(status_code=404, detail="Module not found")
    return db_module

@app.get("/resources/{resource_id}/complete", response_model=schemas.Resource)
def get_resource_with_content(resource_id: int, db: Session = Depends(get_db)):
    """Get resource with all its content (videos, PDFs, activities) (public access)"""
    db_resource = crud.get_resource_with_content(db, resource_id)
    if not db_resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    return db_resource

@app.get("/progress", response_model=List[schemas.CourseProgress])
def get_user_progress(current_user: User = Depends(get_authenticated_user), db: Session = Depends(get_db)):
    """Get current user's progress across all courses (authenticated users only)"""
    return crud.get_user_progress(db, current_user.id)

@app.post("/modules/{module_id}/complete", response_model=schemas.GenericResponse)
def complete_module(module_id: int, db: Session = Depends(get_db),
                    current_user: User = Depends(get_authenticated_user)):
    """Mark module as completed and unlock next content (authenticated users only)"""
    # Mark module as completed
    db_module = crud.update_module(db, module_id, completed=True)
    if not db_module:
        raise HTTPException(status_code=404, detail="Module not found")
    
    # Unlock next content for this user
    crud.unlock_next_content(db, module_id, user_id=current_user.id)
    
    return {"message": "Module completed successfully"}

@app.post("/activities/{activity_id}/submit", response_model=schemas.Activity)
def submit_activity(activity_id: int, score: float, db: Session = Depends(get_db),
                    current_user: User = Depends(get_authenticated_user)):
    """Submit activity with score (authenticated users only)"""
    db_activity = crud.update_activity(db, activity_id, completed=True, score=score)
    if not db_activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    return db_activity

# ==================== ADMIN SPECIFIC ENDPOINTS ====================

@app.get("/admin/stats", response_model=dict)
def get_admin_stats(admin_user: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    """Get system statistics (admin only)"""
    total_users = len(crud.get_users(db, limit=10000))
    total_courses = len(crud.get_courses(db, limit=10000))
    total_modules = len(crud.get_modules(db, limit=10000))
    total_resources = len(crud.get_resources(db, limit=10000))
    total_videos = len(crud.get_videos(db, limit=10000))
    total_pdfs = len(crud.get_pdfs(db, limit=10000))
    total_activities = len(crud.get_activities(db, limit=10000))
    
    return {
        "total_users": total_users,
        "total_courses": total_courses,
        "total_modules": total_modules,
        "total_resources": total_resources,
        "total_videos": total_videos,
        "total_pdfs": total_pdfs,
        "total_activities": total_activities
    }

@app.post("/admin/users/{user_id}/make-admin", response_model=schemas.GenericResponse)
def make_user_admin(user_id: int, db: Session = Depends(get_db),
                    admin_user: User = Depends(get_admin_user)):
    """Make a user admin (admin only)"""
    db_user = crud.get_user(db, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    db_user.is_admin = True
    db.commit()
    return {"message": f"User {db_user.email} is now an admin"}

@app.post("/admin/users/{user_id}/remove-admin", response_model=schemas.GenericResponse)
def remove_user_admin(user_id: int, db: Session = Depends(get_db),
                      admin_user: User = Depends(get_admin_user)):
    """Remove admin privileges from a user (admin only)"""
    db_user = crud.get_user(db, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if db_user.id == admin_user.id:
        raise HTTPException(status_code=400, detail="Cannot remove admin privileges from yourself")
    
    db_user.is_admin = False
    db.commit()
    return {"message": f"Admin privileges removed from user {db_user.email}"}

# ==================== HEALTH CHECK ====================

@app.get("/health", response_model=schemas.GenericResponse)
def health_check():
    """Health check endpoint (public access)"""
    return {"message": "API is running successfully"}

@app.middleware("http")
async def authentication_middleware(request: Request, call_next):
    # List of public endpoints that don't require authentication
    public_paths = [
        "/docs",
        "/redoc",
        "/openapi.json",
        "/health",
        "/register",
        "/login",
        "/static",
    ]
    
    # Check if the path is public
    if any(request.url.path.startswith(path) for path in public_paths):
        return await call_next(request)
    
    # Check for authentication token
    token = request.cookies.get("access_token")
    if not token and not request.url.path.startswith("/admin"):
        return JSONResponse(
            status_code=401,
            content={
                "message": "Not authenticated. Please login at /login or register at /register",
                "success": False
            }
        )
    
    return await call_next(request)

# Error handler for unauthorized access
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    if exc.status_code == 401:
        return JSONResponse(
            status_code=401,
            content={
                "message": "Not authenticated. Please login at /login or register at /register",
                "success": False
            }
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail, "success": False}
    )

@app.post("/modules/{module_id}/user-progress", response_model=schemas.ModuleResponse)
async def update_user_module_progress(
    module_id: int,
    progress: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_authenticated_user)
):
    """
    Update user's progress for a specific module
    
    Args:
        module_id: ID of the module
        progress: Dictionary containing "completed" status
    """
    # Verify module exists
    db_module = crud.get_module(db, module_id)
    if not db_module:
        raise HTTPException(status_code=404, detail="Module not found")
    
    # Get or create user progress
    user_progress = db.query(UserModuleProgress).filter(
        UserModuleProgress.user_id == current_user.id,
        UserModuleProgress.module_id == module_id
    ).first()
    
    if not user_progress:
        user_progress = UserModuleProgress(
            user_id=current_user.id,
            module_id=module_id,
            locked=False,
            completed=False
        )
        db.add(user_progress)
    
    # Update progress
    user_progress.completed = progress.get("completed", user_progress.completed)
    user_progress.last_accessed = datetime.utcnow()
    
    # If module is completed, unlock next module
    if user_progress.completed:
        next_module = db.query(Module).filter(
            and_(
                Module.course_id == db_module.course_id,
                Module.id > module_id
            )
        ).order_by(Module.id).first()
        
        if next_module:
            next_progress = db.query(UserModuleProgress).filter(
                UserModuleProgress.user_id == current_user.id,
                UserModuleProgress.module_id == next_module.id
            ).first()
            
            if not next_progress:
                next_progress = UserModuleProgress(
                    user_id=current_user.id,
                    module_id=next_module.id,
                    locked=False,
                    completed=False
                )
                db.add(next_progress)
            else:
                next_progress.locked = False
    
    db.commit()
    
    # Return updated module with progress
    return {
        "id": db_module.id,
        "name": db_module.name,
        "description": db_module.description,
        "background_image": db_module.background_image,
        "course_id": db_module.course_id,
        "user_progress": {
            "locked": user_progress.locked,
            "completed": user_progress.completed,
            "last_accessed": user_progress.last_accessed.isoformat() if user_progress.last_accessed else None
        }
    }
@app.post("/modules/{module_id}/complete", response_model=schemas.StudentScore)
async def complete_module(
    module_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_authenticated_user)
):
    """Complete a module and calculate total score from activities"""
    
    # Verify module exists
    db_module = crud.get_module(db, module_id)
    if not db_module:
        raise HTTPException(status_code=404, detail="Module not found")
    
    # Calculate and save score
    student_score = crud.calculate_and_save_student_score(
        db, current_user.id, module_id
    )
    
    if not student_score:
        raise HTTPException(
            status_code=400, 
            detail="No completed activities found for this module"
        )
    
    return student_score

@app.get("/students/scores", response_model=List[schemas.StudentScore])
async def get_student_scores(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_authenticated_user)
):
    """Get all scores for the current student"""
    return crud.get_student_scores(db, current_user.id)

@app.get("/modules/{module_id}/scores", response_model=List[schemas.StudentScore])
async def get_module_scores(
    module_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_authenticated_user)
):
    """Get all student scores for a module"""
    return crud.get_module_scores(db, module_id)

@app.post("/modules/{module_id}/complete-progress", response_model=schemas.ModuleResponse)
async def complete_module_and_progress(
    module_id: int,
    progress: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_authenticated_user)
):
    """
    Update user's progress for a specific module and calculate total score if completed.
    """
    # Verify module exists
    db_module = crud.get_module(db, module_id)
    if not db_module:
        raise HTTPException(status_code=404, detail="Module not found")
    
    # Get or create user progress
    user_progress = db.query(UserModuleProgress).filter(
        UserModuleProgress.user_id == current_user.id,
        UserModuleProgress.module_id == module_id
    ).first()
    
    if not user_progress:
        user_progress = UserModuleProgress(
            user_id=current_user.id,
            module_id=module_id,
            locked=False,
            completed=False
        )
        db.add(user_progress)
        db.commit()
        db.refresh(user_progress)
    
    # Update progress
    completed_now = progress.get("completed", user_progress.completed)
    user_progress.completed = completed_now
    user_progress.last_accessed = datetime.utcnow()
    db.commit()
    db.refresh(user_progress)
    
    student_score = None
    # If module is completed, unlock next module and calculate score
    if completed_now:
        # Unlock next module
        next_module = db.query(Module).filter(
            Module.course_id == db_module.course_id,
            Module.id > module_id
        ).order_by(Module.id).first()
        
        if next_module:
            next_progress = db.query(UserModuleProgress).filter(
                UserModuleProgress.user_id == current_user.id,
                UserModuleProgress.module_id == next_module.id
            ).first()
            
            if not next_progress:
                next_progress = UserModuleProgress(
                    user_id=current_user.id,
                    module_id=next_module.id,
                    locked=False,
                    completed=False
                )
                db.add(next_progress)
            else:
                next_progress.locked = False
            db.commit()
        
        # Calculate and save score
        student_score = crud.calculate_and_save_student_score(
            db, current_user.id, module_id
        )
    
    # Build response
    response = {
        "id": db_module.id,
        "name": db_module.name,
        "description": db_module.description,
        "background_image": db_module.background_image,
        "course_id": db_module.course_id,
        "user_progress": {
            "locked": user_progress.locked,
            "completed": user_progress.completed,
            "last_accessed": user_progress.last_accessed.isoformat() if user_progress.last_accessed else None
        }
    }
    # Optionally include score if completed
    if student_score:
        response["score"] = {
            "total_score": student_score.total_score,
            "completed_at": student_score.completed_at.isoformat()
        }
    return response

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
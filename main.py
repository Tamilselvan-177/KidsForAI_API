# main.py - Complete FastAPI application with CRUD endpoints
from fastapi import UploadFile,File,Path,Body
import shutil
from googletrans import Translator# import argostranslate.package, argostranslate.translate

from fastapi import Query
from typing import List
import glob
from wtforms import StringField, PasswordField,BooleanField
from wtforms.validators import DataRequired
from sqladmin.forms import Form
from models import Course, StudentScore, Activity, Resource, Module, User, UserCourseProgress, UserModuleProgress,Video
import uuid
from wtforms import FileField  # <== this is from WTForms, SQLAdmin uses it under the hood
from sqlalchemy.orm import Session
import os
from fastapi import FastAPI, Depends, HTTPException, Response, Request, Query
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from database import SessionLocal, engine, Base
import crud, schemas
from auth import create_access_token, verify_token
from typing import List, Optional
from sqlalchemy import and_, asc
from datetime import datetime
from models import StudentScore
from fastapi.staticfiles import StaticFiles
from starlette_admin import BaseAdmin

# SQLAdmin imports
from sqlalchemy import create_engine
from sqladmin import Admin, ModelView,action
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request as StarletteRequest
from starlette.responses import RedirectResponse
from sqladmin.forms import FileField
from fastapi import UploadFile
from fastapi.responses import FileResponse,HTMLResponse


# Import your existing models
from models import User, Course, Module, Video, Activity, PDF, Resource, UserModuleProgress

app = FastAPI(title="Learning Management System API", version="1.0.0")
# Define upload directory
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Mount static files to serve uploaded files
app.mount("/files", StaticFiles(directory=UPLOAD_DIR), name="files")

app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="files")
# Serve the 'videos' folder at /videos
app.mount("/videos", StaticFiles(directory="videos"), name="videos")
app.mount("/pdf", StaticFiles(directory="pdf"), name="pdf")


# CORS for Flutter local dev
app.add_middleware(
    CORSMiddleware,
 allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:8080",
        "http://192.168.137.154:8000",  # Example
        "http://192.168.1.10:8000",     # <-- Add your actual local IP here
        "http://192.168.1.10:3000" ,
         
    ],    
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
# Initialize the database
# Create SQLAlchemy tables
Base.metadata.create_all(bind=engine)

# Authentication backend for admin
class AdminAuth(AuthenticationBackend):
    async def login(self, request: StarletteRequest) -> bool:
        form = await request.form()
        username, password = form["username"], form["password"]
        
        if authenticate_user(username, password):
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
class UserForm(Form):
    email = StringField("Email", validators=[DataRequired()])
    password = StringField("Password", validators=[DataRequired()])
    is_admin = BooleanField("Is Admin")
    def validate(self, extra_validators=None):
        # Run default validations first
        if not super().validate(extra_validators):
            return False

        # Automatically hash password if not hashed
        if self.password.data and not self.password.data.startswith("$2b$"):
            self.password.data = crud.pwd_context.hash(self.password.data)
        
        return True
# Admin views
class UserAdmin(ModelView, model=User):
    form = UserForm
    column_list = [User.id, User.email]
    # column_exclude_list = [User.password]  # Hide password from admin list view
    # form_excluded_columns = [User.password]  # Hide password from admin form unless handled separately
    save_as=True
    name = "User"
    name_plural = "Users"
    icon = "fa-solid fa-user"
    can_delete = True
    
    # Fix 1: Remove the 'iscreated' parameter - it's likely not expected
    async def on_model_create(self, data, request):
        print("Enter into on_model_create")
        if "password" in data and not data["password"].startswith("$2b$"):
            data["password"] = crud.hash_password(data["password"])
        return data  # Make sure to return the modified data

    # Fix 2: Complete the print statement and ensure proper return
    async def on_model_update(self, data, request, model):
        print("Enter into on_model_update")
        
        if "password" in data:
            # Only re-hash if the password changed and is not already hashed
            if data["password"] != model.password and not data["password"].startswith("$2b$"):
                data["password"] = crud.hash_password(data["password"])
        return data  # Make sure to return the modified data

# Alternative approach - try these method names if the above don't work:
class UserAdminAlternative(ModelView, model=User):
    column_list = [User.id, User.email]
    name = "User"
    name_plural = "Users"
    icon = "fa-solid fa-user"
    can_delete = True
    form_columns = ["is_admin", "email", "password"]
    
    # Try these alternative method names:
    async def before_create(self, request, data, **kwargs):
        print("Enter into before_create")
        if "password" in data and not data["password"].startswith("$2b$"):
            data["password"] = crud.hash_password(data["password"])
        return data

    async def before_update(self, request, data, model, **kwargs):
        print("Enter into before_update")
        if "password" in data:
            if data["password"] != model.password and not data["password"].startswith("$2b$"):
                data["password"] = crud.hash_password(data["password"])
        return data

    # Or try these:
    async def on_create(self, data, request):
        print("Enter into on_create")
        if "password" in data and not data["password"].startswith("$2b$"):
            data["password"] = crud.hash_password(data["password"])
        return data

    async def on_update(self, data, request, model):
        print("Enter into on_update")
        if "password" in data:
            if data["password"] != model.password and not data["password"].startswith("$2b$"):
                data["password"] = crud.hash_password(data["password"])
        return data
class CourseAdmin(ModelView, model=Course):
    column_list = [Course.id, Course.name]
    name = "Course"
    name_plural = "Courses"  
    icon = "fa-solid fa-book"

class ModuleAdmin(ModelView, model=Module):
    column_list = [Module.id, Module.name, Module.description, Module.locked, 
                  Module.completed, Module.course_id,Module.score]
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
    column_list = [Activity.id, Activity.name, Activity.completed, Activity.resource_id]
    name = "Activity"
    name_plural = "Activities"
    icon = "fa-solid fa-tasks"


class PDFAdmin(ModelView, model=PDF):
    name = "PDF"
    name_plural = "PDFs"
    icon = "fa-solid fa-file-pdf"
    column_list = [PDF.id, PDF.title, PDF.url]
    print("PDFAdmin initialized with custom URL formatter")

    @action("upload", "Upload PDF", "GO TO UPLOAD")
    async def go_to_upload(self, request: Request):
        # Redirect to /upload (custom route in FastAPI app)
        base_url = str(request.base_url).rstrip('/')+"/upload"
        return RedirectResponse(url=base_url)
    # form_overrides = {
    #     "url": FileField
    # }
    # async def on_model_create(self, data, request: Request):
    #     form = await request.form()
    #     file = form.get("url")
    #     print(file)

    #     if not file or not file.filename.endswith(".pdf"):
    #         raise ValueError("Only PDF files are allowed")
        
    #     title = form.get("title")
    #     resource_id = form.get("resource_id")
    #     resource_id = int(resource_id) if resource_id else None
    #     print(f"Creating PDF with title: {title}, resource_id: {resource_id}")
    #     print(f"File: {file.filename}, Size: {file.size} bytes" )
    #     # ✅ Let serialize_field_value handle saving the file
    #     return PDF(
    #         title=title,
    #         url=file,  # UploadFile here!
    #         resource_id=resource_id,
    #         thumbnail=None
    #     )

    
    # async def serialize_field_value(self, value, field_name: str, request: Request):
    #     """Convert UploadFile objects to file paths before database operations"""
    #     if field_name == "url" and isinstance(value, UploadFile):
    #         if not value.filename or not value.filename.endswith(".pdf"):
    #             raise ValueError("Only PDF files are allowed")
            
    #         # Generate unique filename to avoid conflicts
    #         unique_filename = f"{uuid.uuid4().hex}_{value.filename}"
    #         file_path = os.path.join(UPLOAD_DIR, unique_filename)
            
    #         # Save the uploaded PDF file
    #         with open(file_path, "wb") as f:
    #             shutil.copyfileobj(value.file, f)
            
    #         return file_path
        
    #     return await super().serialize_field_value(value, field_name, request)
    
    # async def on_model_change(self, data, model, is_created: bool, request: Request):
    #     """Clean up old files when updating"""
    #     if not is_created and hasattr(model, 'url'):
    #         # Get the form to check if a new file was uploaded
    #         form = await request.form()
    #         new_file = form.get("url")
            
    #         # If a new file was uploaded and we have an old file, delete it
    #         if (new_file and isinstance(new_file, UploadFile) and 
    #             new_file.filename and model.url and os.path.exists(model.url)):
    #             try:
    #                 os.remove(model.url)
    #             except OSError:
    #                 pass  # File might not exist or be accessible
    
    
class UserProgressAdmin(ModelView, model=UserModuleProgress):
    column_list = [
        UserModuleProgress.id, 
        UserModuleProgress.user_id, 
        UserModuleProgress.module_id, 
        UserModuleProgress.locked, 
        UserModuleProgress.completed,
        UserModuleProgress.last_accessed,
    ]
    can_create = False  # Progress is created automatically
    name = "User Progress"
    name_plural = "User Progress"
    icon = "fa-solid fa-chart-line"
class ClassProgressAdmin(ModelView, model=UserCourseProgress):
    column_list = [
        UserCourseProgress.id, 
        UserCourseProgress.user_id, 
        UserCourseProgress.course_id, 
        UserCourseProgress.locked, 
        UserCourseProgress.completed,
        UserCourseProgress.last_accessed,
    ]
    can_create = False  # Progress is created automatically
    name = "Class Progress"
    name_plural = "Class Progress"
    icon = "fa-solid fa-school"
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
admin.add_view(ClassProgressAdmin)

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

def authenticate_user(username: str, password: str):
    db = SessionLocal() 
    user = db.query(User).filter(User.email == username).first()
    if not user:
        return None
    print(f"Authenticating user: {user.email}, is_admin: {user.is_admin}")
    
    if not crud.verify_password(password, user.password) and user.is_admin:
        return None
    # token = create_access_token({"sub": user.email})

    # # ✅ Set cookie
    # response.set_cookie(
    #     key="access_token",
    #     value=token,
    #     httponly=True,
    #     max_age=365*24*60*60,
    #     expires=365*24*60*60,
    #     samesite="Lax",
    #     secure=False
    # )
    
    return user
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

# ==================== USER CRUD ENDPOINTS ==================
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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_authenticated_user)
):
    """Get all courses with user-specific progress"""
    first_course = db.query(Course).order_by(Course.id.asc()).first()

    if first_course:
        # Check if course progress already exists
        existing_course_progress = db.query(UserCourseProgress).filter_by(
            user_id=current_user.id,
            course_id=first_course.id
        ).first()

        # If not already created, unlock course
        if not existing_course_progress:
            course_progress = UserCourseProgress(
                user_id=current_user.id,
                course_id=first_course.id,
                locked=False,
                completed=False
            )
            db.add(course_progress)

        # Get the first module in the first course
        first_module = (
            db.query(Module)
            .filter(Module.course_id == first_course.id)
            .order_by(Module.id.asc())
            .first()
        )

        if first_module:
            # Check if module progress already exists
            existing_module_progress = db.query(UserModuleProgress).filter_by(
                user_id=current_user.id,
                module_id=first_module.id
            ).first()

            # If not already created, unlock module
            if not existing_module_progress:
                module_progress = UserModuleProgress(
                    user_id=current_user.id,
                    module_id=first_module.id,
                    locked=False,
                    completed=False
                )
                db.add(module_progress)

        db.commit()
    return crud.get_courses_with_progress(db, current_user.id)

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
    last_module_completed = modules[-1]["user_progress"]["completed"]

    if last_module_completed:
        print("Last module completed, unlocking next course if available")
        # Unlock the next course if available
        next_course = (
            db.query(Course)
            .filter(Course.id > course_id)
            .order_by(asc(Course.id))
            .first()
        )

        if next_course:
            progress = (
                db.query(UserCourseProgress)
                .filter_by(user_id=current_user.id, course_id=next_course.id)
                .first()
            )

            if progress and progress.locked:
                progress.locked = False
                db.commit()

            elif not progress:
                # If no progress entry exists yet, create one and unlock
                new_progress = UserCourseProgress(
                    user_id=current_user.id,
                    course_id=next_course.id,
                    locked=False,
                    completed=False
                )
                db.add(new_progress)
                db.commit()
            first_module = (
            db.query(Module)
            .filter(Module.course_id == next_course.id)
            .order_by(Module.id.asc())  # or Module.order.asc() if exists
            .first()
        )

        if first_module:
            module_progress = (
                db.query(UserModuleProgress)
                .filter_by(user_id=current_user.id, module_id=first_module.id)
                .first()
            )

            if not module_progress:
                new_module_progress = UserModuleProgress(
                    user_id=current_user.id,
                    module_id=first_module.id,
                    locked=False,
                    completed=False
                )
                db.add(new_module_progress)
                db.commit()
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

@app.post("/modules/{module_id}/complete", response_model=schemas.StudentScore)
def complete_module(module_id: int, db: Session = Depends(get_db),
                    current_user: User = Depends(get_authenticated_user)):
    """Mark module as completed and unlock next content (authenticated users only)"""
    # Mark module as completed
    print(f"Completing module {module_id} for user {current_user.id}")
    db_module = crud.update_module(db, module_id, completed=True,user_id=current_user.id)
    if not db_module:
        raise HTTPException(status_code=404, detail="Module not found")
    
    # Unlock next content for this user
    crud.unlock_next_content(db, module_id, user_id=current_user.id)
    student_score = db.query(StudentScore).filter(
        StudentScore.user_id == current_user.id,
        StudentScore.module_id == module_id
    ).first()
    
    return student_score if student_score else {"message": "Module completed successfully"}
    

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
    public_paths = [
        "/docs",
        "/redoc",
        "/openapi.json",
        "/health",
        "/register",
        "/login",
        "/static",
        "/videos",   # <-- add this
        "/pdf",      # <-- add this
        "uploads",
        "/files",
        "upload",
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

## =================== PDF UPLOAD ENDPOINT ====================

from fastapi import Request

@app.post("/upload-pdf")
async def upload_pdf(request: Request, file: UploadFile = File(...)):
    """Upload PDF file and return full file URL"""
    try:
        print(f"Received file: {file.filename}, content_type: {file.content_type}")
        
        # Validate file type
        if not file.filename or not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are allowed")
        
        # Generate unique filename
        unique_filename = f"{uuid.uuid4().hex}_{file.filename}"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)
        
        print(f"Saving file to: {file_path}")
        
        # Read file content
        content = await file.read()
        
        # Save the file
        with open(file_path, "wb") as f:
            f.write(content)
        
        file_size = os.path.getsize(file_path)
        print(f"File saved successfully. Size: {file_size} bytes")
        
        # Get base URL with IP or domain
        base_url = str(request.base_url).rstrip('/')
        full_file_url = f"{base_url}/uploads/{unique_filename}"
        
        return {
            "success": True,
            "filename": unique_filename,
            "original_name": file.filename,
            "file_path": file_path,
            "file_url": full_file_url,
            "size": file_size,
            "message": "File uploaded successfully"
        }

    except Exception as e:
        print("Upload failed:", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/deletefile/{filename}")
async def delete_upload(filename: str):
    """Delete a specific uploaded file"""
    try:
        # Security validation
        # if not filename.replace('-', '').replace('_', '').replace('.', '').isalnum():
        #     raise HTTPException(status_code=400, detail="Invalid filename")

        file_path = os.path.join(UPLOAD_DIR, filename)
        print(file_path)

        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found")

        os.remove(file_path)
        return {
            "success": True,
            # "filename": file_path,
            "message": "File deleted successfully"
        }
        return 
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error deleting file {filename}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Serve files manually instead of using StaticFiles to avoid conflicts
@app.get("/files/{filename}")
async def serve_file(filename: str):
    """Serve uploaded files"""
    try:
        # Security: only allow alphanumeric, dots, hyphens, underscores
        if not filename.replace('-', '').replace('_', '').replace('.', '').isalnum():
            raise HTTPException(status_code=400, detail="Invalid filename")
        
        file_path = os.path.join(UPLOAD_DIR, filename)
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found")
        
        return FileResponse(
            file_path,
            media_type='application/pdf',
            filename=filename
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error serving file {filename}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error serving file")



@app.get("/uploads")
async def list_uploads(request: Request):
    """List all uploaded PDF files with metadata"""
    try:
        pattern = os.path.join(UPLOAD_DIR, "*_*.pdf")  # matches your naming scheme
        files = []
        for path in glob.glob(pattern):
            filename = os.path.basename(path)
            stat = os.stat(path)
            base_url = str(request.base_url).rstrip('/')
            files.append({
                "filename": filename,
                "original_name": "_".join(filename.split("_")[1:]),  # best effort
                
                "file_url": f"{base_url}/files/{filename}",  # adjust base if needed
                "size": stat.st_size,
                "uploaded_at": stat.st_ctime
            })
        return {"success": True, "files": files}
    except Exception as e:
        print("Error listing uploads:", e)
        raise HTTPException(status_code=500, detail="Could not list uploads")


@app.get("/upload")
async def upload_page():
    """Serve the upload page"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>PDF Upload</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
            .upload-zone { 
                border: 2px dashed #ccc; 
                border-radius: 10px; 
                padding: 50px; 
                text-align: center; 
                margin: 20px 0; 
                transition: all 0.3s ease;
            }
            .upload-zone:hover { border-color: #007bff; background-color: #f8f9fa; }
            .upload-zone.dragover { border-color: #007bff; background-color: #e3f2fd; }
            .btn { 
                background: #007bff; 
                color: white; 
                padding: 10px 20px; 
                border: none; 
                border-radius: 5px; 
                cursor: pointer; 
            }
            .btn:hover { background: #0056b3; }
            .file-list { margin-top: 20px; }
            .file-item { 
                background: #f8f9fa; 
                padding: 15px; 
                margin: 10px 0; 
                border-radius: 5px; 
                border-left: 4px solid #007bff; 
            }
            .file-url { 
                background: #e9ecef; 
                padding: 5px 10px; 
                border-radius: 3px; 
                font-family: monospace; 
                font-size: 14px; 
                margin: 5px 0; 
                word-break: break-all;
            }
            .copy-btn { 
                background: #28a745; 
                color: white; 
                border: none; 
                padding: 5px 15px; 
                border-radius: 3px; 
                cursor: pointer; 
                font-size: 12px; 
            }
            .error { 
                background: #f8d7da; 
                color: #721c24; 
                padding: 15px; 
                border-radius: 5px; 
                margin: 10px 0; 
            }
        </style>
    </head>
    <body>
        <h1>📄 PDF Upload Manager</h1>
        <p>Upload PDF files and get URLs for your admin panel</p>
        
        <div class="upload-zone" id="uploadZone">
            <h3>Drop PDF files here or click to browse</h3>
            <input type="file" id="fileInput" multiple accept=".pdf" style="display: none;">
            <button class="btn" onclick="document.getElementById('fileInput').click()">
                Choose PDF Files
            </button>
        </div>
        
        <div class="file-list" id="fileList"></div>
      <script>
    const uploadZone = document.getElementById('uploadZone');
    const fileInput = document.getElementById('fileInput');
    const fileList = document.getElementById('fileList');

    // Helper to get base URL dynamically
    const baseUrl = window.location.origin;

    uploadZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadZone.classList.add('dragover');
    });

    uploadZone.addEventListener('dragleave', () => {
        uploadZone.classList.remove('dragover');
    });

    uploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadZone.classList.remove('dragover');
        handleFiles(Array.from(e.dataTransfer.files));
    });

    fileInput.addEventListener('change', (e) => {
        handleFiles(Array.from(e.target.files));
    });

    async function handleFiles(files) {
        const pdfFiles = files.filter(file =>
            file.type === 'application/pdf' ||
            file.name.toLowerCase().endsWith('.pdf')
        );

        if (pdfFiles.length === 0) {
            showError('Please select PDF files only');
            return;
        }

        for (const file of pdfFiles) {
            await uploadFile(file);
        }
        await refreshFileList();
    }

    async function uploadFile(file) {
        console.log('Uploading:', file.name, 'Size:', file.size);

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('/upload-pdf', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();
            console.log('Result:', result);

            if (result.success) {
                addFileToList(result);
            } else {
                throw new Error(result.detail || 'Upload failed');
            }
        } catch (error) {
            console.error('Upload error:', error);
            showError('Upload failed: ' + error.message);
        }
    }

    function addFileToList(fileInfo, prepend = false) {
        const fileItem = document.createElement('div');
        fileItem.className = 'file-item';
        fileItem.dataset.filename = fileInfo.filename;

        fileItem.innerHTML = `
            <h4>✅ ${fileInfo.original_name || fileInfo.filename}</h4>
            <p>Size: ${(fileInfo.size / 1024).toFixed(1)} KB</p>
            <div class="file-url">${fileInfo.file_url}</div>
            <div style="margin-top:8px;">
                <button class="copy-btn" onclick="copyToClipboard('${fileInfo.file_url}')">
                    Copy URL
                </button>
                <a href="${fileInfo.file_url}" target="_blank" style="margin-left:10px;">View PDF</a>
                <button class="copy-btn" style="margin-left:10px; background:#dc3545;" onclick="confirmDelete('${fileInfo.filename}', this)">
                    Delete
                </button>
            </div>
        `;
        if (prepend) fileList.prepend(fileItem);
        else fileList.appendChild(fileItem);
    }

    function showError(message) {
        const errorItem = document.createElement('div');
        errorItem.className = 'error';
        errorItem.innerHTML = `❌ ${message}`;
        fileList.appendChild(errorItem);
        setTimeout(() => errorItem.remove(), 5000);
    }

    function copyToClipboard(text) {
        navigator.clipboard.writeText(text).then(() => {
            alert('URL copied to clipboard!');
        }).catch(() => {
            const textArea = document.createElement('textarea');
            textArea.value = text;
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
            alert('URL copied to clipboard!');
        });
    }

    async function refreshFileList() {
        try {
            const res = await fetch('/uploads');
            const data = await res.json();
            if (data.success && Array.isArray(data.files)) {
                fileList.innerHTML = '';
                if (data.files.length === 0) {
                    fileList.innerHTML = '<p>No uploaded PDFs yet.</p>';
                    return;
                }
                data.files
                    .sort((a, b) => b.uploaded_at - a.uploaded_at)
                    .forEach(f => addFileToList(f));
            } else {
                showError('Failed to load uploaded files');
            }
        } catch (e) {
            console.error('Error fetching uploads:', e);
            showError('Could not fetch uploads');
        }
    }

    function confirmDelete(filename, btn) {
        if (!confirm(`Delete "${filename}"? This cannot be undone.`)) return;
        deleteFile(filename, btn);
    }

    async function deleteFile(filename, btn) {
        try {
           const res = await fetch(`/deletefile/${encodeURIComponent(filename)}`, {
    method: 'GET'
    
});           console.log(`Deleting file: ${encodeURIComponent(filename)}`);


            if (res.headers.get('content-type')?.includes('application/json')) {
    const result = await res.json();
    if (result.success) {
        alert(`Deleted ${filename}`);
        document.querySelector(`.file-item[data-filename="${filename}"]`)?.remove();
    } else {
        showError('Delete failed: ' + result.detail || 'Unknown error');
    }
} else {
    const text = await res.text();
    showError('Delete failed (non-JSON response): ' + text.slice(0, 100));
}
            
        } catch (e) {
            console.error('Delete error:', e);
            showError('Delete failed: ' + e.message);
        }
    }

    // Initial load
    window.addEventListener('DOMContentLoaded', refreshFileList);
</script>


    </body>
    </html>
    """
    return HTMLResponse(content=html_content)
@app.post("/translator")
async def translators(text: str = Body(..., embed=True)):
    translator = Translator()
    result = await translator.translate(text, src="en", dest="ta")
    return {"translated_text": result.text}
@app.get("/")
async def root():
    return {"message": "PDF Upload Server", "upload_dir": UPLOAD_DIR}

# IMPORTANT: Put the StaticFiles mount at the very end, or remove it entirely
# since we're handling file serving manually with the /files/{filename} route above
# app.mount("/files", StaticFiles(directory=UPLOAD_DIR), name="files")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
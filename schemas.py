# schemas.py - Pydantic schemas for API validation

from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional, List
from datetime import datetime

# ==================== USER SCHEMAS ====================

class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str
    is_admin: bool = False

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    is_admin: Optional[bool] = None

class User(UserBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    is_admin: bool = False

# ==================== BASIC SCHEMAS (NO NESTED RELATIONS) ====================

class CourseBase(BaseModel):
    name: str

class CourseCreate(CourseBase):
    pass

class CourseUpdate(BaseModel):
    name: Optional[str] = None

class CourseSimple(CourseBase):
    """Course without nested modules to avoid circular references"""
    model_config = ConfigDict(from_attributes=True)
    id: int

class ModuleBase(BaseModel):
    name: str
    description: Optional[str] = None
    background_image: Optional[str] = None

class ModuleCreate(ModuleBase):
    course_id: int

class ModuleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    background_image: Optional[str] = None
    locked: Optional[bool] = None
    completed: Optional[bool] = None

class ModuleSimple(ModuleBase):
    """Module without nested relations to avoid circular references"""
    model_config = ConfigDict(from_attributes=True)
    id: int
    course_id: int

class ResourceBase(BaseModel):
    name: str
    module_id: int

class ResourceCreate(ResourceBase):
    module_id: int

class ResourceUpdate(BaseModel):
    name: Optional[str] = None
    locked: Optional[bool] = None
    completed: Optional[bool] = None

class ResourceSimple(ResourceBase):
    """Resource without nested relations"""
    model_config = ConfigDict(from_attributes=True)
    id: int
    module_id: int

# ==================== CONTENT SCHEMAS (NO BACK REFERENCES) ====================

class VideoBase(BaseModel):
    title: str
    thumbnail: Optional[str] = None
    url: str

class VideoCreate(VideoBase):
    resource_id: int

class VideoUpdate(BaseModel):
    title: Optional[str] = None
    thumbnail: Optional[str] = None
    url: Optional[str] = None

class Video(VideoBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    resource_id: int

class ActivityBase(BaseModel):
    name: str
    completed: bool = False
    score: float = 0.0

class ActivityCreate(ActivityBase):
    resource_id: int

class ActivityUpdate(BaseModel):
    name: Optional[str] = None
    completed: Optional[bool] = None
    score: Optional[float] = None

class Activity(ActivityBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    resource_id: int

class PDFBase(BaseModel):
    title: str
    thumbnail: Optional[str] = None
    url: str

class PDFCreate(PDFBase):
    resource_id: int

class PDFUpdate(BaseModel):
    title: Optional[str] = None
    thumbnail: Optional[str] = None
    url: Optional[str] = None

class PDF(PDFBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    resource_id: int

# ==================== NESTED SCHEMAS (SAFE NESTING) ====================

class Resource(ResourceBase):
    id: int
    videos: List[Video] = []
    pdfs: List[PDF] = []
    activities: List[Activity] = []

    class Config:
        orm_mode = True

class Module(ModuleBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    course_id: int
    # resources: List[Resource] = []
class ModuleResource(ModuleBase):
    model_config = ConfigDict(from_attributes=False)
    id: int
    course_id: int
    resources: List[Resource] = []

class Course(CourseBase):
    """Course with all nested content"""
    model_config = ConfigDict(from_attributes=True)
    id: int
    description: str



# ==================== PROGRESS SCHEMAS ====================

class ResourceProgress(BaseModel):
    resource_id: int
    resource_name: str
    locked: bool
    completed: bool

class ModuleProgress(BaseModel):
    module_id: int
    module_name: str
    locked: bool
    completed: bool
    score: float
    resources: List[ResourceProgress]

class CourseProgress(BaseModel):
    course_id: int
    course_name: str
    modules: List[ModuleProgress]

# ==================== SPECIALIZED SCHEMAS ====================

class VideoWithResource(Video):
    """Video with resource info"""
    resource: ResourceSimple

class ActivityWithResource(Activity):
    """Activity with resource info"""
    resource: ResourceSimple

class PDFWithResource(PDF):
    """PDF with resource info"""
    resource: ResourceSimple

class ResourceWithModule(Resource):
    """Resource with module info"""
    module: ModuleSimple

class ModuleWithCourse(Module):
    """Module with course info"""
    course: CourseSimple

# ==================== RESPONSE SCHEMAS ====================

class superuser_login(BaseModel):
    email: EmailStr
    

    class Config:
        orm_mode = True

class GenericResponse(BaseModel):
    message: str
    cookie: str
    success: bool = True

class ErrorResponse(BaseModel):
    message: str
    success: bool = False

class PaginatedResponse(BaseModel):
    items: List[dict]
    total: int
    page: int
    per_page: int
    has_next: bool
    has_prev: bool

class ModuleBase(BaseModel):
    name: str
    description: Optional[str] = None
    background_image: Optional[str] = None

class ModuleWithProgress(ModuleBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    course_id: int
    locked: bool
    completed: bool
    resources: List[Resource] = []

class ModuleResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    background_image: Optional[str] = None
    course_id: int
    user_progress: dict
    score: Optional[dict] = None  # Optionally include score

    class Config:
        orm_mode = True

class CourseWithProgress(CourseBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    description: Optional[str] = None
    background_image: Optional[str] = None
    user_progress: dict = {
        "locked": True,
        "completed": False,
        "last_accessed": None
    }
    #=========================StudentScore==========================
class StudentScore(BaseModel):
    id: int
    user_id: int
    module_id: int
    total_score: float
    completed_at: datetime

    class Config:
        orm_mode = True
class SpellCheckRequest(BaseModel):
    text: str

class CompleteActivityRequest(BaseModel):
    score:int

class ActivityWithCompletion(BaseModel):
    id: int
    name: str
    resource_id: int
    completed: bool

    class Config:
        orm_mode = True
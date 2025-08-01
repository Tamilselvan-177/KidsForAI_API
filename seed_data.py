from sqlalchemy.orm import Session
from database import SessionLocal
from models import User, Course, Module, Resource, Video, PDF, Activity
from crud import create_user, hash_password

def seed_database():
    db = SessionLocal()
    try:
        # Create users
        users = [
            User(email="admin@example.com", password=hash_password("admin123"), is_admin=True),
            User(email="user1@example.com", password=hash_password("user123"), is_admin=False),
            User(email="user2@example.com", password=hash_password("user123"), is_admin=False),
        ]
        db.bulk_save_objects(users)
        db.commit()

        # Create courses with detailed information
        courses = [
            Course(
                name="Python Programming",
                description="Learn Python from basics to advanced concepts",
                background_image="assets/courses/python-bg.jpg"
            ),
            Course(
                name="Web Development",
                description="Full-stack web development course",
                background_image="assets/courses/web-bg.jpg"
            ),
            Course(
                name="Data Science",
                description="Introduction to data science and analytics",
                background_image="assets/courses/data-bg.jpg"
            )
        ]
        db.bulk_save_objects(courses)
        db.commit()

        # Create detailed modules for each course
        python_modules = [
            Module(
                name="Python Basics",
                description="Introduction to Python programming",
                course_id=1,
                background_image="assets/modules/python-basics.jpg"
            ),
            Module(
                name="Object-Oriented Programming",
                description="Learn OOP concepts in Python",
                course_id=1,
                background_image="assets/modules/python-oop.jpg"
            ),
            Module(
                name="Advanced Python",
                description="Advanced Python features and patterns",
                course_id=1,
                background_image="assets/modules/python-advanced.jpg"
            )
        ]

        web_modules = [
            Module(
                name="HTML & CSS",
                description="Web fundamentals",
                course_id=2,
                background_image="assets/modules/web-basics.jpg"
            ),
            Module(
                name="JavaScript",
                description="Interactive web programming",
                course_id=2,
                background_image="assets/modules/javascript.jpg"
            ),
            Module(
                name="Backend Development",
                description="Server-side programming",
                course_id=2,
                background_image="assets/modules/backend.jpg"
            )
        ]

        data_modules = [
            Module(
                name="Data Analysis",
                description="Introduction to data analysis",
                course_id=3,
                background_image="assets/modules/data-analysis.jpg"
            ),
            Module(
                name="Machine Learning",
                description="Basic machine learning concepts",
                course_id=3,
                background_image="assets/modules/machine-learning.jpg"
            ),
            Module(
                name="Data Visualization",
                description="Creating effective visualizations",
                course_id=3,
                background_image="assets/modules/data-viz.jpg"
            )
        ]

        all_modules = python_modules + web_modules + data_modules
        db.bulk_save_objects(all_modules)
        db.commit()

        # Create resources for each module
        for module in all_modules:
            resources = [
                Resource(
                    name=f"Introduction to {module.name}",
                    module_id=module.id,
                    locked=False
                ),
                Resource(
                    name=f"Practice - {module.name}",
                    module_id=module.id,
                    locked=True
                ),
                Resource(
                    name=f"Advanced {module.name}",
                    module_id=module.id,
                    locked=True
                )
            ]
            db.bulk_save_objects(resources)
            db.commit()

            # Add content to each resource
            for resource in resources:
                # Videos
                videos = [
                    Video(
                        title=f"Introduction Video - {resource.name}",
                        url=f"https://example.com/videos/{module.id}/{resource.id}/intro.mp4",
                        thumbnail=f"assets/thumbnails/video_{resource.id}_1.jpg",
                        resource_id=resource.id
                    ),
                    Video(
                        title=f"Tutorial Video - {resource.name}",
                        url=f"https://example.com/videos/{module.id}/{resource.id}/tutorial.mp4",
                        thumbnail=f"assets/thumbnails/video_{resource.id}_2.jpg",
                        resource_id=resource.id
                    )
                ]
                db.bulk_save_objects(videos)

                # PDFs
                pdfs = [
                    PDF(
                        title=f"Study Guide - {resource.name}",
                        url=f"https://example.com/pdfs/{module.id}/{resource.id}/guide.pdf",
                        thumbnail=f"assets/thumbnails/pdf_{resource.id}_1.jpg",
                        resource_id=resource.id
                    ),
                    PDF(
                        title=f"Exercise Sheet - {resource.name}",
                        url=f"https://example.com/pdfs/{module.id}/{resource.id}/exercises.pdf",
                        thumbnail=f"assets/thumbnails/pdf_{resource.id}_2.jpg",
                        resource_id=resource.id
                    )
                ]
                db.bulk_save_objects(pdfs)

                # Activities
                activities = [
                    Activity(
                        name=f"Quiz - {resource.name}",
                        resource_id=resource.id,
                        completed=False,
                        score=0.0
                    ),
                    Activity(
                        name=f"Programming Exercise - {resource.name}",
                        resource_id=resource.id,
                        completed=False,
                        score=0.0
                    )
                ]
                db.bulk_save_objects(activities)

            db.commit()

        print("Sample data has been added successfully!")
        
        # Print summary
        print("\nDatabase Summary:")
        print(f"Users: {db.query(User).count()}")
        print(f"Courses: {db.query(Course).count()}")
        print(f"Modules: {db.query(Module).count()}")
        print(f"Resources: {db.query(Resource).count()}")
        print(f"Videos: {db.query(Video).count()}")
        print(f"PDFs: {db.query(PDF).count()}")
        print(f"Activities: {db.query(Activity).count()}")

    except Exception as e:
        print(f"An error occurred: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
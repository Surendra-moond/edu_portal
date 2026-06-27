import os
import django
import random
from datetime import date, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'student_management.settings')
django.setup()

from apps.accounts.models import CustomUser, Student, Teacher
from apps.courses.models import Course, Enrollment
from apps.academics.models import Attendance, Marks

def seed():
    print("Seeding database...")
    # Clear existing data
    Attendance.objects.all().delete()
    Marks.objects.all().delete()
    Enrollment.objects.all().delete()
    Course.objects.all().delete()
    Student.objects.all().delete()
    Teacher.objects.all().delete()
    # Delete non-superuser users
    CustomUser.objects.filter(is_superuser=False).delete()

    # Create admin
    admin_user, created = CustomUser.objects.get_or_create(
        username='admin',
        email='admin@eduportal.com',
        role=CustomUser.Role.ADMIN,
        defaults={'is_superuser': True, 'is_staff': True}
    )
    if created:
        admin_user.set_password('admin123')
        admin_user.save()
    else:
        admin_user.is_superuser = True
        admin_user.is_staff = True
        admin_user.save()
    print("Admin user created/verified (username: admin, password: admin123)")

    # Departments list
    depts = ['Computer Science', 'Electrical Engineering', 'Mechanical Engineering', 'Physics', 'Mathematics']

    # Create Teachers
    teachers_data = [
        ('t_smith', 'John', 'Smith', 'smith@eduportal.com', 'EMP001', 'Professor', 'Computer Science', 'Ph.D. in CS'),
        ('t_jones', 'Sarah', 'Jones', 'jones@eduportal.com', 'EMP002', 'Assistant Professor', 'Electrical Engineering', 'Ph.D. in EE'),
        ('t_taylor', 'David', 'Taylor', 'taylor@eduportal.com', 'EMP003', 'Lecturer', 'Mechanical Engineering', 'M.Tech in ME'),
        ('t_miller', 'Emily', 'Miller', 'miller@eduportal.com', 'EMP004', 'Professor', 'Physics', 'Ph.D. in Astrophysics'),
        ('t_wilson', 'Michael', 'Wilson', 'wilson@eduportal.com', 'EMP005', 'Professor', 'Mathematics', 'Ph.D. in Pure Math'),
    ]
    
    teachers = []
    for username, fname, lname, email, emp_id, desg, dept, qual in teachers_data:
        u = CustomUser.objects.create_user(
            username=username,
            email=email,
            password='password123',
            first_name=fname,
            last_name=lname,
            role=CustomUser.Role.TEACHER
        )
        t = Teacher.objects.create(
            user=u,
            employee_id=emp_id,
            designation=desg,
            department=dept,
            qualification=qual
        )
        teachers.append(t)
    print(f"Created {len(teachers)} Teachers (password: password123)")

    # Create Courses
    courses_data = [
        ('CS101', 'Introduction to Python', 3, teachers[0]),
        ('CS202', 'Data Structures & Algorithms', 4, teachers[0]),
        ('EE101', 'Basic Electrical Theory', 3, teachers[1]),
        ('ME201', 'Thermodynamics', 3, teachers[2]),
        ('PHY101', 'General Physics I', 4, teachers[3]),
        ('MATH101', 'Calculus I', 4, teachers[4]),
    ]
    
    courses = []
    for code, name, creds, teacher in courses_data:
        c = Course.objects.create(
            course_code=code,
            course_name=name,
            credits=creds,
            teacher=teacher
        )
        courses.append(c)
    print(f"Created {len(courses)} Courses")

    # Create Students
    students_names = [
        ('s_albert', 'Albert', 'Einstein', 'albert@eduportal.com', 'CS', 1),
        ('s_curie', 'Marie', 'Curie', 'marie@eduportal.com', 'Physics', 3),
        ('s_tesla', 'Nikola', 'Tesla', 'nikola@eduportal.com', 'EE', 5),
        ('s_turing', 'Alan', 'Turing', 'alan@eduportal.com', 'CS', 7),
        ('s_ada', 'Ada', 'Lovelace', 'ada@eduportal.com', 'CS', 1),
        ('s_newton', 'Isaac', 'Newton', 'isaac@eduportal.com', 'Mathematics', 5),
        ('s_bohr', 'Niels', 'Bohr', 'niels@eduportal.com', 'Physics', 3),
        ('s_galileo', 'Galileo', 'Galilei', 'galileo@eduportal.com', 'Physics', 7),
        ('s_copernicus', 'Nicolaus', 'Copernicus', 'nicolaus@eduportal.com', 'Mathematics', 1),
        ('s_faraday', 'Michael', 'Faraday', 'faraday@eduportal.com', 'EE', 3),
        ('s_hawking', 'Stephen', 'Hawking', 'stephen@eduportal.com', 'Physics', 7),
        ('s_pasteur', 'Louis', 'Pasteur', 'louis@eduportal.com', 'Mathematics', 1),
    ]

    students = []
    for idx, (username, fname, lname, email, dept_code, sem) in enumerate(students_names):
        u = CustomUser.objects.create_user(
            username=username,
            email=email,
            password='password123',
            first_name=fname,
            last_name=lname,
            role=CustomUser.Role.STUDENT
        )
        # Find matching department full name
        full_dept = depts[0]
        for d in depts:
            if dept_code in d:
                full_dept = d
                break
                
        s = Student.objects.create(
            user=u,
            roll_number=f"ROLL{2600 + idx}",
            first_name=fname,
            last_name=lname,
            email=email,
            phone=f"+1234567890{idx}",
            gender=random.choice(['M', 'F']),
            dob=date(2003, 1, 1) + timedelta(days=idx*40),
            address=f"Student Housing Block {idx + 1}, Room {100 + idx}",
            semester=sem,
            department=full_dept
        )
        students.append(s)
    print(f"Created {len(students)} Students (password: password123)")

    # Enroll Students and Add Marks/Attendance
    # We enroll each student in 2-3 courses based on their department
    comments_list = [
        "Excellent performer. Active in class.",
        "Good understanding of fundamental concepts.",
        "Performs well in assignments, needs slight improvement in final exam.",
        "Needs to be more regular in class and focus more.",
        "Outstanding work, potential for research projects.",
        "Consistent performer. Hardworking student."
    ]

    for s in students:
        # Pick 3 random courses
        enrolled_courses = random.sample(courses, 3)
        for c in enrolled_courses:
            Enrollment.objects.create(student=s, course=c)
            
            # Create Marks
            assign = random.uniform(70, 98)
            mid = random.uniform(65, 95)
            final = random.uniform(60, 96)
            
            Marks.objects.create(
                student=s,
                course=c,
                assignment_marks=round(assign, 2),
                mid_marks=round(mid, 2),
                final_marks=round(final, 2),
                teacher_comments=random.choice(comments_list)
            )

            # Create Attendance records for past 10 days
            start_date = date.today() - timedelta(days=10)
            for day in range(10):
                d = start_date + timedelta(days=day)
                # 85% chance of being present
                status = 'P' if random.random() < 0.85 else 'A'
                Attendance.objects.create(
                    student=s,
                    course=c,
                    date=d,
                    status=status
                )

    print("Successfully enrolled students, populated marks and attendance histories!")

if __name__ == '__main__':
    seed()

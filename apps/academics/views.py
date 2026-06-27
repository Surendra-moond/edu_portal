from decimal import Decimal, InvalidOperation

from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from django.utils.timezone import now
from django.views.generic import ListView
from datetime import datetime

from apps.accounts.views import StaffRequiredMixin, LoginRequiredMixin
from apps.accounts.models import CustomUser
from apps.courses.models import Course, Enrollment
from apps.accounts.models import Student
from .models import Attendance, Marks
from .forms import MarksForm
from .utils import get_course_for_staff


def _parse_mark(value):
    if value is None or value == '':
        return None
    try:
        return Decimal(value)
    except (InvalidOperation, ValueError):
        return None


# ==========================================
# Academics Hub
# ==========================================

class AcademicsHubView(StaffRequiredMixin, ListView):
    """Landing page for teachers/admins to manage attendance and marks per course."""
    model = Course
    template_name = 'academics/academics_hub.html'
    context_object_name = 'courses'
    paginate_by = 12

    def get_queryset(self):
        user = self.request.user
        queryset = Course.objects.select_related('teacher', 'teacher__user')
        if user.role == CustomUser.Role.TEACHER:
            if hasattr(user, 'teacher_profile'):
                queryset = queryset.filter(teacher=user.teacher_profile)
            else:
                return Course.objects.none()
        return queryset.order_by('course_code')


# ==========================================
# Attendance Views
# ==========================================

class MarkAttendanceView(StaffRequiredMixin, View):
    template_name = 'academics/mark_attendance.html'

    def get(self, request, course_id):
        course = get_course_for_staff(request.user, course_id)
        date_str = request.GET.get('date', now().strftime('%Y-%m-%d'))

        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            date = now().date()

        enrollments = Enrollment.objects.filter(course=course).select_related('student')
        existing_attendance = {
            att.student_id: att.status
            for att in Attendance.objects.filter(course=course, date=date)
        }

        student_attendance_list = [
            {
                'student': enrollment.student,
                'status': existing_attendance.get(enrollment.student.id, 'P'),
            }
            for enrollment in enrollments
        ]

        context = {
            'course': course,
            'date': date.strftime('%Y-%m-%d'),
            'student_attendance_list': student_attendance_list,
        }
        return render(request, self.template_name, context)

    def post(self, request, course_id):
        course = get_course_for_staff(request.user, course_id)
        date_str = request.POST.get('date')

        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            messages.error(request, "Invalid date format.")
            return redirect('mark_attendance', course_id=course_id)

        enrollments = Enrollment.objects.filter(course=course)
        for enrollment in enrollments:
            status = request.POST.get(f"status_{enrollment.student.id}")
            if status in ['P', 'A']:
                Attendance.objects.update_or_create(
                    student=enrollment.student,
                    course=course,
                    date=date,
                    defaults={'status': status},
                )

        messages.success(request, f"Attendance for {date} has been saved.")
        return redirect('mark_attendance', course_id=course_id)


class StudentAttendanceReportView(LoginRequiredMixin, View):
    template_name = 'academics/student_attendance_report.html'

    def get(self, request, student_id=None):
        user = request.user

        if student_id:
            if user.role not in ['ADMIN', 'TEACHER'] and (
                not hasattr(user, 'student_profile') or user.student_profile.id != student_id
            ):
                messages.error(request, "Access denied.")
                return redirect('dashboard')
            student = get_object_or_404(Student, id=student_id)
        else:
            if user.role != 'STUDENT':
                messages.error(request, "Dashboard is only for students.")
                return redirect('dashboard')
            student = get_object_or_404(Student, user=user)

        enrollments = Enrollment.objects.filter(student=student).select_related('course')
        attendance_summary = []

        for enrollment in enrollments:
            course = enrollment.course
            records = Attendance.objects.filter(student=student, course=course)
            total = records.count()
            present = records.filter(status='P').count()
            absent = records.filter(status='A').count()
            percentage = (present / total * 100) if total > 0 else 100.0

            attendance_summary.append({
                'course': course,
                'total_classes': total,
                'present_classes': present,
                'absent_classes': absent,
                'percentage': round(percentage, 2),
            })

        context = {
            'student': student,
            'attendance_summary': attendance_summary,
        }
        return render(request, self.template_name, context)


# ==========================================
# Marks & Grading Views
# ==========================================

class ManageMarksView(StaffRequiredMixin, View):
    template_name = 'academics/manage_marks.html'

    def get(self, request, course_id):
        course = get_course_for_staff(request.user, course_id)
        enrollments = Enrollment.objects.filter(course=course).select_related('student')
        existing_marks = {
            mark.student_id: mark
            for mark in Marks.objects.filter(course=course)
        }

        student_marks_list = [
            {
                'student': enrollment.student,
                'marks': existing_marks.get(enrollment.student.id),
            }
            for enrollment in enrollments
        ]

        context = {
            'course': course,
            'student_marks_list': student_marks_list,
        }
        return render(request, self.template_name, context)

    def post(self, request, course_id):
        course = get_course_for_staff(request.user, course_id)
        enrollments = Enrollment.objects.filter(course=course).select_related('student')
        updated_count = 0

        for enrollment in enrollments:
            sid = enrollment.student.id
            assignment = _parse_mark(request.POST.get(f'assignment_{sid}'))
            mid = _parse_mark(request.POST.get(f'mid_{sid}'))
            final = _parse_mark(request.POST.get(f'final_{sid}'))
            comments = request.POST.get(f'comments_{sid}', '').strip()

            if assignment is None and mid is None and final is None and not comments:
                continue

            marks_obj, _ = Marks.objects.get_or_create(
                student=enrollment.student,
                course=course,
                defaults={
                    'assignment_marks': Decimal('0'),
                    'mid_marks': Decimal('0'),
                    'final_marks': Decimal('0'),
                },
            )
            if assignment is not None:
                marks_obj.assignment_marks = assignment
            if mid is not None:
                marks_obj.mid_marks = mid
            if final is not None:
                marks_obj.final_marks = final
            marks_obj.teacher_comments = comments
            marks_obj.save()
            updated_count += 1

        if updated_count:
            messages.success(request, f"Grades saved for {updated_count} student(s) in {course.course_name}.")
        else:
            messages.info(request, "No grade changes were submitted.")
        return redirect('manage_marks', course_id=course_id)


class UpdateMarksView(StaffRequiredMixin, View):
    template_name = 'academics/update_marks.html'

    def get(self, request, course_id, student_id):
        course = get_course_for_staff(request.user, course_id)
        student = get_object_or_404(Student, id=student_id)

        if not Enrollment.objects.filter(course=course, student=student).exists():
            messages.error(request, "This student is not enrolled in this course.")
            return redirect('manage_marks', course_id=course_id)

        marks_obj, _ = Marks.objects.get_or_create(
            student=student,
            course=course,
            defaults={
                'assignment_marks': Decimal('0'),
                'mid_marks': Decimal('0'),
                'final_marks': Decimal('0'),
            },
        )

        form = MarksForm(instance=marks_obj)
        context = {'course': course, 'student': student, 'form': form}
        return render(request, self.template_name, context)

    def post(self, request, course_id, student_id):
        course = get_course_for_staff(request.user, course_id)
        student = get_object_or_404(Student, id=student_id)

        marks_obj, _ = Marks.objects.get_or_create(
            student=student,
            course=course,
            defaults={
                'assignment_marks': Decimal('0'),
                'mid_marks': Decimal('0'),
                'final_marks': Decimal('0'),
            },
        )

        form = MarksForm(request.POST, instance=marks_obj)
        if form.is_valid():
            form.save()
            messages.success(request, f"Grades updated for {student.first_name} {student.last_name}.")
            return redirect('manage_marks', course_id=course_id)

        context = {'course': course, 'student': student, 'form': form}
        return render(request, self.template_name, context)


class StudentReportCardView(LoginRequiredMixin, View):
    template_name = 'academics/student_report_card.html'

    def get(self, request, student_id=None):
        user = request.user

        if student_id:
            if user.role not in ['ADMIN', 'TEACHER'] and (
                not hasattr(user, 'student_profile') or user.student_profile.id != student_id
            ):
                messages.error(request, "Access denied.")
                return redirect('dashboard')
            student = get_object_or_404(Student, id=student_id)
        else:
            if user.role != 'STUDENT':
                messages.error(request, "Dashboard is only for students.")
                return redirect('dashboard')
            student = get_object_or_404(Student, user=user)

        marks_records = Marks.objects.filter(student=student).select_related('course')
        total_courses = marks_records.count()
        overall_total_marks = sum(mark.total_marks for mark in marks_records)
        average_marks = (overall_total_marks / total_courses) if total_courses > 0 else 0.0

        context = {
            'student': student,
            'marks_records': marks_records,
            'average_marks': round(average_marks, 2),
            'total_courses': total_courses,
        }
        return render(request, self.template_name, context)

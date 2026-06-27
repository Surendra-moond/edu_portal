from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib import messages
from django.db.models import Q
from django.views import View
from django.utils import timezone

from .models import Course, Enrollment, EnrollmentRequest
from .forms import CourseForm, EnrollmentForm
from apps.accounts.views import AdminRequiredMixin, StudentRequiredMixin, LoginRequiredMixin
from apps.accounts.models import Student

class CourseListView(LoginRequiredMixin, ListView):
    model = Course
    template_name = 'courses/course_list.html'
    context_object_name = 'courses'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(
                Q(course_name__icontains=query) |
                Q(course_code__icontains=query)
            )
        
        # Filter based on role if student or teacher
        user = self.request.user
        if user.role == 'TEACHER':
            # Teachers only see courses assigned to them
            if hasattr(user, 'teacher_profile'):
                queryset = queryset.filter(teacher=user.teacher_profile)
            else:
                queryset = Course.objects.none()
        elif user.role == 'STUDENT':
            # Students only see courses they are enrolled in
            if hasattr(user, 'student_profile'):
                queryset = queryset.filter(enrollments__student=user.student_profile)
            else:
                queryset = Course.objects.none()
                
        return queryset.order_by('course_code')


class CourseDetailView(LoginRequiredMixin, DetailView):
    model = Course
    template_name = 'courses/course_detail.html'
    context_object_name = 'course'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        enrollments = self.object.enrollments.all().select_related('student')
        context['enrollments'] = enrollments

        user = self.request.user
        can_manage = False
        if user.role == 'ADMIN':
            can_manage = True
        elif (
            user.role == 'TEACHER'
            and hasattr(user, 'teacher_profile')
            and self.object.teacher_id == user.teacher_profile.id
        ):
            can_manage = True
        context['can_manage_academics'] = can_manage

        if self.request.user.role == 'ADMIN':
            # Only show students not enrolled in this course yet
            enrolled_student_ids = enrollments.values_list('student_id', flat=True)
            available_students = Student.objects.exclude(id__in=enrolled_student_ids)
            context['available_students'] = available_students
            context['enrollment_form'] = EnrollmentForm(initial={'course': self.object})
            
        return context


class CourseCreateView(AdminRequiredMixin, CreateView):
    model = Course
    form_class = CourseForm
    template_name = 'courses/course_form.html'
    success_url = reverse_lazy('course_list')

    def form_valid(self, form):
        messages.success(self.request, f"Course {form.cleaned_data['course_name']} created successfully.")
        return super().form_valid(form)


class CourseUpdateView(AdminRequiredMixin, UpdateView):
    model = Course
    form_class = CourseForm
    template_name = 'courses/course_form.html'
    success_url = reverse_lazy('course_list')

    def form_valid(self, form):
        messages.success(self.request, f"Course {form.cleaned_data['course_name']} updated successfully.")
        return super().form_valid(form)


class CourseDeleteView(AdminRequiredMixin, DeleteView):
    model = Course
    template_name = 'courses/course_confirm_delete.html'
    success_url = reverse_lazy('course_list')

    def post(self, request, *args, **kwargs):
        course = self.get_object()
        messages.success(request, f"Course {course.course_name} deleted successfully.")
        return super().post(request, *args, **kwargs)


class EnrollStudentView(AdminRequiredMixin, View):
    def post(self, request, course_id):
        course = get_object_or_404(Course, id=course_id)
        student_id = request.POST.get('student')
        if student_id:
            student = get_object_or_404(Student, id=student_id)
            enrollment, created = Enrollment.objects.get_or_create(student=student, course=course)
            if created:
                messages.success(request, f"Successfully enrolled {student.first_name} {student.last_name} in {course.course_name}.")
            else:
                messages.warning(request, f"{student.first_name} is already enrolled in this course.")
        return redirect('course_detail', pk=course_id)


class UnenrollStudentView(AdminRequiredMixin, View):
    def post(self, request, course_id, student_id):
        enrollment = get_object_or_404(Enrollment, course_id=course_id, student_id=student_id)
        enrollment.delete()
        messages.success(request, "Student has been removed from this course.")
        return redirect('course_detail', pk=course_id)


class StudentEnrollCoursesView(StudentRequiredMixin, ListView):
    """Browse available courses and submit enrollment requests."""
    model = Course
    template_name = 'courses/student_enroll_courses.html'
    context_object_name = 'courses'
    paginate_by = 10

    def get_queryset(self):
        student = self.request.user.student_profile
        enrolled_ids = Enrollment.objects.filter(student=student).values_list('course_id', flat=True)
        queryset = Course.objects.exclude(id__in=enrolled_ids)

        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(
                Q(course_name__icontains=query) | Q(course_code__icontains=query)
            )
        return queryset.order_by('course_code')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        student = self.request.user.student_profile
        requests = {
            r.course_id: r.status
            for r in EnrollmentRequest.objects.filter(student=student)
        }
        context['course_items'] = [
            {'course': course, 'request_status': requests.get(course.id)}
            for course in context['courses']
        ]
        return context


class RequestCourseEnrollmentView(StudentRequiredMixin, View):
    def post(self, request, course_id):
        course = get_object_or_404(Course, id=course_id)
        student = request.user.student_profile

        if Enrollment.objects.filter(student=student, course=course).exists():
            messages.warning(request, f"You are already enrolled in {course.course_name}.")
            return redirect('student_enroll_courses')

        request_obj, created = EnrollmentRequest.objects.get_or_create(
            student=student,
            course=course,
            defaults={'status': EnrollmentRequest.Status.PENDING},
        )

        if not created:
            if request_obj.status == EnrollmentRequest.Status.PENDING:
                messages.info(request, f"Your enrollment request for {course.course_name} is already pending admin approval.")
            elif request_obj.status == EnrollmentRequest.Status.APPROVED:
                messages.warning(request, f"You are already enrolled in {course.course_name}.")
            elif request_obj.status == EnrollmentRequest.Status.REJECTED:
                request_obj.status = EnrollmentRequest.Status.PENDING
                request_obj.requested_at = timezone.now()
                request_obj.reviewed_at = None
                request_obj.save()
                messages.success(request, f"Enrollment request for {course.course_name} has been resubmitted.")
        else:
            messages.success(request, f"Enrollment request for {course.course_name} sent to admin for approval.")

        return redirect('student_enroll_courses')


class AdminPendingEnrollmentListView(AdminRequiredMixin, ListView):
    model = EnrollmentRequest
    template_name = 'courses/admin_pending_enrollments.html'
    context_object_name = 'pending_requests'
    paginate_by = 15

    def get_queryset(self):
        return EnrollmentRequest.objects.filter(
            status=EnrollmentRequest.Status.PENDING
        ).select_related('student', 'student__user', 'course').order_by('-requested_at')


class AdminApproveEnrollmentView(AdminRequiredMixin, View):
    def post(self, request, pk):
        enrollment_request = get_object_or_404(
            EnrollmentRequest,
            pk=pk,
            status=EnrollmentRequest.Status.PENDING,
        )
        enrollment_request.status = EnrollmentRequest.Status.APPROVED
        enrollment_request.reviewed_at = timezone.now()
        enrollment_request.save()

        Enrollment.objects.get_or_create(
            student=enrollment_request.student,
            course=enrollment_request.course,
        )

        messages.success(
            request,
            f"Approved enrollment: {enrollment_request.student.first_name} {enrollment_request.student.last_name} "
            f"→ {enrollment_request.course.course_name}."
        )
        return redirect('admin_pending_enrollments')


class AdminRejectEnrollmentView(AdminRequiredMixin, View):
    def post(self, request, pk):
        enrollment_request = get_object_or_404(
            EnrollmentRequest,
            pk=pk,
            status=EnrollmentRequest.Status.PENDING,
        )
        enrollment_request.status = EnrollmentRequest.Status.REJECTED
        enrollment_request.reviewed_at = timezone.now()
        enrollment_request.save()

        messages.success(
            request,
            f"Rejected enrollment request: {enrollment_request.student.first_name} "
            f"{enrollment_request.student.last_name} → {enrollment_request.course.course_name}."
        )
        return redirect('admin_pending_enrollments')


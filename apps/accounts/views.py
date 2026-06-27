from django.contrib.auth import login, logout
from django.contrib.auth.views import LoginView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.shortcuts import redirect, render, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView, DeleteView, ListView, DetailView
from django.views import View

from .models import CustomUser, Student, Teacher
from .forms import StudentRegistrationForm, TeacherRegistrationForm, StudentForm, TeacherForm

# ==========================================
# Permission Mixins
# ==========================================

class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.role == CustomUser.Role.ADMIN
    
    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            messages.error(self.request, "You do not have permission to view this page.")
            return redirect('dashboard')
        return super().handle_no_permission()


class TeacherRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.role == CustomUser.Role.TEACHER
    
    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            messages.error(self.request, "You do not have permission to view this page.")
            return redirect('dashboard')
        return super().handle_no_permission()


class StudentRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.role == CustomUser.Role.STUDENT
    
    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            messages.error(self.request, "You do not have permission to view this page.")
            return redirect('dashboard')
        return super().handle_no_permission()


class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Admin or Teacher — for attendance and marks management."""

    def test_func(self):
        return (
            self.request.user.is_authenticated
            and self.request.user.role in (CustomUser.Role.ADMIN, CustomUser.Role.TEACHER)
        )

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            messages.error(self.request, "You do not have permission to view this page.")
            return redirect('dashboard')
        return super().handle_no_permission()

# ==========================================
# Authentication Views
# ==========================================

class UserLoginView(LoginView):
    template_name = 'accounts/login.html'
    
    def get_success_url(self):
        messages.success(self.request, f"Welcome back, {self.request.user.username}!")
        return reverse_lazy('dashboard')


class UserLogoutView(View):
    def post(self, request):
        logout(request)
        messages.success(request, "You have been logged out successfully.")
        return redirect('login')
        
    def get(self, request):
        logout(request)
        messages.success(request, "You have been logged out successfully.")
        return redirect('login')


class StudentRegisterView(CreateView):
    """
    Self-registration view for students.
    Creates the account in PENDING state (is_active=False) and redirects
    to a 'pending approval' page instead of logging the user in.
    Admin must approve before the student can log in.
    """
    template_name = 'accounts/register.html'
    form_class = StudentRegistrationForm
    success_url = reverse_lazy('registration_pending')

    def form_valid(self, form):
        try:
            with transaction.atomic():
                # Create user with is_active=False so they cannot log in until approved
                user = CustomUser.objects.create_user(
                    username=form.cleaned_data['username'],
                    email=form.cleaned_data['email'],
                    password=form.cleaned_data['password'],
                    first_name=form.cleaned_data['first_name'],
                    last_name=form.cleaned_data['last_name'],
                    role=CustomUser.Role.STUDENT,
                    is_active=False,   # Cannot log in until admin approves
                )
                student = form.save(commit=False)
                student.user = user
                student.email = form.cleaned_data['email']  # sync email to Student record
                student.approval_status = Student.ApprovalStatus.PENDING
                student.save()
        except Exception as e:
            messages.error(self.request, f"Error during registration: {str(e)}")
            return self.form_invalid(form)
        return redirect(self.success_url)


class RegistrationPendingView(View):
    """Static page shown to a student after they self-register, informing them to wait for approval."""
    def get(self, request):
        return render(request, 'accounts/pending_approval.html')

# ==========================================
# Profile Edit Views (Self Service)
# ==========================================

class StudentEditProfileView(StudentRequiredMixin, UpdateView):
    model = Student
    form_class = StudentForm
    template_name = 'accounts/profile_edit.html'
    success_url = reverse_lazy('dashboard')

    def get_object(self, queryset=None):
        return self.request.user.student_profile

    def form_valid(self, form):
        # Synchronize first_name/last_name of CustomUser
        student = form.save()
        user = student.user
        user.first_name = student.first_name
        user.last_name = student.last_name
        user.email = student.email
        user.save()
        messages.success(self.request, "Your profile has been updated.")
        return redirect(self.success_url)


class TeacherEditProfileView(TeacherRequiredMixin, UpdateView):
    model = Teacher
    form_class = TeacherForm
    template_name = 'accounts/profile_edit.html'
    success_url = reverse_lazy('dashboard')

    def get_object(self, queryset=None):
        return self.request.user.teacher_profile

    def form_valid(self, form):
        form.save()
        messages.success(self.request, "Your profile has been updated.")
        return redirect(self.success_url)

# ==========================================
# Admin CRUD Views for Student Management
# ==========================================

class AdminStudentListView(AdminRequiredMixin, ListView):
    model = Student
    template_name = 'accounts/admin_student_list.html'
    context_object_name = 'students'
    paginate_by = 10

    def get_queryset(self):
        # Only show APPROVED students in main list
        queryset = Student.objects.filter(approval_status=Student.ApprovalStatus.APPROVED)
        query = self.request.GET.get('q')
        dept = self.request.GET.get('dept')
        sem = self.request.GET.get('sem')
        
        if query:
            queryset = queryset.filter(
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query) |
                Q(roll_number__icontains=query) |
                Q(email__icontains=query)
            )
        if dept:
            queryset = queryset.filter(department__iexact=dept)
        if sem:
            queryset = queryset.filter(semester=sem)
            
        return queryset.order_by('roll_number')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['departments'] = Student.objects.filter(
            approval_status=Student.ApprovalStatus.APPROVED
        ).values_list('department', flat=True).distinct()
        context['semesters'] = Student.objects.filter(
            approval_status=Student.ApprovalStatus.APPROVED
        ).values_list('semester', flat=True).distinct().order_by('semester')
        return context


class AdminCreateStudentView(AdminRequiredMixin, CreateView):
    template_name = 'accounts/admin_student_form.html'
    form_class = StudentRegistrationForm
    success_url = reverse_lazy('admin_student_list')

    def form_valid(self, form):
        try:
            with transaction.atomic():
                # Admin-created students are active and approved immediately
                user = CustomUser.objects.create_user(
                    username=form.cleaned_data['username'],
                    email=form.cleaned_data['email'],
                    password=form.cleaned_data['password'],
                    first_name=form.cleaned_data['first_name'],
                    last_name=form.cleaned_data['last_name'],
                    role=CustomUser.Role.STUDENT,
                    is_active=True,
                )
                student = form.save(commit=False)
                student.user = user
                student.email = form.cleaned_data['email']  # sync email to Student record
                student.approval_status = Student.ApprovalStatus.APPROVED
                student.save()
                messages.success(self.request, f"Student {student.first_name} {student.last_name} created successfully.")
        except Exception as e:
            messages.error(self.request, f"Error creating student: {str(e)}")
            return self.form_invalid(form)
        return redirect(self.success_url)


class AdminEditStudentView(AdminRequiredMixin, UpdateView):
    model = Student
    form_class = StudentForm
    template_name = 'accounts/admin_student_form.html'
    success_url = reverse_lazy('admin_student_list')

    def form_valid(self, form):
        student = form.save()
        user = student.user
        user.first_name = student.first_name
        user.last_name = student.last_name
        user.email = student.email
        user.save()
        messages.success(self.request, f"Student {student.first_name} has been updated.")
        return redirect(self.success_url)


class AdminDeleteStudentView(AdminRequiredMixin, DeleteView):
    model = Student
    template_name = 'accounts/admin_confirm_delete.html'
    success_url = reverse_lazy('admin_student_list')

    def post(self, request, *args, **kwargs):
        student = self.get_object()
        user = student.user
        student.delete()
        user.delete()  # Delete CustomUser as well
        messages.success(request, "Student deleted successfully.")
        return redirect(self.success_url)

# ==========================================
# Admin Approval Workflow Views
# ==========================================

class AdminPendingStudentListView(AdminRequiredMixin, ListView):
    """
    Lists all students who self-registered and are waiting for admin approval.
    Admin can Approve or Reject each one.
    """
    model = Student
    template_name = 'accounts/admin_pending_list.html'
    context_object_name = 'pending_students'
    paginate_by = 15

    def get_queryset(self):
        return Student.objects.filter(
            approval_status=Student.ApprovalStatus.PENDING
        ).select_related('user').order_by('-id')


class AdminApproveStudentView(AdminRequiredMixin, View):
    """Approve a pending student — activate their account and mark as APPROVED."""
    def post(self, request, pk):
        student = get_object_or_404(Student, pk=pk, approval_status=Student.ApprovalStatus.PENDING)
        student.approval_status = Student.ApprovalStatus.APPROVED
        student.save()
        # Activate the user account so they can log in
        user = student.user
        user.is_active = True
        user.save()
        messages.success(
            request,
            f"✅ Student '{student.first_name} {student.last_name}' has been approved and can now log in."
        )
        return redirect('admin_pending_students')


class AdminRejectStudentView(AdminRequiredMixin, View):
    """Reject a pending student — delete their account entirely."""
    def post(self, request, pk):
        student = get_object_or_404(Student, pk=pk, approval_status=Student.ApprovalStatus.PENDING)
        name = f"{student.first_name} {student.last_name}"
        user = student.user
        student.delete()
        user.delete()
        messages.warning(request, f"❌ Registration for '{name}' has been rejected and removed.")
        return redirect('admin_pending_students')

# ==========================================
# Admin CRUD Views for Teacher Management
# ==========================================

class AdminTeacherListView(AdminRequiredMixin, ListView):
    model = Teacher
    template_name = 'accounts/admin_teacher_list.html'
    context_object_name = 'teachers'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        query = self.request.GET.get('q')
        dept = self.request.GET.get('dept')
        
        if query:
            queryset = queryset.filter(
                Q(user__first_name__icontains=query) |
                Q(user__last_name__icontains=query) |
                Q(employee_id__icontains=query) |
                Q(user__email__icontains=query)
            )
        if dept:
            queryset = queryset.filter(department__iexact=dept)
            
        return queryset.order_by('employee_id')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['departments'] = Teacher.objects.values_list('department', flat=True).distinct()
        return context


class AdminCreateTeacherView(AdminRequiredMixin, CreateView):
    template_name = 'accounts/admin_teacher_form.html'
    form_class = TeacherRegistrationForm
    success_url = reverse_lazy('admin_teacher_list')

    def form_valid(self, form):
        try:
            with transaction.atomic():
                user = CustomUser.objects.create_user(
                    username=form.cleaned_data['username'],
                    email=form.cleaned_data['email'],
                    password=form.cleaned_data['password'],
                    first_name=form.cleaned_data['first_name'],
                    last_name=form.cleaned_data['last_name'],
                    role=CustomUser.Role.TEACHER
                )
                teacher = form.save(commit=False)
                teacher.user = user
                teacher.save()
                messages.success(self.request, f"Teacher {user.get_full_name()} created successfully.")
        except Exception as e:
            messages.error(self.request, f"Error creating teacher: {str(e)}")
            return self.form_invalid(form)
        return redirect(self.success_url)


class AdminEditTeacherView(AdminRequiredMixin, UpdateView):
    model = Teacher
    form_class = TeacherForm
    template_name = 'accounts/admin_teacher_form.html'
    success_url = reverse_lazy('admin_teacher_list')

    def form_valid(self, form):
        teacher = form.save()
        user = teacher.user
        # First/Last name are editable in User for Teacher registration
        user.first_name = self.request.POST.get('first_name', user.first_name)
        user.last_name = self.request.POST.get('last_name', user.last_name)
        user.email = self.request.POST.get('email', user.email)
        user.save()
        messages.success(self.request, "Teacher details updated.")
        return redirect(self.success_url)


class AdminDeleteTeacherView(AdminRequiredMixin, DeleteView):
    model = Teacher
    template_name = 'accounts/admin_confirm_delete.html'
    success_url = reverse_lazy('admin_teacher_list')

    def post(self, request, *args, **kwargs):
        teacher = self.get_object()
        user = teacher.user
        teacher.delete()
        user.delete()  # Delete CustomUser as well
        messages.success(request, "Teacher deleted successfully.")
        return redirect(self.success_url)


# ==========================================
# Dashboard View
# ==========================================

class DashboardView(LoginRequiredMixin, View):
    template_name = 'dashboard/index.html'

    def get(self, request):
        user = request.user
        context = {
            'role': user.role
        }

        # Lazy imports to avoid circular dependency
        from apps.courses.models import Course, Enrollment
        from apps.academics.models import Attendance, Marks
        from django.db.models import Avg

        if user.role == CustomUser.Role.ADMIN:
            # Only count APPROVED students in stats
            context['total_students'] = Student.objects.filter(
                approval_status=Student.ApprovalStatus.APPROVED
            ).count()
            context['total_teachers'] = Teacher.objects.count()
            context['total_courses'] = Course.objects.count()

            # Pending approvals badge count
            context['pending_count'] = Student.objects.filter(
                approval_status=Student.ApprovalStatus.PENDING
            ).count()

            # Avg total marks across all students
            avg_marks = Marks.objects.aggregate(Avg('total_marks'))['total_marks__avg']
            context['avg_marks'] = round(avg_marks, 2) if avg_marks else 0.0

            # Overall attendance rate
            total_att = Attendance.objects.count()
            present_att = Attendance.objects.filter(status='P').count()
            context['attendance_rate'] = round((present_att / total_att * 100), 2) if total_att > 0 else 100.0
            
            # Recent students (approved only)
            context['recent_students'] = Student.objects.filter(
                approval_status=Student.ApprovalStatus.APPROVED
            ).select_related('user').order_by('-id')[:5]

        elif user.role == CustomUser.Role.TEACHER:
            teacher_profile = getattr(user, 'teacher_profile', None)
            if teacher_profile:
                assigned_courses = Course.objects.filter(teacher=teacher_profile)
                context['courses'] = assigned_courses
                context['total_courses'] = assigned_courses.count()
                
                # Count total unique students enrolled in these courses
                students_enrolled = Student.objects.filter(enrollments__course__in=assigned_courses).distinct()
                context['total_students'] = students_enrolled.count()
            else:
                context['courses'] = []
                context['total_courses'] = 0
                context['total_students'] = 0

        elif user.role == CustomUser.Role.STUDENT:
            student_profile = getattr(user, 'student_profile', None)
            if student_profile:
                enrollments = Enrollment.objects.filter(student=student_profile).select_related('course')
                context['enrollments'] = enrollments
                context['total_courses'] = enrollments.count()
                
                # Get attendance statistics
                records = Attendance.objects.filter(student=student_profile)
                total = records.count()
                present = records.filter(status='P').count()
                context['attendance_percentage'] = round((present / total * 100), 2) if total > 0 else 100.0
                
                # Get average marks
                marks_records = Marks.objects.filter(student=student_profile)
                total_courses = marks_records.count()
                overall_total_marks = sum(mark.total_marks for mark in marks_records)
                context['average_marks'] = round((overall_total_marks / total_courses), 2) if total_courses > 0 else 0.0
            else:
                context['enrollments'] = []
                context['total_courses'] = 0
                context['attendance_percentage'] = 100.0
                context['average_marks'] = 0.0

        return render(request, self.template_name, context)

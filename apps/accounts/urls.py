from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('login/', views.UserLoginView.as_view(), name='login'),
    path('logout/', views.UserLogoutView.as_view(), name='logout'),
    path('register/', views.StudentRegisterView.as_view(), name='register'),
    path('register/pending/', views.RegistrationPendingView.as_view(), name='registration_pending'),

    # Password reset
    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='accounts/password_reset.html',
        email_template_name='accounts/password_reset_email.html',
        subject_template_name='accounts/password_reset_subject.txt',
        success_url='done/',
    ), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='accounts/password_reset_done.html',
    ), name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='accounts/password_reset_confirm.html',
        success_url='/password-reset-complete/',
    ), name='password_reset_confirm'),
    path('password-reset-complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='accounts/password_reset_complete.html',
    ), name='password_reset_complete'),

    # Profile edits
    path('profile/student/edit/', views.StudentEditProfileView.as_view(), name='student_profile_edit'),
    path('profile/teacher/edit/', views.TeacherEditProfileView.as_view(), name='teacher_profile_edit'),

    # Admin Student Management (approved students)
    path('portal/students/', views.AdminStudentListView.as_view(), name='admin_student_list'),
    path('portal/students/add/', views.AdminCreateStudentView.as_view(), name='admin_student_add'),
    path('portal/students/<int:pk>/edit/', views.AdminEditStudentView.as_view(), name='admin_student_edit'),
    path('portal/students/<int:pk>/delete/', views.AdminDeleteStudentView.as_view(), name='admin_student_delete'),

    # Admin Approval Workflow
    path('portal/students/pending/', views.AdminPendingStudentListView.as_view(), name='admin_pending_students'),
    path('portal/students/<int:pk>/approve/', views.AdminApproveStudentView.as_view(), name='admin_approve_student'),
    path('portal/students/<int:pk>/reject/', views.AdminRejectStudentView.as_view(), name='admin_reject_student'),

    # Admin Teacher Management
    path('portal/teachers/', views.AdminTeacherListView.as_view(), name='admin_teacher_list'),
    path('portal/teachers/add/', views.AdminCreateTeacherView.as_view(), name='admin_teacher_add'),
    path('portal/teachers/<int:pk>/edit/', views.AdminEditTeacherView.as_view(), name='admin_teacher_edit'),
    path('portal/teachers/<int:pk>/delete/', views.AdminDeleteTeacherView.as_view(), name='admin_teacher_delete'),
]

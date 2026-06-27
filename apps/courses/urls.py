from django.urls import path
from . import views

urlpatterns = [
    path('', views.CourseListView.as_view(), name='course_list'),
    path('enroll/', views.StudentEnrollCoursesView.as_view(), name='student_enroll_courses'),
    path('<int:course_id>/request-enrollment/', views.RequestCourseEnrollmentView.as_view(), name='request_course_enrollment'),
    path('pending-enrollments/', views.AdminPendingEnrollmentListView.as_view(), name='admin_pending_enrollments'),
    path('pending-enrollments/<int:pk>/approve/', views.AdminApproveEnrollmentView.as_view(), name='admin_approve_enrollment'),
    path('pending-enrollments/<int:pk>/reject/', views.AdminRejectEnrollmentView.as_view(), name='admin_reject_enrollment'),
    path('<int:pk>/', views.CourseDetailView.as_view(), name='course_detail'),
    path('add/', views.CourseCreateView.as_view(), name='course_add'),
    path('<int:pk>/edit/', views.CourseUpdateView.as_view(), name='course_edit'),
    path('<int:pk>/delete/', views.CourseDeleteView.as_view(), name='course_delete'),
    
    # Student Enrollment Actions
    path('<int:course_id>/enroll/', views.EnrollStudentView.as_view(), name='course_enroll'),
    path('<int:course_id>/unenroll/<int:student_id>/', views.UnenrollStudentView.as_view(), name='course_unenroll'),
]

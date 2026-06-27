from django.urls import path
from . import views

urlpatterns = [
    path('', views.AcademicsHubView.as_view(), name='academics_hub'),

    # Attendance URLs
    path('course/<int:course_id>/attendance/mark/', views.MarkAttendanceView.as_view(), name='mark_attendance'),
    path('student/<int:student_id>/attendance/', views.StudentAttendanceReportView.as_view(), name='student_attendance_detail'),
    path('my-attendance/', views.StudentAttendanceReportView.as_view(), name='student_attendance_self'),

    # Marks URLs
    path('course/<int:course_id>/marks/', views.ManageMarksView.as_view(), name='manage_marks'),
    path('course/<int:course_id>/student/<int:student_id>/marks/update/', views.UpdateMarksView.as_view(), name='update_marks'),
    path('student/<int:student_id>/report-card/', views.StudentReportCardView.as_view(), name='student_report_card_detail'),
    path('my-report-card/', views.StudentReportCardView.as_view(), name='student_report_card_self'),
]

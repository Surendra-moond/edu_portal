from .models import Student, CustomUser
from apps.courses.models import EnrollmentRequest


def pending_count(request):
    """
    Context processor that injects 'pending_count' into every template context.
    Only queries the database if the current user is an authenticated Admin,
    keeping the overhead minimal for other user types.
    """
    count = 0
    enrollment_pending_count = 0
    if request.user.is_authenticated and getattr(request.user, 'role', None) == CustomUser.Role.ADMIN:
        count = Student.objects.filter(approval_status=Student.ApprovalStatus.PENDING).count()
        enrollment_pending_count = EnrollmentRequest.objects.filter(
            status=EnrollmentRequest.Status.PENDING
        ).count()
    return {
        'pending_count': count,
        'enrollment_pending_count': enrollment_pending_count,
    }

from django.shortcuts import get_object_or_404
from django.http import Http404

from apps.courses.models import Course


def get_course_for_staff(user, course_id):
    """Return course if user is admin or the assigned teacher; otherwise raise 404."""
    course = get_object_or_404(Course, id=course_id)
    if user.role == 'ADMIN':
        return course
    if (
        user.role == 'TEACHER'
        and hasattr(user, 'teacher_profile')
        and course.teacher_id == user.teacher_profile.id
    ):
        return course
    raise Http404

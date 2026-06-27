from django.db import models
from apps.accounts.models import Student
from apps.courses.models import Course

class Attendance(models.Model):
    STATUS_CHOICES = [
        ('P', 'Present'),
        ('A', 'Absent'),
    ]
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='attendance_records')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='attendance_records')
    date = models.DateField()
    status = models.CharField(max_length=1, choices=STATUS_CHOICES)

    class Meta:
        unique_together = ('student', 'course', 'date')
        verbose_name_plural = "Attendance"

    def __str__(self):
        return f"{self.student.roll_number} - {self.course.course_code} - {self.date} - {self.get_status_display()}"


class Marks(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='marks_records')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='marks_records')
    assignment_marks = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    mid_marks = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    final_marks = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    total_marks = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    teacher_comments = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ('student', 'course')
        verbose_name_plural = "Marks"

    def save(self, *args, **kwargs):
        # Calculate total marks automatically before saving
        self.total_marks = (self.assignment_marks or 0) + (self.mid_marks or 0) + (self.final_marks or 0)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.student.roll_number} - {self.course.course_code} - Total: {self.total_marks}"


from django import forms
from .models import Marks, Attendance

class MarksForm(forms.ModelForm):
    class Meta:
        model = Marks
        fields = ['assignment_marks', 'mid_marks', 'final_marks', 'teacher_comments']
        widgets = {
            'assignment_marks': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': 0, 'max': 100}),
            'mid_marks': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': 0, 'max': 100}),
            'final_marks': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': 0, 'max': 100}),
            'teacher_comments': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

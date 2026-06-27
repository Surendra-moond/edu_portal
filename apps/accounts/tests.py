from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

CustomUser = get_user_model()

class UserRoleTestCase(TestCase):
    def setUp(self):
        self.admin = CustomUser.objects.create_user(
            username='admin_test',
            email='admin@test.com',
            password='password123',
            role=CustomUser.Role.ADMIN
        )
        self.teacher = CustomUser.objects.create_user(
            username='teacher_test',
            email='teacher@test.com',
            password='password123',
            role=CustomUser.Role.TEACHER
        )
        self.student = CustomUser.objects.create_user(
            username='student_test',
            email='student@test.com',
            password='password123',
            role=CustomUser.Role.STUDENT
        )

    def test_user_creation_roles(self):
        """Verify role validation and representation"""
        self.assertEqual(self.admin.role, 'ADMIN')
        self.assertEqual(self.teacher.role, 'TEACHER')
        self.assertEqual(self.student.role, 'STUDENT')
        self.assertTrue(self.admin.check_password('password123'))
        
        self.assertEqual(str(self.admin), "admin_test (Admin)")

    def test_dashboard_redirect_anonymous(self):
        """Anonymous user should be redirected to login from dashboard"""
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)

    def test_student_list_restricted_to_admin(self):
        """Only Admin should be allowed to view the student list"""
        # Test anonymous
        response = self.client.get(reverse('admin_student_list'))
        self.assertEqual(response.status_code, 302)
        
        # Test student login
        self.client.login(username='student_test', password='password123')
        response = self.client.get(reverse('admin_student_list'))
        # Should redirect to standard dashboard with warning
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('dashboard'))
        
        # Test admin login
        self.client.login(username='admin_test', password='password123')
        response = self.client.get(reverse('admin_student_list'))
        self.assertEqual(response.status_code, 200)


"""
Unit tests for core models in the consulting manager application.
"""
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from datetime import date, timedelta
from decimal import Decimal

from clients.models import Client
from projects.models import (
    Project, ProjectPhase, TimeEntry, Milestone, 
    ProjectTemplate, ActivityLog, ScopeItem
)
from files.models import File


class ClientModelTest(TestCase):
    """Tests for the Client model"""
    
    def setUp(self):
        self.client_data = {
            'name': 'John Doe',
            'company': 'Acoustic Consulting Inc',
            'email': 'john@acoustic.com',
            'phone': '555-1234',
            'address': '123 Main St, Honolulu, HI'
        }
    
    def test_create_client(self):
        """Test creating a basic client"""
        client = Client.objects.create(**self.client_data)
        self.assertEqual(client.name, 'John Doe')
        self.assertEqual(client.company, 'Acoustic Consulting Inc')
        self.assertIsNotNone(client.created_at)
    
    def test_client_str(self):
        """Test client string representation"""
        client = Client.objects.create(**self.client_data)
        self.assertEqual(str(client), 'John Doe - Acoustic Consulting Inc')
    
    def test_client_ordering(self):
        """Test clients are ordered by name"""
        # Clear any existing clients (must clear projects first due to FK protection)
        Project.objects.all().delete()
        Client.objects.all().delete()
        Client.objects.create(name='Zack', company='Z Corp', email='z@z.com', phone='111', address='Addr')
        Client.objects.create(name='Alice', company='A Corp', email='a@a.com', phone='222', address='Addr')
        clients = Client.objects.all()
        self.assertEqual(clients[0].name, 'Alice')
        self.assertEqual(clients[1].name, 'Zack')


class ProjectModelTest(TestCase):
    """Tests for the Project model"""
    
    def setUp(self):
        self.client = Client.objects.create(
            name='Test Client',
            company='Test Company',
            email='test@test.com',
            phone='555-0000',
            address='123 Test St'
        )
    
    def test_create_project(self):
        """Test creating a basic project"""
        project = Project.objects.create(
            title='Sound Isolation Study',
            client=self.client,
            description='Evaluate sound isolation requirements',
            start_date=date.today(),
            status='planning'
        )
        self.assertEqual(project.title, 'Sound Isolation Study')
        self.assertEqual(project.status, 'planning')
        self.assertEqual(project.client, self.client)
    
    def test_project_str(self):
        """Test project string representation"""
        project = Project.objects.create(
            title='Test Project',
            client=self.client,
            description='Test',
            start_date=date.today()
        )
        self.assertEqual(str(project), 'Test Project - Test Client')
    
    def test_project_date_validation(self):
        """Test that end_date cannot be before start_date"""
        project = Project(
            title='Invalid Dates Project',
            client=self.client,
            description='Test',
            start_date=date(2024, 6, 15),
            end_date=date(2024, 6, 1)  # Before start
        )
        with self.assertRaises(ValidationError) as context:
            project.full_clean()
        self.assertIn('end_date', context.exception.message_dict)
    
    def test_project_valid_dates(self):
        """Test that valid date ranges pass validation"""
        project = Project(
            title='Valid Dates Project',
            client=self.client,
            description='Test',
            start_date=date(2024, 6, 1),
            end_date=date(2024, 12, 31)
        )
        project.full_clean()  # Should not raise
    
    def test_project_client_protection(self):
        """Test that deleting a client with projects raises error"""
        Project.objects.create(
            title='Protected Project',
            client=self.client,
            description='Test',
            start_date=date.today()
        )
        # Attempting to delete the client should raise ProtectedError
        from django.db.models import ProtectedError
        with self.assertRaises(ProtectedError):
            self.client.delete()


class ProjectPhaseTest(TestCase):
    """Tests for the ProjectPhase model"""
    
    def setUp(self):
        self.client = Client.objects.create(
            name='Phase Client', company='Co', email='p@c.com', phone='111', address='Addr'
        )
        self.project = Project.objects.create(
            title='Phase Test Project',
            client=self.client,
            description='Test',
            start_date=date.today()
        )
    
    def test_create_phase(self):
        """Test creating project phases"""
        phase = ProjectPhase.objects.create(
            project=self.project,
            name='Design Development',
            order=1,
            percent_complete=25.5
        )
        self.assertEqual(phase.name, 'Design Development')
        self.assertEqual(phase.percent_complete, 25.5)
        self.assertEqual(phase.status, 'not_started')


class TimeEntryTest(TestCase):
    """Tests for the TimeEntry model"""
    
    def setUp(self):
        self.user = User.objects.create_user('testuser', 'test@test.com', 'password')
        self.client = Client.objects.create(
            name='Time Client', company='Co', email='t@c.com', phone='111', address='Addr'
        )
        self.project = Project.objects.create(
            title='Time Project',
            client=self.client,
            description='Test',
            start_date=date.today()
        )
    
    def test_create_time_entry(self):
        """Test creating a time entry"""
        entry = TimeEntry.objects.create(
            project=self.project,
            user=self.user,
            date=date.today(),
            hours=Decimal('2.5'),
            description='Acoustic measurements',
            billable=True
        )
        self.assertEqual(entry.hours, Decimal('2.5'))
        self.assertTrue(entry.billable)


class MilestoneTest(TestCase):
    """Tests for the Milestone model"""
    
    def setUp(self):
        self.client = Client.objects.create(
            name='Mile Client', company='Co', email='m@c.com', phone='111', address='Addr'
        )
        self.project = Project.objects.create(
            title='Milestone Project',
            client=self.client,
            description='Test',
            start_date=date.today()
        )
    
    def test_create_milestone(self):
        """Test creating a milestone"""
        due = date.today() + timedelta(days=30)
        milestone = Milestone.objects.create(
            project=self.project,
            name='Draft Report Due',
            due_date=due,
            source='manual'
        )
        self.assertEqual(milestone.name, 'Draft Report Due')
        self.assertEqual(milestone.due_date, due)


class ProjectTemplateTest(TestCase):
    """Tests for the ProjectTemplate model"""
    
    def setUp(self):
        self.template = ProjectTemplate.objects.create(
            name='Standard Acoustic Study',
            description='Template for typical acoustic consulting projects',
            default_phases=[
                {'name': 'Kickoff', 'order': 1},
                {'name': 'Field Measurements', 'order': 2},
                {'name': 'Analysis', 'order': 3},
                {'name': 'Report', 'order': 4}
            ],
            default_milestones=[
                {'name': 'Site Visit', 'days_from_start': 7},
                {'name': 'Draft Report', 'days_from_start': 30},
                {'name': 'Final Report', 'days_from_start': 45}
            ],
            default_scope_categories=['Sound Isolation', 'Mechanical Noise'],
            estimated_duration_days=60
        )
        self.client = Client.objects.create(
            name='Template Client', company='Co', email='t@c.com', phone='111', address='Addr'
        )
    
    def test_create_template(self):
        """Test template creation"""
        self.assertEqual(self.template.name, 'Standard Acoustic Study')
        self.assertEqual(len(self.template.default_phases), 4)
        self.assertEqual(len(self.template.default_milestones), 3)
    
    def test_apply_template_to_project(self):
        """Test applying template to a project"""
        project = Project.objects.create(
            title='New Project from Template',
            client=self.client,
            description='Test',
            start_date=date.today()
        )
        
        self.template.apply_to_project(project)
        
        # Check phases were created
        self.assertEqual(project.phases.count(), 4)
        phase_names = list(project.phases.values_list('name', flat=True))
        self.assertIn('Kickoff', phase_names)
        self.assertIn('Field Measurements', phase_names)
        
        # Check milestones were created
        self.assertEqual(project.milestones.count(), 3)
        
        # Check end date was set
        project.refresh_from_db()
        expected_end = date.today() + timedelta(days=60)
        self.assertEqual(project.end_date, expected_end)


class ActivityLogTest(TestCase):
    """Tests for the ActivityLog model"""
    
    def setUp(self):
        self.user = User.objects.create_user('loguser', 'log@test.com', 'password')
        self.client = Client.objects.create(
            name='Log Client', company='Co', email='l@c.com', phone='111', address='Addr'
        )
        self.project = Project.objects.create(
            title='Log Project',
            client=self.client,
            description='Test',
            start_date=date.today()
        )
    
    def test_create_activity_log(self):
        """Test creating an activity log entry"""
        log = ActivityLog.objects.create(
            project=self.project,
            user=self.user,
            action='create',
            description='Created new project',
            object_type='Project',
            object_id=self.project.id
        )
        self.assertEqual(log.action, 'create')
        self.assertEqual(log.get_action_display(), 'Created')
        self.assertIsNotNone(log.created_at)
    
    def test_activity_log_ordering(self):
        """Test logs are ordered by most recent first"""
        ActivityLog.objects.create(
            project=self.project, action='create', description='First'
        )
        ActivityLog.objects.create(
            project=self.project, action='update', description='Second'
        )
        logs = ActivityLog.objects.filter(project=self.project)
        self.assertEqual(logs[0].description, 'Second')
        self.assertEqual(logs[1].description, 'First')

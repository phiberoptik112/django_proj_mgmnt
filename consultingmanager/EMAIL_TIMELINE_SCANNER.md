# Email Timeline Scanner - Implementation Plan

## Overview

The Email Timeline Scanner is designed to automatically extract project timeline waypoints and status indicators from email communications stored in project folders. This builds on the existing minimal email text display functionality and the PIF Scanner pattern to reduce manual data entry for engineers and project managers.

## Goals

1. **Automatic Timeline Detection**: Identify dates, deadlines, and milestones mentioned in emails
2. **Project Status Inference**: Determine project phase/status from email content patterns
3. **Waypoint Extraction**: Create Milestone records from detected timeline events
4. **Communication History**: Build a timeline of key project communications
5. **Progress Tracking**: Track project progression through standard consulting phases

## Existing Infrastructure

### Current Email Model (`files/models.py`)
```python
class Email(models.Model):
    project = ForeignKey('projects.Project')
    folder = ForeignKey(ProjectFolder)
    filename = CharField(max_length=255)
    sender = CharField(max_length=255)
    subject = CharField(max_length=255)
    body = TextField()
    date = DateTimeField()
    attachments = JSONField()
    thread_id = CharField(max_length=255)
    thread_subject = CharField(max_length=255)
    # ...
```

### Current Email Processor (`files/utils/email_processor.py`)
- Converts .msg files to text
- Extracts basic fields: From, To, Subject, Date, Body
- Batch processing for project directories

### Current Milestone Model (`projects/models.py`)
```python
class Milestone(models.Model):
    MILESTONE_SOURCE_CHOICES = [
        ('manual', 'Manual'),
        ('email', 'Extracted from Email'),
    ]
    project = ForeignKey('Project')
    name = CharField(max_length=200)
    due_date = DateField()
    source = CharField(max_length=20, choices=MILESTONE_SOURCE_CHOICES)
    description = TextField()
    related_email = ForeignKey('files.Email', null=True)  # Already supports email linking!
```

## New Models

### 1. EmailScanBatch (`files/models.py`)
```python
class EmailScanBatch(models.Model):
    """Batch of email scans for a project or set of projects"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    name = CharField(max_length=200)
    description = TextField(blank=True)
    project = ForeignKey('projects.Project', null=True, blank=True)  # Optional single project
    folder_paths = JSONField(default=list)  # List of folder paths to scan
    
    status = CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    started_at = DateTimeField(null=True)
    completed_at = DateTimeField(null=True)
    
    # Statistics
    total_emails_scanned = IntegerField(default=0)
    total_waypoints_found = IntegerField(default=0)
    total_milestones_created = IntegerField(default=0)
    
    error_summary = TextField(blank=True)
    created_at = DateTimeField(auto_now_add=True)
```

### 2. EmailTimelineEvent (`files/models.py`)
```python
class EmailTimelineEvent(models.Model):
    """Extracted timeline waypoint from email content"""
    EVENT_TYPES = [
        ('deadline', 'Deadline'),
        ('meeting', 'Meeting'),
        ('submittal', 'Submittal/Delivery'),
        ('milestone', 'Milestone'),
        ('kickoff', 'Project Kickoff'),
        ('site_visit', 'Site Visit'),
        ('review', 'Review Period'),
        ('approval', 'Approval'),
        ('completion', 'Completion'),
        ('invoice', 'Invoice/Payment'),
        ('change_order', 'Change Order'),
        ('other', 'Other'),
    ]
    
    CONFIDENCE_LEVELS = [
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('confirmed', 'Confirmed'),
        ('rejected', 'Rejected'),
        ('converted', 'Converted to Milestone'),
    ]
    
    scan_batch = ForeignKey(EmailScanBatch, on_delete=CASCADE, related_name='events')
    email = ForeignKey(Email, on_delete=CASCADE, related_name='timeline_events')
    project = ForeignKey('projects.Project', on_delete=CASCADE, related_name='email_timeline_events')
    
    event_type = CharField(max_length=30, choices=EVENT_TYPES)
    event_date = DateField()
    event_description = CharField(max_length=500)
    
    # Extraction metadata
    extracted_text = TextField()  # The text snippet that triggered extraction
    confidence = CharField(max_length=10, choices=CONFIDENCE_LEVELS, default='medium')
    extraction_method = CharField(max_length=50)  # 'regex', 'nlp', 'pattern'
    
    # Review workflow
    status = CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reviewed_by = ForeignKey('auth.User', null=True, blank=True, on_delete=SET_NULL)
    reviewed_at = DateTimeField(null=True, blank=True)
    
    # If converted to milestone
    milestone = ForeignKey('projects.Milestone', null=True, blank=True, on_delete=SET_NULL)
    
    created_at = DateTimeField(auto_now_add=True)
```

### 3. ProjectStatusIndicator (`files/models.py`)
```python
class ProjectStatusIndicator(models.Model):
    """Inferred project status from email patterns"""
    INDICATOR_TYPES = [
        ('phase_start', 'Phase Start'),
        ('phase_complete', 'Phase Complete'),
        ('deliverable_sent', 'Deliverable Sent'),
        ('client_approval', 'Client Approval'),
        ('waiting_on_client', 'Waiting on Client'),
        ('active_work', 'Active Work'),
        ('on_hold', 'On Hold'),
        ('issue_flagged', 'Issue Flagged'),
    ]
    
    scan_batch = ForeignKey(EmailScanBatch, on_delete=CASCADE, related_name='indicators')
    email = ForeignKey(Email, on_delete=CASCADE, related_name='status_indicators')
    project = ForeignKey('projects.Project', on_delete=CASCADE, related_name='email_status_indicators')
    
    indicator_type = CharField(max_length=30, choices=INDICATOR_TYPES)
    indicator_date = DateField()
    description = TextField()
    extracted_text = TextField()
    confidence = CharField(max_length=10)
    
    # Phase inference
    inferred_phase = CharField(max_length=100, blank=True)  # Maps to ProjectPhase.name
    
    created_at = DateTimeField(auto_now_add=True)
```

## Email Parser Module

### `files/utils/email_timeline_parser.py`

```python
"""
Email Timeline Parser

Extracts timeline waypoints and project status indicators from email content.
Uses pattern matching, regex, and heuristics specific to consulting workflows.
"""

import re
from datetime import datetime, date
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

class EventType(Enum):
    DEADLINE = 'deadline'
    MEETING = 'meeting'
    SUBMITTAL = 'submittal'
    MILESTONE = 'milestone'
    KICKOFF = 'kickoff'
    SITE_VISIT = 'site_visit'
    REVIEW = 'review'
    APPROVAL = 'approval'
    COMPLETION = 'completion'
    INVOICE = 'invoice'
    CHANGE_ORDER = 'change_order'
    OTHER = 'other'

@dataclass
class ExtractedEvent:
    event_type: EventType
    event_date: date
    description: str
    extracted_text: str
    confidence: str  # 'high', 'medium', 'low'
    extraction_method: str

class EmailTimelineParser:
    """Parse emails for timeline waypoints and status indicators"""
    
    # Date patterns for extraction
    DATE_PATTERNS = [
        # Standard formats
        r'(\d{1,2}/\d{1,2}/\d{2,4})',  # MM/DD/YYYY or M/D/YY
        r'(\d{1,2}-\d{1,2}-\d{2,4})',  # MM-DD-YYYY
        r'(\w+ \d{1,2},? \d{4})',       # Month DD, YYYY
        r'(\d{1,2} \w+ \d{4})',         # DD Month YYYY
    ]
    
    # Consulting-specific timeline keywords
    DEADLINE_KEYWORDS = [
        'due', 'deadline', 'by', 'before', 'no later than', 'submit by',
        'need by', 'required by', 'expected by', 'target date'
    ]
    
    MEETING_KEYWORDS = [
        'meeting', 'call', 'conference', 'discussion', 'presentation',
        'kick-off', 'kickoff', 'kick off', 'review meeting'
    ]
    
    SUBMITTAL_KEYWORDS = [
        'submit', 'deliver', 'send', 'provide', 'transmit', 'issue',
        'draft', 'final', 'report', 'deliverable', 'package'
    ]
    
    SITE_VISIT_KEYWORDS = [
        'site visit', 'field work', 'field visit', 'on-site', 'onsite',
        'measurement', 'testing', 'survey', 'inspection'
    ]
    
    REVIEW_KEYWORDS = [
        'review', 'comment', 'feedback', 'response', 'revision',
        'approval', 'sign-off', 'signoff'
    ]
    
    COMPLETION_KEYWORDS = [
        'complete', 'completed', 'finished', 'done', 'final',
        'closeout', 'close-out', 'close out', 'wrapped up'
    ]
    
    # Phase detection patterns (consulting-specific)
    PHASE_PATTERNS = {
        'Proposal': ['proposal', 'quote', 'estimate', 'fee'],
        'Contract': ['contract', 'agreement', 'authorization', 'NTP', 'notice to proceed'],
        'Design': ['design', 'schematic', 'DD', 'design development'],
        'Construction Documents': ['CD', 'construction documents', 'permit'],
        'Bidding': ['bid', 'bidding', 'contractor selection'],
        'Construction Administration': ['CA', 'construction admin', 'RFI', 'submittal review'],
        'Closeout': ['closeout', 'close-out', 'final report', 'project complete']
    }
    
    def parse_email(self, subject: str, body: str, email_date: datetime) -> List[ExtractedEvent]:
        """Extract timeline events from email content"""
        events = []
        full_text = f"{subject}\n{body}"
        
        # Find all dates in the email
        dates_found = self._extract_dates(full_text)
        
        # For each date, determine context and event type
        for date_str, parsed_date, context in dates_found:
            event = self._classify_event(context, parsed_date, date_str)
            if event:
                events.append(event)
        
        # Also check for relative dates ("next week", "tomorrow", etc.)
        relative_events = self._extract_relative_dates(full_text, email_date)
        events.extend(relative_events)
        
        return events
    
    def _extract_dates(self, text: str) -> List[Tuple[str, date, str]]:
        """Extract dates and their surrounding context"""
        results = []
        for pattern in self.DATE_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                date_str = match.group(1)
                parsed = self._parse_date(date_str)
                if parsed:
                    # Get surrounding context (100 chars before and after)
                    start = max(0, match.start() - 100)
                    end = min(len(text), match.end() + 100)
                    context = text[start:end]
                    results.append((date_str, parsed, context))
        return results
    
    def _classify_event(self, context: str, event_date: date, date_str: str) -> Optional[ExtractedEvent]:
        """Classify an event based on surrounding context"""
        context_lower = context.lower()
        
        # Check each event type
        if any(kw in context_lower for kw in self.DEADLINE_KEYWORDS):
            return ExtractedEvent(
                event_type=EventType.DEADLINE,
                event_date=event_date,
                description=self._extract_description(context, date_str),
                extracted_text=context,
                confidence='high' if 'deadline' in context_lower else 'medium',
                extraction_method='keyword_match'
            )
        
        if any(kw in context_lower for kw in self.MEETING_KEYWORDS):
            return ExtractedEvent(
                event_type=EventType.MEETING,
                event_date=event_date,
                description=self._extract_description(context, date_str),
                extracted_text=context,
                confidence='high' if 'meeting' in context_lower else 'medium',
                extraction_method='keyword_match'
            )
        
        # Continue for other event types...
        # (site visit, submittal, review, completion, etc.)
        
        return None
    
    def infer_project_phase(self, emails: List[dict]) -> str:
        """Infer current project phase from email patterns"""
        phase_scores = {phase: 0 for phase in self.PHASE_PATTERNS}
        
        for email in emails:
            text = f"{email.get('subject', '')} {email.get('body', '')}".lower()
            for phase, keywords in self.PHASE_PATTERNS.items():
                for keyword in keywords:
                    if keyword.lower() in text:
                        phase_scores[phase] += 1
        
        # Return phase with highest score
        if max(phase_scores.values()) > 0:
            return max(phase_scores, key=phase_scores.get)
        return 'Unknown'
```

## Views and URLs

### New Views (`files/views.py` additions)

```python
# Email Scanner Dashboard
@login_required
def email_scanner_dashboard(request):
    """Dashboard for email timeline scanning"""
    recent_batches = EmailScanBatch.objects.order_by('-created_at')[:10]
    pending_events = EmailTimelineEvent.objects.filter(status='pending').count()
    
    context = {
        'recent_batches': recent_batches,
        'pending_events': pending_events,
        'stats': {
            'total_emails_scanned': EmailScanBatch.objects.aggregate(Sum('total_emails_scanned'))['total_emails_scanned__sum'] or 0,
            'total_waypoints': EmailTimelineEvent.objects.count(),
            'total_milestones_created': EmailTimelineEvent.objects.filter(status='converted').count(),
        }
    }
    return render(request, 'files/email_scanner_dashboard.html', context)

# Create scan batch
@login_required
def email_scan_batch_create(request):
    """Create a new email scan batch"""
    # Similar to PIF scan batch creation
    pass

# Run scan
@login_required
@require_POST
def run_email_scan_batch(request, batch_id):
    """Execute an email scan batch"""
    batch = get_object_or_404(EmailScanBatch, id=batch_id)
    # Process emails, extract events
    pass

# Review extracted events
@login_required
def email_event_review(request, batch_id):
    """Review and confirm/reject extracted timeline events"""
    batch = get_object_or_404(EmailScanBatch, id=batch_id)
    events = batch.events.filter(status='pending')
    # Paginate and display for review
    pass

# Convert event to milestone
@login_required
@require_POST
def convert_event_to_milestone(request, event_id):
    """Convert a confirmed event to a project milestone"""
    event = get_object_or_404(EmailTimelineEvent, id=event_id)
    # Create milestone from event
    milestone = Milestone.objects.create(
        project=event.project,
        name=event.event_description,
        due_date=event.event_date,
        source='email',
        description=f"Extracted from email: {event.extracted_text[:200]}",
        related_email=event.email
    )
    event.status = 'converted'
    event.milestone = milestone
    event.save()
    pass

# Project email timeline view
@login_required
def project_email_timeline(request, project_id):
    """View email-derived timeline for a project"""
    project = get_object_or_404(Project, id=project_id)
    # Get all emails, events, indicators for this project
    # Build chronological timeline
    pass
```

### URL Patterns (`files/urls.py` additions)

```python
# Email Scanner URLs
path('email-scanner/', views.email_scanner_dashboard, name='email-scanner-dashboard'),
path('email-scanner/batch/create/', views.email_scan_batch_create, name='email-scan-batch-create'),
path('email-scanner/batch/<int:batch_id>/', views.email_scan_batch_detail, name='email-scan-batch-detail'),
path('email-scanner/batch/<int:batch_id>/run/', views.run_email_scan_batch, name='run-email-scan-batch'),
path('email-scanner/batch/<int:batch_id>/review/', views.email_event_review, name='email-event-review'),
path('email-scanner/event/<int:event_id>/convert/', views.convert_event_to_milestone, name='convert-event-to-milestone'),
path('email-scanner/event/<int:event_id>/confirm/', views.confirm_event, name='confirm-event'),
path('email-scanner/event/<int:event_id>/reject/', views.reject_event, name='reject-event'),
path('project/<int:project_id>/email-timeline/', views.project_email_timeline, name='project-email-timeline'),
```

## User Interface

### 1. Email Scanner Dashboard (`templates/files/email_scanner_dashboard.html`)
- Statistics cards (total scanned, waypoints found, milestones created)
- Recent scan batches list
- Quick scan button for single project
- Link to pending review queue

### 2. Scan Batch Creation Form
- Select project(s) or folder paths
- Option to scan specific date range
- Event type filters (what to look for)

### 3. Event Review Interface
- Card-based layout showing extracted events
- Original email context highlighted
- Quick actions: Confirm, Reject, Edit, Convert to Milestone
- Bulk actions for efficiency

### 4. Project Email Timeline View
- Chronological timeline visualization
- Events, milestones, and status indicators
- Filter by event type, date range
- Link to original emails
- Inferred project phase indicator

## Integration Points

### 1. Project Detail Page
Add "Email Timeline" tab showing:
- Extracted timeline events
- Inferred current phase
- Recent email activity summary

### 2. Home Dashboard
Add widget for:
- Projects with pending email events to review
- Recent timeline discoveries

### 3. Milestone Views
Show source indicator (manual vs email-extracted) and link to source email

### 4. Activity Log
Log email scan activities and milestone creations

## Implementation Order

### Phase 1: Core Models and Parser (Week 1)
1. Create new models (EmailScanBatch, EmailTimelineEvent, ProjectStatusIndicator)
2. Implement EmailTimelineParser with basic date/keyword extraction
3. Add migrations

### Phase 2: Scanner Infrastructure (Week 1-2)
1. Create email scanning management command
2. Implement batch processing logic
3. Build on existing email_processor.py

### Phase 3: Views and Dashboard (Week 2)
1. Email scanner dashboard
2. Batch creation and management views
3. Event review interface

### Phase 4: Review Workflow (Week 2-3)
1. Event confirmation/rejection flow
2. Milestone conversion
3. Bulk actions

### Phase 5: Integration (Week 3)
1. Project detail page integration
2. Home dashboard widgets
3. Activity logging

### Phase 6: Refinement (Week 3-4)
1. Improve extraction accuracy based on real data
2. Add consulting-specific patterns
3. Phase inference improvements

## Consulting-Specific Patterns to Detect

### Acoustic/Noise Consulting Keywords
- "noise study", "acoustical report", "sound transmission"
- "STC rating", "NIC", "NC level", "RT60"
- "HVAC noise", "environmental noise"
- "measurement", "testing", "site visit"

### Standard Project Phases
1. **Proposal/Fee**: "proposal", "fee estimate", "scope"
2. **Contract/Authorization**: "NTP", "authorization", "contract signed"
3. **Design**: "design", "specifications", "recommendations"
4. **Report**: "draft report", "final report", "deliverable"
5. **Review**: "client review", "comments", "revisions"
6. **Closeout**: "project complete", "final invoice"

### Timeline Trigger Phrases
- "Please provide by [DATE]"
- "Deadline is [DATE]"
- "Meeting scheduled for [DATE]"
- "Site visit on [DATE]"
- "Report due [DATE]"
- "Expecting delivery by [DATE]"

## Testing Strategy

1. Unit tests for date extraction patterns
2. Unit tests for event classification
3. Integration tests with sample .msg files
4. Manual testing with real project emails
5. Accuracy tracking and improvement

## Future Enhancements

1. **Machine Learning**: Train classifier on confirmed events
2. **NLP Integration**: Use spaCy or similar for better entity extraction
3. **Email Threading**: Better thread analysis for conversation context
4. **Automatic Status Updates**: Auto-update project status based on patterns
5. **Notifications**: Alert when important timeline events are detected
6. **Calendar Integration**: Export milestones to calendar

"""
Tests for the Email Timeline Parser
"""
from django.test import TestCase
from datetime import datetime, date, timedelta
from files.utils.email_timeline_parser import (
    EmailTimelineParser, EventType, IndicatorType, 
    ExtractedEvent, ParseResult
)


class EmailTimelineParserDateExtractionTest(TestCase):
    """Test date extraction functionality"""
    
    def setUp(self):
        self.parser = EmailTimelineParser()
    
    def test_extract_mm_dd_yyyy_date(self):
        """Test extraction of MM/DD/YYYY format"""
        text = "The deadline is 01/15/2024 for the report."
        dates = self.parser._extract_dates(text)
        
        # May match multiple patterns, but should find the date
        self.assertGreaterEqual(len(dates), 1)
        # Check that at least one parsed date matches
        parsed_dates = [d[1] for d in dates]
        self.assertIn(date(2024, 1, 15), parsed_dates)
    
    def test_extract_month_name_date(self):
        """Test extraction of 'January 15, 2024' format"""
        text = "The meeting is scheduled for January 15, 2024."
        dates = self.parser._extract_dates(text)
        
        self.assertEqual(len(dates), 1)
        date_str, parsed_date, context = dates[0]
        self.assertEqual(parsed_date, date(2024, 1, 15))
    
    def test_extract_multiple_dates(self):
        """Test extraction of multiple dates from text"""
        text = "The project starts 01/01/2024 and ends 03/15/2024."
        dates = self.parser._extract_dates(text)
        
        # Should find at least 2 unique dates (may have duplicates from overlapping patterns)
        unique_dates = set(d[1] for d in dates)
        self.assertGreaterEqual(len(unique_dates), 2)
    
    def test_extract_iso_date(self):
        """Test extraction of ISO format date"""
        text = "Target completion: 2024-06-30"
        dates = self.parser._extract_dates(text)
        
        self.assertEqual(len(dates), 1)
        self.assertEqual(dates[0][1], date(2024, 6, 30))


class EmailTimelineParserEventClassificationTest(TestCase):
    """Test event classification functionality"""
    
    def setUp(self):
        self.parser = EmailTimelineParser()
        self.email_date = datetime(2024, 1, 10)
    
    def test_classify_deadline_event(self):
        """Test classification of deadline events"""
        subject = "Report Due Date"
        body = "Please submit the final report by 01/20/2024. This is the deadline for the acoustical analysis."
        
        result = self.parser.parse_email(subject, body, self.email_date)
        
        deadline_events = [e for e in result.events if e.event_type == EventType.DEADLINE]
        self.assertGreaterEqual(len(deadline_events), 1)
        self.assertEqual(deadline_events[0].event_date, date(2024, 1, 20))
    
    def test_classify_meeting_event(self):
        """Test classification of meeting events"""
        subject = "Project Kickoff Meeting"
        body = "We have scheduled a meeting for 01/25/2024 to discuss project requirements."
        
        result = self.parser.parse_email(subject, body, self.email_date)
        
        # May classify as meeting or kickoff (both are valid)
        meeting_events = [e for e in result.events if e.event_type in [EventType.MEETING, EventType.KICKOFF]]
        self.assertGreaterEqual(len(meeting_events), 1)
    
    def test_classify_site_visit_event(self):
        """Test classification of site visit events"""
        subject = "Field Work Schedule"
        body = "The site visit for acoustic testing is scheduled for 02/05/2024."
        
        result = self.parser.parse_email(subject, body, self.email_date)
        
        site_visits = [e for e in result.events if e.event_type == EventType.SITE_VISIT]
        self.assertGreaterEqual(len(site_visits), 1)
    
    def test_classify_submittal_event(self):
        """Test classification of submittal/delivery events"""
        subject = "Draft Report Delivery"
        body = "We will deliver the draft report on 01/30/2024 for your review."
        
        result = self.parser.parse_email(subject, body, self.email_date)
        
        submittals = [e for e in result.events if e.event_type == EventType.SUBMITTAL]
        self.assertGreaterEqual(len(submittals), 1)
    
    def test_high_confidence_for_specific_keywords(self):
        """Test that specific keywords result in high or medium confidence"""
        subject = "Submission Deadline"
        body = "The deadline is 02/15/2024. This is the due date. No later than this date."
        
        result = self.parser.parse_email(subject, body, self.email_date)
        
        # Should have events with confidence scores
        self.assertGreater(len(result.events), 0)
        # At least one event should have high or medium confidence
        self.assertTrue(any(e.confidence in ['high', 'medium'] for e in result.events))


class EmailTimelineParserRelativeDateTest(TestCase):
    """Test relative date extraction"""
    
    def setUp(self):
        self.parser = EmailTimelineParser()
    
    def test_extract_tomorrow(self):
        """Test extraction of 'tomorrow'"""
        email_date = datetime(2024, 1, 10)
        subject = "Quick Reminder"
        body = "Don't forget the meeting tomorrow. We need to discuss the deadline."
        
        result = self.parser.parse_email(subject, body, email_date)
        
        # Should find an event for January 11
        tomorrow_events = [e for e in result.events if e.event_date == date(2024, 1, 11)]
        self.assertGreaterEqual(len(tomorrow_events), 1)
    
    def test_extract_next_week(self):
        """Test extraction of 'next week'"""
        email_date = datetime(2024, 1, 10)
        subject = "Project Update"
        body = "The site visit is scheduled for next week. Please confirm availability."
        
        result = self.parser.parse_email(subject, body, email_date)
        
        # Should find an event for January 17 (7 days from email date)
        next_week_events = [e for e in result.events if e.event_date == date(2024, 1, 17)]
        self.assertGreaterEqual(len(next_week_events), 1)
    
    def test_extract_in_x_days(self):
        """Test extraction of 'in X days'"""
        email_date = datetime(2024, 1, 10)
        subject = "Deadline Reminder"
        body = "The report is due in 5 days. Please complete your sections."
        
        result = self.parser.parse_email(subject, body, email_date)
        
        future_events = [e for e in result.events if e.event_date == date(2024, 1, 15)]
        self.assertGreaterEqual(len(future_events), 1)


class EmailTimelineParserPhaseInferenceTest(TestCase):
    """Test project phase inference"""
    
    def setUp(self):
        self.parser = EmailTimelineParser()
    
    def test_infer_proposal_phase(self):
        """Test inference of proposal phase"""
        text = "Please find attached our fee proposal for the acoustical consulting services."
        
        phase = self.parser._infer_phase(text)
        self.assertEqual(phase, 'Proposal')
    
    def test_infer_construction_admin_phase(self):
        """Test inference of construction administration phase"""
        text = "Please review the attached RFI response. We have also completed the submittal review for the acoustic panels."
        
        phase = self.parser._infer_phase(text)
        self.assertEqual(phase, 'Construction Administration')
    
    def test_infer_site_visit_phase(self):
        """Test inference of site visit/testing phase"""
        text = "The field measurement results from last week's acoustic testing are attached."
        
        phase = self.parser._infer_phase(text)
        self.assertEqual(phase, 'Site Visit/Testing')
    
    def test_infer_closeout_phase(self):
        """Test inference of closeout phase"""
        text = "Project complete. Please find attached the final invoice for this project closeout."
        
        phase = self.parser._infer_phase(text)
        self.assertEqual(phase, 'Closeout')


class EmailTimelineParserStatusIndicatorTest(TestCase):
    """Test status indicator extraction"""
    
    def setUp(self):
        self.parser = EmailTimelineParser()
        self.email_date = datetime(2024, 1, 10)
    
    def test_extract_waiting_on_client_indicator(self):
        """Test extraction of 'waiting on client' indicator"""
        subject = "Awaiting Client Response"
        body = "We are waiting for your review comments before proceeding with the final report."
        
        result = self.parser.parse_email(subject, body, self.email_date)
        
        waiting_indicators = [i for i in result.indicators 
                             if i.indicator_type == IndicatorType.WAITING_ON_CLIENT]
        self.assertGreaterEqual(len(waiting_indicators), 1)
    
    def test_extract_deliverable_sent_indicator(self):
        """Test extraction of 'deliverable sent' indicator"""
        subject = "Draft Report Attached"
        body = "Please find attached the draft acoustical report for your review."
        
        result = self.parser.parse_email(subject, body, self.email_date)
        
        sent_indicators = [i for i in result.indicators 
                          if i.indicator_type == IndicatorType.DELIVERABLE_SENT]
        self.assertGreaterEqual(len(sent_indicators), 1)
    
    def test_extract_on_hold_indicator(self):
        """Test extraction of 'on hold' indicator"""
        subject = "Project Status Update"
        body = "The project has been put on hold pending client budget approval."
        
        result = self.parser.parse_email(subject, body, self.email_date)
        
        hold_indicators = [i for i in result.indicators 
                          if i.indicator_type == IndicatorType.ON_HOLD]
        self.assertGreaterEqual(len(hold_indicators), 1)


class EmailTimelineParserBatchProcessingTest(TestCase):
    """Test batch processing of emails"""
    
    def setUp(self):
        self.parser = EmailTimelineParser()
    
    def test_batch_processing(self):
        """Test processing multiple emails"""
        emails = [
            {
                'subject': 'Project Kickoff',
                'body': 'Meeting scheduled for 01/15/2024 to kick off the project.',
                'date': datetime(2024, 1, 10)
            },
            {
                'subject': 'Draft Report',
                'body': 'Draft report due 02/01/2024. Please review the proposal phase.',
                'date': datetime(2024, 1, 20)
            },
            {
                'subject': 'Final Report Deadline',
                'body': 'The final report deadline is 02/28/2024.',
                'date': datetime(2024, 2, 15)
            }
        ]
        
        result = self.parser.parse_emails_batch(emails)
        
        self.assertEqual(result['total_emails_processed'], 3)
        self.assertGreater(len(result['events']), 0)
        self.assertIn('inferred_current_phase', result)
    
    def test_phase_voting(self):
        """Test that phase inference uses voting across emails"""
        emails = [
            {'subject': 'Proposal', 'body': 'Fee proposal attached.', 'date': datetime(2024, 1, 1)},
            {'subject': 'Proposal Review', 'body': 'Proposal comments.', 'date': datetime(2024, 1, 2)},
            {'subject': 'Report Draft', 'body': 'Draft report attached.', 'date': datetime(2024, 1, 3)},
        ]
        
        result = self.parser.parse_emails_batch(emails)
        
        # Proposal should win with 2 votes vs 1 for Report
        self.assertEqual(result['inferred_current_phase'], 'Proposal')


class EmailTimelineParserDeduplicationTest(TestCase):
    """Test event deduplication"""
    
    def setUp(self):
        self.parser = EmailTimelineParser()
    
    def test_deduplicate_same_date_type(self):
        """Test that duplicate events are removed"""
        email_date = datetime(2024, 1, 10)
        subject = "Double Deadline"
        body = "The deadline is 01/20/2024. Remember the deadline on 01/20/2024 for the report."
        
        result = self.parser.parse_email(subject, body, email_date)
        
        # Should only have one deadline event for 01/20
        deadline_events = [e for e in result.events 
                          if e.event_type == EventType.DEADLINE and e.event_date == date(2024, 1, 20)]
        self.assertEqual(len(deadline_events), 1)

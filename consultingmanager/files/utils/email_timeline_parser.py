"""
Email Timeline Parser

Extracts timeline waypoints and project status indicators from email content.
Uses pattern matching, regex, and heuristics specific to consulting workflows.
"""

import re
import logging
from datetime import datetime, date, timedelta
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


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


class IndicatorType(Enum):
    PHASE_START = 'phase_start'
    PHASE_COMPLETE = 'phase_complete'
    DELIVERABLE_SENT = 'deliverable_sent'
    CLIENT_APPROVAL = 'client_approval'
    WAITING_ON_CLIENT = 'waiting_on_client'
    ACTIVE_WORK = 'active_work'
    ON_HOLD = 'on_hold'
    ISSUE_FLAGGED = 'issue_flagged'


@dataclass
class ExtractedEvent:
    """Represents an extracted timeline event from email"""
    event_type: EventType
    event_date: date
    description: str
    extracted_text: str
    confidence: str  # 'high', 'medium', 'low'
    extraction_method: str


@dataclass
class ExtractedIndicator:
    """Represents an extracted status indicator from email"""
    indicator_type: IndicatorType
    indicator_date: date
    description: str
    extracted_text: str
    confidence: str
    inferred_phase: str = ''


@dataclass
class ParseResult:
    """Result of parsing an email for timeline information"""
    events: List[ExtractedEvent] = field(default_factory=list)
    indicators: List[ExtractedIndicator] = field(default_factory=list)
    inferred_phase: str = ''
    errors: List[str] = field(default_factory=list)


class EmailTimelineParser:
    """Parse emails for timeline waypoints and status indicators"""
    
    # Date patterns for extraction (ordered by specificity)
    DATE_PATTERNS = [
        # Full date formats
        (r'(\d{1,2}/\d{1,2}/\d{4})', '%m/%d/%Y'),           # 01/15/2024
        (r'(\d{1,2}/\d{1,2}/\d{2})', '%m/%d/%y'),           # 01/15/24
        (r'(\d{1,2}-\d{1,2}-\d{4})', '%m-%d-%Y'),           # 01-15-2024
        (r'(\d{1,2}-\d{1,2}-\d{2})', '%m-%d-%y'),           # 01-15-24
        (r'(\w+ \d{1,2},? \d{4})', None),                   # January 15, 2024 (special handling)
        (r'(\d{1,2} \w+ \d{4})', None),                     # 15 January 2024 (special handling)
        (r'(\d{4}-\d{2}-\d{2})', '%Y-%m-%d'),               # 2024-01-15 (ISO)
    ]
    
    # Month names for parsing
    MONTH_NAMES = {
        'january': 1, 'jan': 1,
        'february': 2, 'feb': 2,
        'march': 3, 'mar': 3,
        'april': 4, 'apr': 4,
        'may': 5,
        'june': 6, 'jun': 6,
        'july': 7, 'jul': 7,
        'august': 8, 'aug': 8,
        'september': 9, 'sep': 9, 'sept': 9,
        'october': 10, 'oct': 10,
        'november': 11, 'nov': 11,
        'december': 12, 'dec': 12,
    }
    
    # Keywords for event type detection (consulting-specific)
    EVENT_KEYWORDS = {
        EventType.DEADLINE: [
            'due', 'deadline', 'due date', 'by', 'before', 'no later than', 
            'submit by', 'need by', 'required by', 'expected by', 'target date',
            'must be completed', 'completion date'
        ],
        EventType.MEETING: [
            'meeting', 'call', 'conference', 'discussion', 'presentation',
            'webinar', 'teams meeting', 'zoom', 'phone call', 'teleconference'
        ],
        EventType.KICKOFF: [
            'kick-off', 'kickoff', 'kick off', 'project start', 'project kickoff',
            'project kick-off', 'initiation meeting', 'start meeting'
        ],
        EventType.SUBMITTAL: [
            'submit', 'deliver', 'send', 'provide', 'transmit', 'issue',
            'draft', 'final report', 'deliverable', 'package', 'transmittal',
            'will send', 'sending', 'attached is', 'please find attached'
        ],
        EventType.SITE_VISIT: [
            'site visit', 'field work', 'field visit', 'on-site', 'onsite',
            'measurement', 'testing', 'survey', 'inspection', 'field measurement',
            'site survey', 'field testing', 'acoustic testing', 'noise measurement'
        ],
        EventType.REVIEW: [
            'review', 'comment', 'feedback', 'response', 'revision',
            'review period', 'comment period', 'redline', 'markup',
            'review and comment', 'client review'
        ],
        EventType.APPROVAL: [
            'approval', 'approve', 'approved', 'sign-off', 'signoff', 'sign off',
            'authorization', 'authorize', 'accept', 'accepted', 'agreement'
        ],
        EventType.COMPLETION: [
            'complete', 'completed', 'finished', 'done', 'final',
            'closeout', 'close-out', 'close out', 'wrapped up', 'concluded',
            'project complete', 'project completed'
        ],
        EventType.INVOICE: [
            'invoice', 'payment', 'billing', 'fee', 'cost', 'pay',
            'remittance', 'invoice attached', 'please pay', 'payment due'
        ],
        EventType.CHANGE_ORDER: [
            'change order', 'additional services', 'scope change', 'amendment',
            'modification', 'additional work', 'extra work', 'added scope'
        ],
    }
    
    # Status indicator patterns
    STATUS_PATTERNS = {
        IndicatorType.DELIVERABLE_SENT: [
            'attached is', 'please find attached', 'sending you', 'here is',
            'enclosed', 'transmitting', 'delivering', 'submitting'
        ],
        IndicatorType.CLIENT_APPROVAL: [
            'approved', 'client approved', 'authorization received',
            'proceed with', 'go ahead', 'green light', 'accepted'
        ],
        IndicatorType.WAITING_ON_CLIENT: [
            'waiting for', 'awaiting', 'pending your', 'need your',
            'please provide', 'please send', 'please review', 'at your earliest'
        ],
        IndicatorType.ON_HOLD: [
            'on hold', 'paused', 'delayed', 'postponed', 'suspended',
            'put on hold', 'holding off'
        ],
        IndicatorType.ISSUE_FLAGGED: [
            'issue', 'problem', 'concern', 'delay', 'challenge',
            'difficulty', 'obstacle', 'risk', 'warning'
        ],
    }
    
    # Phase detection patterns (acoustic/consulting specific)
    PHASE_PATTERNS = {
        'Proposal': ['proposal', 'quote', 'estimate', 'fee proposal', 'cost estimate'],
        'Contract': ['contract', 'agreement', 'authorization', 'NTP', 'notice to proceed', 
                     'executed agreement', 'signed contract'],
        'Design': ['design', 'schematic', 'SD', 'DD', 'design development',
                   'preliminary design', 'concept design'],
        'Construction Documents': ['CD', 'construction documents', 'permit', 'permit set',
                                   'bid documents', 'construction drawings'],
        'Bidding': ['bid', 'bidding', 'contractor selection', 'bid opening',
                    'contractor bids', 'bidding phase'],
        'Construction Administration': ['CA', 'construction admin', 'RFI', 'submittal review',
                                        'field observation', 'punch list', 'construction phase'],
        'Site Visit/Testing': ['site visit', 'field work', 'testing', 'measurement',
                               'field measurement', 'acoustic testing', 'noise monitoring'],
        'Report': ['report', 'final report', 'draft report', 'deliverable', 
                   'technical report', 'study'],
        'Closeout': ['closeout', 'close-out', 'project complete', 'final invoice',
                     'project closeout', 'wrap up']
    }
    
    # Relative date patterns
    RELATIVE_DATE_PATTERNS = [
        (r'\b(tomorrow)\b', 1),
        (r'\b(next week)\b', 7),
        (r'\b(next monday)\b', None),  # Special handling
        (r'\b(next tuesday)\b', None),
        (r'\b(next wednesday)\b', None),
        (r'\b(next thursday)\b', None),
        (r'\b(next friday)\b', None),
        (r'\b(end of week)\b', None),
        (r'\b(end of month)\b', None),
        (r'\b(in (\d+) days?)\b', None),
        (r'\b(in (\d+) weeks?)\b', None),
    ]

    def __init__(self):
        self.current_year = datetime.now().year

    def parse_email(self, subject: str, body: str, email_date: datetime) -> ParseResult:
        """
        Extract timeline events and status indicators from email content.
        
        Args:
            subject: Email subject line
            body: Email body text
            email_date: Date the email was sent
            
        Returns:
            ParseResult containing extracted events, indicators, and inferred phase
        """
        result = ParseResult()
        full_text = f"{subject}\n{body}"
        
        try:
            # Extract explicit dates and classify events
            dates_found = self._extract_dates(full_text)
            for date_str, parsed_date, context in dates_found:
                event = self._classify_event(context, parsed_date, date_str)
                if event:
                    result.events.append(event)
            
            # Extract relative dates
            relative_events = self._extract_relative_dates(full_text, email_date)
            result.events.extend(relative_events)
            
            # Extract status indicators
            indicators = self._extract_status_indicators(full_text, email_date.date() if isinstance(email_date, datetime) else email_date)
            result.indicators.extend(indicators)
            
            # Infer project phase
            result.inferred_phase = self._infer_phase(full_text)
            
            # De-duplicate events by date and type
            result.events = self._deduplicate_events(result.events)
            
        except Exception as e:
            logger.error(f"Error parsing email: {str(e)}")
            result.errors.append(str(e))
        
        return result

    def _extract_dates(self, text: str) -> List[Tuple[str, date, str]]:
        """Extract dates and their surrounding context from text"""
        results = []
        
        for pattern, date_format in self.DATE_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                date_str = match.group(1)
                parsed = self._parse_date(date_str, date_format)
                
                if parsed:
                    # Get surrounding context (150 chars before and after)
                    start = max(0, match.start() - 150)
                    end = min(len(text), match.end() + 150)
                    context = text[start:end]
                    results.append((date_str, parsed, context))
        
        return results

    def _parse_date(self, date_str: str, date_format: Optional[str]) -> Optional[date]:
        """Parse a date string into a date object"""
        try:
            if date_format:
                return datetime.strptime(date_str, date_format).date()
            else:
                # Handle month name formats
                return self._parse_month_name_date(date_str)
        except (ValueError, AttributeError):
            return None

    def _parse_month_name_date(self, date_str: str) -> Optional[date]:
        """Parse dates with month names like 'January 15, 2024' or '15 January 2024'"""
        # Try "Month DD, YYYY" format
        match = re.match(r'(\w+)\s+(\d{1,2}),?\s+(\d{4})', date_str, re.IGNORECASE)
        if match:
            month_str, day, year = match.groups()
            month = self.MONTH_NAMES.get(month_str.lower())
            if month:
                try:
                    return date(int(year), month, int(day))
                except ValueError:
                    pass
        
        # Try "DD Month YYYY" format
        match = re.match(r'(\d{1,2})\s+(\w+)\s+(\d{4})', date_str, re.IGNORECASE)
        if match:
            day, month_str, year = match.groups()
            month = self.MONTH_NAMES.get(month_str.lower())
            if month:
                try:
                    return date(int(year), month, int(day))
                except ValueError:
                    pass
        
        return None

    def _classify_event(self, context: str, event_date: date, date_str: str) -> Optional[ExtractedEvent]:
        """Classify an event based on surrounding context"""
        context_lower = context.lower()
        
        # Score each event type based on keyword matches
        best_type = None
        best_score = 0
        best_keywords = []
        
        for event_type, keywords in self.EVENT_KEYWORDS.items():
            score = 0
            matched_keywords = []
            for keyword in keywords:
                if keyword.lower() in context_lower:
                    # Weight longer keywords more heavily
                    score += len(keyword.split())
                    matched_keywords.append(keyword)
            
            if score > best_score:
                best_score = score
                best_type = event_type
                best_keywords = matched_keywords
        
        if best_type and best_score > 0:
            # Determine confidence based on score and keyword specificity
            if best_score >= 3 or any(len(kw.split()) >= 2 for kw in best_keywords):
                confidence = 'high'
            elif best_score >= 2:
                confidence = 'medium'
            else:
                confidence = 'low'
            
            # Create description from context
            description = self._extract_description(context, date_str, best_keywords)
            
            return ExtractedEvent(
                event_type=best_type,
                event_date=event_date,
                description=description,
                extracted_text=context.strip(),
                confidence=confidence,
                extraction_method='keyword_match'
            )
        
        return None

    def _extract_description(self, context: str, date_str: str, keywords: List[str]) -> str:
        """Extract a meaningful description from the context"""
        # Find the sentence containing the date
        sentences = re.split(r'[.!?\n]', context)
        
        for sentence in sentences:
            if date_str in sentence or any(kw in sentence.lower() for kw in keywords):
                # Clean up the sentence
                desc = sentence.strip()
                # Remove excessive whitespace
                desc = re.sub(r'\s+', ' ', desc)
                if len(desc) > 10:
                    return desc[:200]
        
        # Fallback: use keywords with date
        if keywords:
            return f"{keywords[0].title()} - {date_str}"
        return f"Event on {date_str}"

    def _extract_relative_dates(self, text: str, email_date: datetime) -> List[ExtractedEvent]:
        """Extract events with relative dates like 'tomorrow', 'next week'"""
        events = []
        text_lower = text.lower()
        base_date = email_date.date() if isinstance(email_date, datetime) else email_date
        
        # Check for "tomorrow"
        if 'tomorrow' in text_lower:
            tomorrow = base_date + timedelta(days=1)
            context = self._get_context_around(text, 'tomorrow')
            event = self._classify_event(context, tomorrow, 'tomorrow')
            if event:
                event.extraction_method = 'relative_date'
                events.append(event)
        
        # Check for "next week"
        if 'next week' in text_lower:
            next_week = base_date + timedelta(days=7)
            context = self._get_context_around(text, 'next week')
            event = self._classify_event(context, next_week, 'next week')
            if event:
                event.extraction_method = 'relative_date'
                events.append(event)
        
        # Check for "in X days/weeks"
        days_match = re.search(r'in (\d+) days?', text_lower)
        if days_match:
            days = int(days_match.group(1))
            future_date = base_date + timedelta(days=days)
            context = self._get_context_around(text, days_match.group(0))
            event = self._classify_event(context, future_date, f'in {days} days')
            if event:
                event.extraction_method = 'relative_date'
                events.append(event)
        
        weeks_match = re.search(r'in (\d+) weeks?', text_lower)
        if weeks_match:
            weeks = int(weeks_match.group(1))
            future_date = base_date + timedelta(weeks=weeks)
            context = self._get_context_around(text, weeks_match.group(0))
            event = self._classify_event(context, future_date, f'in {weeks} weeks')
            if event:
                event.extraction_method = 'relative_date'
                events.append(event)
        
        return events

    def _get_context_around(self, text: str, phrase: str) -> str:
        """Get context around a phrase in the text"""
        idx = text.lower().find(phrase.lower())
        if idx >= 0:
            start = max(0, idx - 150)
            end = min(len(text), idx + len(phrase) + 150)
            return text[start:end]
        return ""

    def _extract_status_indicators(self, text: str, email_date: date) -> List[ExtractedIndicator]:
        """Extract project status indicators from email text"""
        indicators = []
        text_lower = text.lower()
        
        for indicator_type, patterns in self.STATUS_PATTERNS.items():
            for pattern in patterns:
                if pattern.lower() in text_lower:
                    context = self._get_context_around(text, pattern)
                    if context:
                        # Determine confidence
                        confidence = 'medium'
                        if len(pattern.split()) >= 2:
                            confidence = 'high'
                        
                        # Infer phase from context
                        inferred_phase = self._infer_phase(context)
                        
                        indicators.append(ExtractedIndicator(
                            indicator_type=indicator_type,
                            indicator_date=email_date,
                            description=f"{indicator_type.value.replace('_', ' ').title()}: {pattern}",
                            extracted_text=context.strip(),
                            confidence=confidence,
                            inferred_phase=inferred_phase
                        ))
                        break  # Only one indicator per type per email
        
        return indicators

    def _infer_phase(self, text: str) -> str:
        """Infer the project phase from text content"""
        text_lower = text.lower()
        phase_scores: Dict[str, int] = {}
        
        for phase, keywords in self.PHASE_PATTERNS.items():
            score = 0
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    # Weight longer keywords more heavily
                    score += len(keyword.split())
            if score > 0:
                phase_scores[phase] = score
        
        if phase_scores:
            return max(phase_scores, key=phase_scores.get)
        return ''

    def _deduplicate_events(self, events: List[ExtractedEvent]) -> List[ExtractedEvent]:
        """Remove duplicate events (same date and type)"""
        seen = set()
        unique_events = []
        
        for event in events:
            key = (event.event_date, event.event_type)
            if key not in seen:
                seen.add(key)
                unique_events.append(event)
            else:
                # Keep the one with higher confidence
                for i, existing in enumerate(unique_events):
                    if (existing.event_date, existing.event_type) == key:
                        if self._confidence_rank(event.confidence) > self._confidence_rank(existing.confidence):
                            unique_events[i] = event
                        break
        
        return unique_events

    def _confidence_rank(self, confidence: str) -> int:
        """Return numeric rank for confidence level"""
        ranks = {'high': 3, 'medium': 2, 'low': 1}
        return ranks.get(confidence, 0)

    def parse_emails_batch(self, emails: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Parse a batch of emails and aggregate results.
        
        Args:
            emails: List of email dicts with 'subject', 'body', 'date' keys
            
        Returns:
            Aggregated results including all events, indicators, and overall phase inference
        """
        all_events = []
        all_indicators = []
        phase_votes: Dict[str, int] = {}
        
        for email in emails:
            result = self.parse_email(
                subject=email.get('subject', ''),
                body=email.get('body', ''),
                email_date=email.get('date', datetime.now())
            )
            
            all_events.extend(result.events)
            all_indicators.extend(result.indicators)
            
            if result.inferred_phase:
                phase_votes[result.inferred_phase] = phase_votes.get(result.inferred_phase, 0) + 1
        
        # Determine most likely current phase
        current_phase = ''
        if phase_votes:
            current_phase = max(phase_votes, key=phase_votes.get)
        
        return {
            'events': all_events,
            'indicators': all_indicators,
            'phase_votes': phase_votes,
            'inferred_current_phase': current_phase,
            'total_emails_processed': len(emails)
        }

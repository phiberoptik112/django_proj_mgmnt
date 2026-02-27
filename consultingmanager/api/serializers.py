import re
from rest_framework import serializers
from projects.models import Project
from clients.models import Client
from files.models import File, Proposal


class ProjectSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source='client.name', read_only=True)

    class Meta:
        model = Project
        fields = [
            'id', 'title', 'client_name', 'status', 'budget',
            'description', 'start_date', 'end_date',
        ]


class FileSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField(source='uploaded_at')

    class Meta:
        model = File
        fields = ['id', 'title', 'file_type', 'url', 'created_at']

    def get_url(self, obj):
        return obj.file.url if obj.file else None


class ProposalSerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField()
    amount = serializers.SerializerMethodField()

    class Meta:
        model = Proposal
        fields = ['id', 'title', 'status', 'amount']

    def get_title(self, obj):
        if obj.recipient_company:
            return f"{obj.recipient_company} Proposal"
        return f"Proposal {obj.id}"

    def get_amount(self, obj):
        compensation = obj.compensation
        if not isinstance(compensation, dict):
            return None
        for key in ('total', 'amount', 'fee'):
            value = compensation.get(key)
            if value is not None:
                try:
                    return str(value)
                except (TypeError, ValueError):
                    continue
        return None


class ClientSerializer(serializers.ModelSerializer):
    contact_name = serializers.CharField(source='billing_contact', read_only=True)

    class Meta:
        model = Client
        fields = ['id', 'name', 'contact_name', 'email', 'phone', 'address']


# ---------------------------------------------------------------------------
# Standards extraction helper
# ---------------------------------------------------------------------------

_STANDARDS_PATTERN = re.compile(
    r'\b(ASTM\s+\w[\w-]+)'
    r'|(ISO\s+\d[\d\-\.]+)'
    r'|(ANSI\s+\w[\w\.\-]+)'
    r'|(IEC\s+\d[\d\-]+)',
    re.IGNORECASE
)

_PREFIX_MAP = {
    'astm': 'ASTM',
    'iso': 'ISO',
    'ansi': 'ANSI',
    'iec': 'IEC',
}


def extract_standards_from_text(text):
    """
    Parse free text and return a list of standard references.
    Example: [{'type': 'ASTM', 'id': 'ASTM E336-17a'}, ...]
    Deduplicates by uppercased full reference string.
    """
    seen = set()
    results = []
    for match in _STANDARDS_PATTERN.finditer(text):
        full_ref = match.group(0).strip()
        full_ref = re.sub(r'\s+', ' ', full_ref)
        key = full_ref.upper()
        if key in seen:
            continue
        seen.add(key)
        prefix = full_ref.split()[0].lower()
        std_type = _PREFIX_MAP.get(prefix, full_ref.split()[0].upper())
        results.append({'type': std_type, 'id': full_ref})
    return results

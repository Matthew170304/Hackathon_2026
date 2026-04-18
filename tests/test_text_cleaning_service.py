from app.schemas.incident_schemas import IncidentCreateRequest
from app.services.text_cleaning import TextCleaningService


def test_clean_text_returns_empty_string_for_none_and_placeholders():
    service = TextCleaningService()

    assert service.clean_text(None) == ''
    assert service.clean_text('-No value-') == ''
    assert service.clean_text(' n/A ') == ''


def test_clean_text_normalizes_whitespace_and_location_separators():
    service = TextCleaningService()

    assert service.clean_text('  Employee   slipped\nnear\tmachine  ') == 'Employee slipped near machine'
    assert service.clean_text('Denmark- Nordborg   -Nordborgvej 81') == 'Denmark - Nordborg - Nordborgvej 81'


def test_build_analysis_text_uses_cleaned_non_empty_incident_fields():
    service = TextCleaningService()
    incident = IncidentCreateRequest(
        external_case_id=None,
        case_type=None,
        location='Denmark- Nordborg   -Nordborgvej 81',
        responsible_entity=None,
        occurred_at=None,
        title='  Wet floor ',
        description='Operator   slipped\nnear machine.',
        activity=None,
        severity_level=None,
        recurrence_frequency=None,
        classification=None,
        cause_category=None,
        cause=None,
        immediate_actions=' -No value- ',
        action_description=None,
        validation_description=None,
    )

    assert service.build_analysis_text(incident) == (
        'Title: Wet floor | '
        'Description: Operator slipped near machine. | '
        'Location: Denmark - Nordborg - Nordborgvej 81'
    )


def test_extract_country_and_site_from_location():
    assert TextCleaningService.extract_country_and_site(None) == (None, None)
    assert TextCleaningService.extract_country_and_site('-No value-') == (None, None)
    assert TextCleaningService.extract_country_and_site('Denmark') == ('Denmark', None)
    assert TextCleaningService.extract_country_and_site('Denmark - Nordborg') == ('Denmark', 'Nordborg')
    assert TextCleaningService.extract_country_and_site(
        'Denmark- Nordborg   -Nordborgvej 81'
    ) == ('Denmark', 'Nordborg')

from .models import AdmissionSettings


def get_admission_settings():
    settings, _ = AdmissionSettings.objects.get_or_create(pk=1)
    return settings


def is_admissions_open():
    return get_admission_settings().is_open

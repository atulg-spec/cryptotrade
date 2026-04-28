from django.utils import timezone
from django.db.models.functions import TruncDay
from django.db.models import Count
import json
from django.core.serializers.json import DjangoJSONEncoder
from django.utils.timezone import now, timedelta
from dashboard.models import SiteSettings

def site_settings_context(request):
    try:
        site_settings = SiteSettings.objects.first()
    except SiteSettings.DoesNotExist:
        site_settings = None

    context = {
        'site_settings': site_settings,
    }
    return context
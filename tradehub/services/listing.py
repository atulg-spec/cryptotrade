from datetime import timedelta

from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.utils import timezone


def apply_time_filter(queryset, time_filter, field_name="created_at"):
    now = timezone.now()
    date_lookup = f"{field_name}__date"
    gte_lookup = f"{field_name}__gte"

    if time_filter == "today":
        return queryset.filter(**{date_lookup: now.date()})
    if time_filter == "week":
        return queryset.filter(**{gte_lookup: now - timedelta(days=7)})
    if time_filter == "month":
        return queryset.filter(**{gte_lookup: now - timedelta(days=30)})
    return queryset


def paginate_queryset(queryset, page_number, per_page=10):
    paginator = Paginator(queryset, per_page)
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)
    return page_obj, paginator

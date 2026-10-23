from datetime import date

from django.contrib import messages


def get_inventory_date_range(request, start_param='date_from', end_param='date_to', legacy_start=(), legacy_end=()):
    start_value = request.GET.get(start_param)
    end_value = request.GET.get(end_param)
    if not start_value:
        start_value = next((request.GET.get(name) for name in legacy_start if request.GET.get(name)), '')
    if not end_value:
        end_value = next((request.GET.get(name) for name in legacy_end if request.GET.get(name)), '')

    try:
        start_date = date.fromisoformat(start_value) if start_value else None
        end_date = date.fromisoformat(end_value) if end_value else None
    except ValueError:
        messages.error(request, 'Enter valid From and To dates.')
        return None, None, False

    if start_date and end_date and start_date > end_date:
        messages.error(request, 'From date must be on or before To date.')
        return start_date, end_date, False

    return start_date, end_date, True

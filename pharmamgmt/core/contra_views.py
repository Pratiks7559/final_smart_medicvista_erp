# ============================================
# CONTRA ENTRY MODULE - VIEWS
# This file can be deleted to remove contra functionality
# ============================================

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Sum, Q
from django.utils import timezone
from datetime import datetime, timedelta
from .models import ContraEntry, Web_User
from .year_filter_utils import apply_year_filter, get_current_financial_year, get_financial_year_dates
import json

@login_required
def contra_list(request):
    """List all contra entries with filters"""
    # Get filter parameters
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    contra_type = request.GET.get('contra_type')
    
    # Base queryset with FY filter
    contras = ContraEntry.objects.all()
    contras = apply_year_filter(contras, request, 'contra_date')

    # Apply additional filters
    if start_date:
        contras = contras.filter(contra_date__gte=start_date)
    if end_date:
        contras = contras.filter(contra_date__lte=end_date)
    if contra_type:
        contras = contras.filter(contra_type=contra_type)
    
    # Calculate totals
    bank_to_cash_total = contras.filter(contra_type='BANK_TO_CASH').aggregate(Sum('amount'))['amount__sum'] or 0
    cash_to_bank_total = contras.filter(contra_type='CASH_TO_BANK').aggregate(Sum('amount'))['amount__sum'] or 0

    # FY info for display
    selected_year = request.session.get('selected_year', get_current_financial_year())
    fy_label = f"FY {selected_year}-{str(selected_year + 1)[2:]}"
    
    context = {
        'title': 'Contra Entries',
        'contras': contras,
        'bank_to_cash_total': bank_to_cash_total,
        'cash_to_bank_total': cash_to_bank_total,
        'start_date': start_date,
        'end_date': end_date,
        'contra_type': contra_type,
        'fy_label': fy_label,
    }
    return render(request, 'contra/contra_list.html', context)

@login_required
def add_contra(request):
    """Add new contra entry"""
    if request.method == 'POST':
        try:
            contra_date = request.POST.get('contra_date')
            contra_type = request.POST.get('contra_type')
            amount = float(request.POST.get('amount'))
            from_account = request.POST.get('from_account')
            to_account = request.POST.get('to_account')
            reference_no = request.POST.get('reference_no', '')
            narration = request.POST.get('narration', '')
            
            # Validation
            if amount <= 0:
                messages.error(request, 'Amount must be greater than 0')
                return redirect('add_contra')
            
            if from_account == to_account:
                messages.error(request, 'From and To accounts cannot be same')
                return redirect('add_contra')
            
            # Create contra entry
            contra = ContraEntry.objects.create(
                contra_date=contra_date,
                contra_type=contra_type,
                amount=amount,
                from_account=from_account,
                to_account=to_account,
                reference_no=reference_no,
                narration=narration,
                created_by=request.user
            )
            
            messages.success(request, f'Contra Entry #{contra.contra_no} created successfully!')
            return redirect('contra_list')
            
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
            return redirect('add_contra')
    
    context = {
        'title': 'Add Contra Entry',
        'today': timezone.now().date()
    }
    return render(request, 'contra/add_contra.html', context)

@login_required
def edit_contra(request, contra_id):
    """Edit existing contra entry"""
    contra = get_object_or_404(ContraEntry, contra_id=contra_id)
    
    if request.method == 'POST':
        try:
            contra.contra_date = request.POST.get('contra_date')
            contra.contra_type = request.POST.get('contra_type')
            contra.amount = float(request.POST.get('amount'))
            contra.from_account = request.POST.get('from_account')
            contra.to_account = request.POST.get('to_account')
            contra.reference_no = request.POST.get('reference_no', '')
            contra.narration = request.POST.get('narration', '')
            
            # Validation
            if contra.amount <= 0:
                messages.error(request, 'Amount must be greater than 0')
                return redirect('edit_contra', contra_id=contra_id)
            
            if contra.from_account == contra.to_account:
                messages.error(request, 'From and To accounts cannot be same')
                return redirect('edit_contra', contra_id=contra_id)
            
            contra.save()
            messages.success(request, f'Contra Entry #{contra.contra_no} updated successfully!')
            return redirect('contra_list')
            
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
            return redirect('edit_contra', contra_id=contra_id)
    
    context = {
        'title': 'Edit Contra Entry',
        'contra': contra
    }
    return render(request, 'contra/edit_contra.html', context)

@login_required
def delete_contra(request, contra_id):
    """Delete contra entry (admin only)"""
    contra = get_object_or_404(ContraEntry, contra_id=contra_id)
    
    if request.user.user_type.lower() != 'admin':
        if request.method == 'POST':
            return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
        messages.error(request, "You don't have permission to delete contra entries")
        return redirect('contra_list')
    
    if request.method == 'POST':
        contra_no = contra.contra_no
        contra.delete()
        messages.success(request, f'Contra Entry #{contra_no} deleted successfully!')
        return redirect('contra_list')
    
    context = {
        'title': 'Delete Contra Entry',
        'contra': contra
    }
    return render(request, 'contra/delete_contra.html', context)

@login_required
def contra_detail(request, contra_id):
    """View contra entry details"""
    contra = get_object_or_404(ContraEntry, contra_id=contra_id)
    
    context = {
        'title': f'Contra Entry #{contra.contra_no}',
        'contra': contra
    }
    return render(request, 'contra/contra_detail.html', context)

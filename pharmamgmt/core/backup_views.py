from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, FileResponse
from django.conf import settings
import os
import subprocess
from datetime import datetime

MYSQL_BIN_DIR = r"C:\Program Files\MySQL\MySQL Server 8.0\bin"


def get_mysql_config():
    db = settings.DATABASES['default']
    return {
        'host':     db.get('HOST', 'localhost'),
        'port':     str(db.get('PORT', 3306)),
        'user':     db.get('USER', 'root'),
        'password': db.get('PASSWORD', 'Pratik@123'),
        'name':     db.get('NAME', ''),
    }


@login_required
def backup_list(request):
    if request.user.user_type != 'admin':
        messages.error(request, "Only admins can access backup management.")
        return redirect('dashboard')

    backup_dir = 'backups'
    os.makedirs(backup_dir, exist_ok=True)

    backups = []
    for filename in os.listdir(backup_dir):
        if filename.endswith('.sql') or filename.endswith('.dump'):
            filepath = os.path.join(backup_dir, filename)
            size = os.path.getsize(filepath) / (1024 * 1024)
            modified = datetime.fromtimestamp(os.path.getmtime(filepath))
            backups.append({
                'filename': filename,
                'size': f'{size:.2f} MB',
                'date': modified.strftime('%Y-%m-%d %H:%M:%S')
            })

    backups.sort(key=lambda x: x['date'], reverse=True)

    context = {
        'backups': backups,
        'title': 'Database Backups'
    }
    return render(request, 'system/backup_list.html', context)


@login_required
def create_backup(request):
    if request.user.user_type != 'admin':
        return JsonResponse({'success': False, 'error': 'Permission denied'})

    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_dir = 'backups'
        os.makedirs(backup_dir, exist_ok=True)

        cfg = get_mysql_config()
        filename = f'backup_{timestamp}.sql'
        destination = os.path.join(backup_dir, filename)

        mysqldump = os.path.join(MYSQL_BIN_DIR, 'mysqldump.exe')

        cmd = [
            mysqldump,
            f'-h{cfg["host"]}',
            f'-P{cfg["port"]}',
            f'-u{cfg["user"]}',
            f'-p{cfg["password"]}',
            '--single-transaction',
            '--routines',
            '--triggers',
            '--add-drop-table',
            '--complete-insert',
            cfg['name'],
        ]

        with open(destination, 'w', encoding='utf-8') as outfile:
            result = subprocess.run(
                cmd,
                stdout=outfile,
                stderr=subprocess.PIPE,
                text=True
            )

        if result.returncode != 0:
            # Remove empty file on failure
            if os.path.exists(destination):
                os.remove(destination)
            return JsonResponse({'success': False, 'error': f'Backup failed: {result.stderr}'})

        backup_size = os.path.getsize(destination)
        return JsonResponse({
            'success': True,
            'message': f'Backup created successfully! Size: {backup_size / (1024*1024):.2f} MB',
            'filename': filename
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def restore_backup(request):
    if request.user.user_type != 'admin':
        return JsonResponse({'success': False, 'error': 'Permission denied'})

    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'})

    try:
        from django.db import connection
        connection.close()

        filename = request.POST.get('filename')
        backup_path = os.path.join('backups', filename)

        if not os.path.exists(backup_path):
            return JsonResponse({'success': False, 'error': 'Backup file not found'})

        cfg = get_mysql_config()
        mysql = os.path.join(MYSQL_BIN_DIR, 'mysql.exe')

        cmd = [
            mysql,
            f'-h{cfg["host"]}',
            f'-P{cfg["port"]}',
            f'-u{cfg["user"]}',
            f'-p{cfg["password"]}',
            cfg['name'],
        ]

        with open(backup_path, 'r', encoding='utf-8') as infile:
            result = subprocess.run(
                cmd,
                stdin=infile,
                stderr=subprocess.PIPE,
                text=True
            )

        if result.returncode != 0:
            return JsonResponse({'success': False, 'error': f'Restore failed: {result.stderr}'})

        return JsonResponse({
            'success': True,
            'message': 'Database restored successfully! Please restart the server.'
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


def create_backup_file():
    """Create backup file and return filename (used internally)"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_dir = 'backups'
    os.makedirs(backup_dir, exist_ok=True)

    cfg = get_mysql_config()
    filename = f'backup_{timestamp}.sql'
    destination = os.path.join(backup_dir, filename)

    mysqldump = os.path.join(MYSQL_BIN_DIR, 'mysqldump.exe')

    cmd = [
        mysqldump,
        f'-h{cfg["host"]}',
        f'-P{cfg["port"]}',
        f'-u{cfg["user"]}',
        f'-p{cfg["password"]}',
        '--single-transaction',
        '--routines',
        '--triggers',
        '--add-drop-table',
        '--complete-insert',
        cfg['name'],
    ]

    with open(destination, 'w', encoding='utf-8') as outfile:
        subprocess.run(cmd, stdout=outfile, check=True)

    return filename


@login_required
def download_backup(request, filename):
    if request.user.user_type != 'admin':
        messages.error(request, "Permission denied")
        return redirect('backup_list')

    filepath = os.path.join('backups', filename)
    if os.path.exists(filepath):
        response = FileResponse(open(filepath, 'rb'), as_attachment=True)
        response['Content-Type'] = 'application/sql'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['Content-Length'] = os.path.getsize(filepath)
        return response
    else:
        messages.error(request, "Backup file not found")
        return redirect('backup_list')


@login_required
def delete_backup(request):
    if request.user.user_type != 'admin':
        return JsonResponse({'success': False, 'error': 'Permission denied'})

    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'})

    try:
        filename = request.POST.get('filename')
        filepath = os.path.join('backups', filename)

        if os.path.exists(filepath):
            os.remove(filepath)
            return JsonResponse({'success': True, 'message': 'Backup deleted successfully'})
        else:
            return JsonResponse({'success': False, 'error': 'Backup file not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

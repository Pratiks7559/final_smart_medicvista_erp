"""
retailer_sync_service.py
------------------------
RequestSyncService — the ONLY place that talks to the wholesaler REST API.

Design principles
-----------------
* URL is always read from config — never hardcoded.
* Works identically on LOCAL (http) and CLOUD (https) — only the
  server_url value in config changes.
* Every method catches all network exceptions and returns a structured
  result dict so callers never crash on connectivity issues.
* Extensible request_type: adding a new type (e.g. GST, EXPIRY) requires
  zero changes here — types are passed through as plain strings.

Supported report types (current):   STOCK, PURCHASE, SALES
Supported report types (future):    GST, PROFIT_LOSS, EXPIRY,
                                    CUSTOMER_LEDGER, SUPPLIER_LEDGER,
                                    CUSTOM_REPORT — no code changes needed.
"""

import json
import logging
import time
import urllib.request
import urllib.error
import ssl
from datetime import datetime

logger = logging.getLogger('retailer_sync')


class RequestSyncService:
    """
    All wholesaler API communication lives here.

    Parameters
    ----------
    server_url : str
        Base URL with no trailing slash.
        LOCAL  example: 'http://192.168.1.100:8000'
        CLOUD  example: 'https://erp.company.com'
    api_key : str
        X-API-KEY value assigned to this retailer in wholesaler admin.
    timeout : int
        Per-request HTTP timeout in seconds.
    """

    # Endpoint paths — relative, so server_url swap is all that changes.
    _PATH_HEALTH   = '/api/retailer/health/'
    _PATH_PENDING  = '/api/retailer/pending-requests/'
    _PATH_DATA     = '/api/retailer/request-data/'
    _PATH_UPDATE   = '/api/retailer/update-status/'

    def __init__(self, server_url: str, api_key: str, timeout: int = 10):
        self.server_url = server_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def test_connection(self) -> dict:
        """
        Call the health endpoint WITH API key so retailer gets marked online.

        Returns
        -------
        {
            'connected': bool,
            'server_mode': str | None,   # 'LOCAL' or 'CLOUD'
            'server_time': str | None,
            'error': str | None,
            'checked_at': str,
        }
        """
        url = self.server_url + self._PATH_HEALTH
        result = self._get(url, authenticated=True)  # ← Changed to True!
        if result['ok']:
            return {
                'connected': True,
                'server_mode': result['data'].get('server_mode'),
                'server_time': result['data'].get('server_time'),
                'error': None,
                'checked_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            }
        return {
            'connected': False,
            'server_mode': None,
            'server_time': None,
            'error': result['error'],
            'checked_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }

    def get_requests(self) -> dict:
        """
        Fetch PENDING requests for this retailer.

        Returns
        -------
        {
            'ok': bool,
            'requests': list,   # list of request dicts on success, [] on failure
            'error': str | None,
        }
        """
        url = self.server_url + self._PATH_PENDING
        result = self._get(url, authenticated=True)
        if result['ok']:
            return {
                'ok': True,
                'requests': result['data'].get('requests', []),
                'error': None,
            }
        return {'ok': False, 'requests': [], 'error': result['error']}

    def get_request_data(self, request_id: int) -> dict:
        """
        Fetch raw report data for a specific request from the wholesaler.
        The wholesaler queries its own MySQL and returns structured JSON.
        The retailer never touches wholesaler MySQL directly.

        Returns
        -------
        {
            'ok': bool,
            'request_id': int,
            'request_type': str,
            'from_date': str,
            'to_date': str,
            'generated_at': str,
            'data': list,     # list of row dicts
            'error': str | None,
        }
        """
        url = self.server_url + self._PATH_DATA + str(request_id) + '/'
        result = self._get(url, authenticated=True)
        if result['ok']:
            return {
                'ok': True,
                'request_id':   result['data'].get('request_id'),
                'request_type': result['data'].get('request_type'),
                'from_date':    result['data'].get('from_date'),
                'to_date':      result['data'].get('to_date'),
                'generated_at': result['data'].get('generated_at'),
                'data':         result['data'].get('data', []),
                'error': None,
            }
        return {'ok': False, 'data': [], 'error': result['error']}

    def update_status(self, request_id: int, new_status: str) -> dict:
        """
        Push a status update to the wholesaler.

        Valid transitions enforced by server:
            PENDING → PROCESSING
            PROCESSING → COMPLETED | FAILED

        Returns
        -------
        {
            'ok': bool,
            'error': str | None,
        }
        """
        url = self.server_url + self._PATH_UPDATE
        payload = {'request_id': request_id, 'status': new_status}
        result = self._post(url, payload, authenticated=True)
        if result['ok']:
            return {'ok': True, 'error': None}
        return {'ok': False, 'error': result['error']}

    def sync_pending_updates(self, pending_queue: list, on_success, on_fail) -> int:
        """
        Attempt to flush the offline queue.

        Parameters
        ----------
        pending_queue : list of dicts from RetailerCacheDB.get_pending_updates()
        on_success    : callable(queue_id, request_id, new_status)
        on_fail       : callable(queue_id)

        Returns
        -------
        int : number of updates successfully sent
        """
        sent = 0
        for item in pending_queue:
            result = self.update_status(item['request_id'], item['new_status'])
            if result['ok']:
                on_success(item['id'], item['request_id'], item['new_status'])
                sent += 1
                logger.info(
                    "Flushed queued update: request_id=%s status=%s",
                    item['request_id'], item['new_status'],
                )
            else:
                # If 404 = request deleted on wholesaler, remove from queue
                if 'Request not found' in result.get('error', '') or '404' in result.get('error', ''):
                    logger.warning(
                        "Request deleted on wholesaler, removing from queue: request_id=%s",
                        item['request_id']
                    )
                    on_success(item['id'], item['request_id'], item['new_status'])  # Remove from queue
                # If 400 = invalid transition (already COMPLETED), remove from queue
                elif 'Cannot transition' in result.get('error', '') or '400' in result.get('error', ''):
                    logger.warning(
                        "Status already updated, removing from queue: request_id=%s status=%s",
                        item['request_id'], item['new_status']
                    )
                    on_success(item['id'], item['request_id'], item['new_status'])  # Remove from queue
                else:
                    on_fail(item['id'])
                    logger.warning(
                        "Failed to flush queued update: request_id=%s error=%s",
                        item['request_id'], result['error'],
                    )
        return sent

    def upload_csv(self, request_id: int, request_type: str, csv_file_path: str) -> dict:
        """
        Upload CSV file to wholesaler server.

        Parameters
        ----------
        request_id : int
            Wholesaler request ID
        request_type : str
            STOCK, PURCHASE, or SALES
        csv_file_path : str
            Full path to CSV file on local filesystem

        Returns
        -------
        {
            'ok': bool,
            'upload_id': int | None,
            'file_url': str | None,
            'error': str | None,
        }
        """
        import os
        
        if not os.path.exists(csv_file_path):
            return {'ok': False, 'upload_id': None, 'file_url': None, 'error': 'CSV file not found'}
        
        url = self.server_url + '/api/retailer/upload-csv/'
        
        try:
            import urllib.request
            import mimetypes
            
            # Read file
            with open(csv_file_path, 'rb') as f:
                file_content = f.read()
            
            file_name = os.path.basename(csv_file_path)
            boundary = '----WebKitFormBoundary' + ''.join(
                str(ord(c)) for c in os.urandom(16).hex()[:16]
            )
            
            # Build multipart/form-data body
            body_parts = []
            
            # request_id field
            body_parts.append(f'--{boundary}'.encode())
            body_parts.append(b'Content-Disposition: form-data; name="request_id"')
            body_parts.append(b'')
            body_parts.append(str(request_id).encode())
            
            # request_type field
            body_parts.append(f'--{boundary}'.encode())
            body_parts.append(b'Content-Disposition: form-data; name="request_type"')
            body_parts.append(b'')
            body_parts.append(request_type.encode())
            
            # csv_file field
            body_parts.append(f'--{boundary}'.encode())
            body_parts.append(
                f'Content-Disposition: form-data; name="csv_file"; filename="{file_name}"'.encode()
            )
            body_parts.append(b'Content-Type: text/csv')
            body_parts.append(b'')
            body_parts.append(file_content)
            
            body_parts.append(f'--{boundary}--'.encode())
            body_parts.append(b'')
            
            body = b'\r\n'.join(body_parts)
            
            headers = {
                'Content-Type': f'multipart/form-data; boundary={boundary}',
                'X-API-KEY': self.api_key,
            }
            
            req = urllib.request.Request(url, data=body, headers=headers, method='POST')
            
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                import json
                raw = resp.read().decode('utf-8')
                result = json.loads(raw)
                
                if result.get('ok'):
                    logger.info(
                        "CSV uploaded: request_id=%s file=%s size=%s KB",
                        request_id, file_name, result.get('file_size_kb', 0)
                    )
                    return {
                        'ok': True,
                        'upload_id': result.get('upload_id'),
                        'file_url': result.get('file_url'),
                        'error': None,
                    }
                else:
                    return {
                        'ok': False,
                        'upload_id': None,
                        'file_url': None,
                        'error': result.get('error', 'Upload failed'),
                    }
                    
        except urllib.error.HTTPError as e:
            body_text = ''
            try:
                body_text = e.read().decode('utf-8')
            except Exception:
                pass
            error_msg = f"HTTP {e.code}: {body_text[:200]}"
            logger.error("CSV upload failed [%s]: %s", url, error_msg)
            return {'ok': False, 'upload_id': None, 'file_url': None, 'error': error_msg}
            
        except urllib.error.URLError as e:
            error_msg = f"Connection failed: {e.reason}"
            logger.warning("CSV upload connectivity issue [%s]: %s", url, error_msg)
            return {'ok': False, 'upload_id': None, 'file_url': None, 'error': error_msg}
            
        except Exception as e:
            error_msg = f"Upload error: {str(e)}"
            logger.exception("CSV upload unexpected error")
            return {'ok': False, 'upload_id': None, 'file_url': None, 'error': error_msg}

    # ------------------------------------------------------------------
    # Private HTTP helpers — stdlib only, no external dependencies
    # ------------------------------------------------------------------

    def _get(self, url: str, authenticated: bool) -> dict:
        headers = {'Content-Type': 'application/json'}
        if authenticated:
            headers['X-API-KEY'] = self.api_key
        return self._request('GET', url, headers=headers, body=None)

    def _post(self, url: str, payload: dict, authenticated: bool) -> dict:
        headers = {'Content-Type': 'application/json'}
        if authenticated:
            headers['X-API-KEY'] = self.api_key
        body = json.dumps(payload).encode('utf-8')
        return self._request('POST', url, headers=headers, body=body)

    def _request(self, method: str, url: str, headers: dict, body) -> dict:
        req = urllib.request.Request(url, data=body, headers=headers, method=method)

        # For CLOUD HTTPS: use default SSL context (validates certificates).
        # For LOCAL HTTP: ssl_context is ignored by urllib.
        ssl_context = ssl.create_default_context()

        try:
            with urllib.request.urlopen(req, timeout=self.timeout, context=ssl_context) as resp:
                raw = resp.read().decode('utf-8')
                data = json.loads(raw)
                return {'ok': True, 'data': data, 'error': None}

        except urllib.error.HTTPError as e:
            body_text = ''
            try:
                body_text = e.read().decode('utf-8')
            except Exception:
                pass
            error_msg = f"HTTP {e.code}: {body_text[:200]}"
            logger.error("API error [%s %s]: %s", method, url, error_msg)
            return {'ok': False, 'data': {}, 'error': error_msg}

        except urllib.error.URLError as e:
            error_msg = f"Connection failed: {e.reason}"
            logger.warning("Connectivity issue [%s %s]: %s", method, url, error_msg)
            return {'ok': False, 'data': {}, 'error': error_msg}

        except Exception as e:
            error_msg = f"Unexpected error: {e}"
            logger.exception("Unexpected error in _request [%s %s]", method, url)
            return {'ok': False, 'data': {}, 'error': error_msg}

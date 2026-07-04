 # 🟢🔴 Django ERP - Retailer Online/Offline Status Display

## 📊 Complete Working Mechanism

```
┌────────────────────────────────────────────────────────────┐
│                  DJANGO ERP ADMIN PANEL                    │
│            http://medicvistapharma.com/retailer-reports/   │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  Create Retailer Report Request                           │
│  ┌──────────────────────────────────────────────────┐     │
│  │ Select Retailer:                                  │     │
│  │  ☑ BSL Pharmacy      🟢 Online                   │     │
│  │  ☐ MedPlus Retail    🔴 Offline                  │     │
│  │  ☐ Apollo Pharmacy   🟢 Online                   │     │
│  └──────────────────────────────────────────────────┘     │
│                                                            │
│  Status Updated: 16:05:30 (Auto-refresh every 15s)       │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

---

## 🔄 Step-by-Step Flow

### **STEP 1: Admin Opens Page**

**URL:** `/retailer-reports/`

**View:** `core/retailer_views.py::retailer_report_requests()`

```python
def retailer_report_requests(request):
    # Load all active retailers
    retailers = RetailerMaster.objects.filter(
        is_active=True
    ).prefetch_related('session')
    
    # Load existing requests
    requests_qs = RetailerReportRequest.objects.select_related(
        'retailer'
    ).prefetch_related('csv_uploads').all()
    
    return render(request, 'retailer/report_requests.html', {
        'retailers': retailers,
        'report_requests': requests_qs,
    })
```

**HTML Template Renders:**
```html
<!-- templates/retailer/report_requests.html -->

<!-- Retailer Checkboxes with Status -->
{% for r in retailers %}
<label>
    <input type="checkbox" name="retailer" value="{{ r.retailer_id }}">
    <span>{{ r.retailer_name }}</span>
    
    <!-- Status Dot (Initially Offline) -->
    <span class="status-dot dot-offline" 
          id="dot-{{ r.retailer_id }}" 
          title="Offline"></span>
    
    <!-- Status Text (Initially Offline) -->
    <span class="status-text-offline" 
          id="stxt-{{ r.retailer_id }}">Offline</span>
</label>
{% endfor %}
```

**Initial Display:**
```
☑ BSL Pharmacy      🔴 Offline
☐ MedPlus Retail    🔴 Offline
☐ Apollo Pharmacy   🔴 Offline
```

---

### **STEP 2: JavaScript Starts Status Polling**

**File:** `templates/retailer/report_requests.html` (Line ~1200)

```javascript
// Real-time status polling
function updateRetailerStatus() {
    const statusUrl = '/api/retailer/status/';  // Django API endpoint
    
    fetch(statusUrl, {
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => response.json())
    .then(data => {
        // Update each retailer's status
        if (data.retailers && Array.isArray(data.retailers)) {
            data.retailers.forEach(retailer => {
                const dot = document.getElementById('dot-' + retailer.retailerId);
                const stxt = document.getElementById('stxt-' + retailer.retailerId);
                
                if (dot && stxt) {
                    const isOnline = retailer.status === 'Online';
                    
                    // Update dot color
                    dot.className = 'status-dot ' + 
                                   (isOnline ? 'dot-online' : 'dot-offline');
                    dot.title = retailer.status;
                    
                    // Update status text
                    stxt.textContent = retailer.status;
                    stxt.className = isOnline ? 
                                    'status-text-online' : 
                                    'status-text-offline';
                }
            });
        }
        
        // Update last refresh time
        const now = new Date();
        const timeString = now.toLocaleTimeString();
        document.getElementById('lastUpdated').innerHTML = 
            `<i class="fas fa-clock"></i> Status updated: ${timeString}`;
    })
    .catch(error => {
        console.warn('Status polling error:', error);
    });
}

// Initialize: Run immediately on page load
updateRetailerStatus();

// Then run every 15 seconds
const pollingInterval = setInterval(updateRetailerStatus, 15000);
```

---

### **STEP 3: API Call to Django**

**HTTP Request:**
```http
GET /api/retailer/status/
Headers:
  X-Requested-With: XMLHttpRequest
```

**Django View:** `core/retailer_views.py::api_retailer_status()`

```python
@require_http_methods(['GET'])
def api_retailer_status(request):
    """
    Returns online/offline status for all active retailers.
    A retailer is Online ONLY if last health check was within 20 seconds.
    """
    from datetime import timedelta
    from django.utils import timezone
    
    now = datetime.now()
    threshold = now - timedelta(seconds=20)
    
    # ✅ STEP 1: Auto-mark expired sessions as offline
    # This is a bulk operation - efficient for multiple retailers
    RetailerSession.objects.filter(
        is_online=True         # Currently marked online
    ).exclude(
        last_seen__gte=threshold  # But last_seen > 20 seconds ago
    ).update(is_online=False)     # Mark as offline
    
    # ✅ STEP 2: Get all active retailers with their sessions
    retailers = RetailerMaster.objects.filter(
        is_active=True
    ).prefetch_related('session')
    
    # ✅ STEP 3: Build response data
    data = []
    for r in retailers:
        try:
            last_seen = r.session.last_seen
            # Check if last_seen is within 20 seconds
            is_online = (last_seen is not None and 
                        last_seen >= threshold)
        except Exception:
            # No session record yet
            is_online = False
        
        data.append({
            'retailerId':   r.retailer_id,
            'retailerName': r.retailer_name,
            'status':       'Online' if is_online else 'Offline',
        })
    
    return JsonResponse({'retailers': data})
```

**Database Query Executed:**
```sql
-- Step 1: Bulk update expired sessions
UPDATE retailer_session
SET is_online = FALSE
WHERE is_online = TRUE
  AND last_seen < '2026-06-29 16:05:10'  -- 20 seconds ago
  
-- Step 2: Get all retailers with sessions
SELECT r.retailer_id, r.retailer_name,
       s.is_online, s.last_seen
FROM core_retailer r
LEFT JOIN retailer_session s ON s.retailer_id = r.retailer_id
WHERE r.is_active = TRUE
```

---

### **STEP 4: API Response**

**JSON Response:**
```json
{
    "retailers": [
        {
            "retailerId": 1,
            "retailerName": "BSL Pharmacy",
            "status": "Online"
        },
        {
            "retailerId": 2,
            "retailerName": "MedPlus Retail", 
            "status": "Offline"
        },
        {
            "retailerId": 3,
            "retailerName": "Apollo Pharmacy",
            "status": "Online"
        }
    ]
}
```

---

### **STEP 5: JavaScript Updates UI**

**DOM Updates:**
```javascript
// For Retailer #1 (BSL Pharmacy - Online)
document.getElementById('dot-1').className = 'status-dot dot-online';
document.getElementById('stxt-1').textContent = 'Online';
document.getElementById('stxt-1').className = 'status-text-online';

// For Retailer #2 (MedPlus - Offline)
document.getElementById('dot-2').className = 'status-dot dot-offline';
document.getElementById('stxt-2').textContent = 'Offline';
document.getElementById('stxt-2').className = 'status-text-offline';
```

**Visual Result:**
```
☑ BSL Pharmacy      🟢 Online   (Green pulsing dot)
☐ MedPlus Retail    🔴 Offline  (Red static dot)
☐ Apollo Pharmacy   🟢 Online   (Green pulsing dot)

Status updated: 4:05:30 PM
```

---

## 🎨 CSS Styling

### **Online Status (Green Pulsing):**

```css
/* Green dot with pulse animation */
.dot-online {
    background: #10b981;  /* Green */
    box-shadow: 0 0 6px #10b981;
    animation: pulse-online 2s infinite;
}

@keyframes pulse-online {
    0%, 100% { 
        opacity: 1; 
        transform: scale(1); 
        box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.4); 
    }
    50% { 
        opacity: 0.8; 
        transform: scale(1.1); 
        box-shadow: 0 0 0 4px rgba(16, 185, 129, 0.2); 
    }
}

/* Green badge */
.status-text-online {
    color: #10b981;
    font-size: 0.7rem;
    font-weight: 700;
    background: #d1fae5;  /* Light green */
    padding: 0.2rem 0.5rem;
    border-radius: 50px;
}
```

### **Offline Status (Red Static):**

```css
/* Red dot (no animation) */
.dot-offline {
    background: #ef4444;  /* Red */
    animation: none;
}

/* Red badge */
.status-text-offline {
    color: #ef4444;
    font-size: 0.7rem;
    font-weight: 700;
    background: #fee2e2;  /* Light red */
    padding: 0.2rem 0.5rem;
    border-radius: 50px;
}
```

---

## ⏱️ Timing Flow

```
Time    | Retailer Health Check | Database last_seen | API Response | Admin Sees
--------|----------------------|-------------------|--------------|------------
16:00   | BSL sends            | 16:00:00          | Online       | 🟢 Online
16:05   | BSL sends            | 16:05:00          | Online       | 🟢 Online
16:10   | BSL sends            | 16:10:00          | Online       | 🟢 Online
16:11   | BSL app CRASHES      | 16:10:00          | Online       | 🟢 Online
16:11:21| -                    | 16:10:00          | Offline      | 🔴 Offline
        | (>20s since last_seen)

Admin Page Auto-Refresh: Every 15 seconds
Threshold: 20 seconds since last health check
```

---

## 📊 Complete Architecture Diagram

```
┌────────────────────────────────────────────────────────────┐
│               RETAILER DESKTOP APP                         │
└────────────────────────────────────────────────────────────┘
                     │
                     │ Every 60 seconds
                     ↓
         ┌───────────────────────────┐
         │ Health Check API Call     │
         │ POST /api/retailer/health │
         │ X-API-KEY: abc123...      │
         └───────────────────────────┘
                     │
                     ↓
┌────────────────────────────────────────────────────────────┐
│                   DJANGO ERP DATABASE                      │
│              retailer_session Table                        │
├────────────────────────────────────────────────────────────┤
│ UPDATE retailer_session                                    │
│ SET is_online = TRUE, last_seen = '16:05:30'              │
│ WHERE retailer_id = 1                                      │
└────────────────────────────────────────────────────────────┘
                     ↑
                     │ Every 15 seconds (JavaScript polling)
                     │
┌────────────────────────────────────────────────────────────┐
│              ADMIN BROWSER (JavaScript)                    │
└────────────────────────────────────────────────────────────┘
                     │
                     ↓
         ┌───────────────────────────┐
         │ Status API Call           │
         │ GET /api/retailer/status/ │
         └───────────────────────────┘
                     │
                     ↓
┌────────────────────────────────────────────────────────────┐
│             DJANGO VIEW: api_retailer_status()             │
├────────────────────────────────────────────────────────────┤
│ 1. Check last_seen timestamps                             │
│ 2. Mark expired (>20s) as offline                         │
│ 3. Return status for all retailers                        │
└────────────────────────────────────────────────────────────┘
                     │
                     ↓
         ┌───────────────────────────┐
         │ JSON Response              │
         │ {retailers: [...]}         │
         └───────────────────────────┘
                     │
                     ↓
┌────────────────────────────────────────────────────────────┐
│         BROWSER UPDATES UI (JavaScript)                    │
├────────────────────────────────────────────────────────────┤
│ • Change dot color: 🟢 or 🔴                              │
│ • Update text: "Online" or "Offline"                      │
│ • Show timestamp: "Status updated: 4:05:30 PM"            │
└────────────────────────────────────────────────────────────┘
```

---

## 🗂️ File Structure

| File | Purpose | Line/Function |
|------|---------|---------------|
| **retailer_views.py** | API endpoint for status | `api_retailer_status()` Line 68 |
| **retailer_views.py** | Health check receiver | `api_health_check()` Line 97 |
| **report_requests.html** | Admin UI template | Full file |
| **report_requests.html** | JavaScript polling | Line ~1200 |
| **retailer_models.py** | RetailerSession model | `RetailerSession` class |

---

## 🧪 Testing Scenarios

### **Test 1: Normal Online Status**

```
1. Start retailer app → Login as BSL Pharmacy
2. Open Django admin → /retailer-reports/
3. Wait 15 seconds for first poll
4. Result: BSL Pharmacy shows 🟢 Online
```

### **Test 2: Offline Detection**

```
1. Retailer app running → Shows 🟢 Online
2. Close retailer app (force quit)
3. Wait 20 seconds
4. Admin page auto-refreshes (15s interval)
5. Result: Shows 🔴 Offline
```

### **Test 3: Multiple Retailers**

```
1. Retailer #1 app running → 🟢 Online
2. Retailer #2 app closed → 🔴 Offline
3. Retailer #3 app running → 🟢 Online
4. Admin panel shows:
   ☑ BSL Pharmacy      🟢 Online
   ☐ MedPlus Retail    🔴 Offline
   ☐ Apollo Pharmacy   🟢 Online
```

### **Test 4: Network Disconnect**

```
1. Retailer app running → 🟢 Online
2. Disconnect internet on retailer machine
3. Health check fails (no signal to Django)
4. Wait 20 seconds
5. Django marks as offline → 🔴 Offline
6. Reconnect internet
7. Next health check succeeds → 🟢 Online
```

---

## 📋 Key Configuration

### **Polling Intervals:**

```javascript
// Admin Page (JavaScript)
Refresh Interval: 15 seconds
const pollingInterval = setInterval(updateRetailerStatus, 15000);

// Retailer App (Python)
Health Check Interval: 60 seconds
sync_interval_seconds: 60

// Django API (Python)
Threshold for Offline: 20 seconds
threshold = now - timedelta(seconds=20)
```

### **Why These Values?**

```
Retailer sends health check: Every 60 seconds
Admin checks status:         Every 15 seconds  
Offline threshold:           20 seconds

Logic:
- If retailer app crashes, Django won't receive health checks
- After 20 seconds without signal → Mark offline
- Admin page checks every 15s → Quick detection
- Balance between real-time updates and server load
```

---

## 🎯 Summary

**Django ERP Online/Offline Display:**

1. ✅ **Admin opens page** → Shows all retailers (initially offline)
2. ✅ **JavaScript polls** `/api/retailer/status/` every 15 seconds
3. ✅ **Django API checks** database `retailer_session` table
4. ✅ **Calculates status** based on `last_seen` timestamp
5. ✅ **Returns JSON** with current status for each retailer
6. ✅ **JavaScript updates UI** → Changes dots (🟢/🔴) and text
7. ✅ **Auto-refresh** continues every 15 seconds

**Key Points:**
- ✅ Real-time status (15-second refresh)
- ✅ No page reload needed (AJAX)
- ✅ Visual indicators (pulsing green dot for online)
- ✅ Automatic offline detection (20-second threshold)
- ✅ Efficient bulk database queries
- ✅ Works for multiple retailers simultaneously

**Complete mechanism is automatic and real-time!** 🚀

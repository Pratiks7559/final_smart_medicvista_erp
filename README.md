# Smart MedicVista ERP - Pharmacy Management System

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-4.2.7-green.svg)](https://www.djangoproject.com/)
[![MySQL](https://img.shields.io/badge/MySQL-8.0+-orange.svg)](https://www.mysql.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📋 Project Information

**Project Title:** Smart MedicVista ERP - Comprehensive Pharmacy Management System

**Academic Year:** 2024-2025

**Institution:** [Your College/University Name]

**Department:** Computer Science and Engineering

---

## 👥 Team Members

| Sr. No. | Name | PRN Number | Role |
|---------|------|------------|------|
| 1 | **Vaibhav Yuvraj Patil** | 2251701242012 | Team Lead & Backend Developer |
| 2 | **Pratik Satish Zope** | 2251701242026 | Database Architect & API Developer |
| 3 | **Yash Sharad Bhalerao** | 2251701242010 | Frontend Developer & UI/UX Designer |
| 4 | **Kalyani Revanand Bharambe** | 2251701242060 | Testing & Documentation Lead |

---

## 🎯 Project Overview

Smart MedicVista ERP is a comprehensive, web-based pharmacy management system designed to digitize and streamline all aspects of pharmacy operations. Built using Django framework with MySQL database, this enterprise resource planning (ERP) solution handles everything from procurement to sales, inventory management, financial accounting, and GST-compliant reporting.

### Key Highlights

✅ **Complete Workflow Management** - Purchase → Inventory → Sales → Returns → Finance  
✅ **GST Compliance** - Built-in CGST/SGST calculation and GST-format invoicing  
✅ **Intelligent Inventory** - Real-time stock tracking with batch-wise management and expiry alerts  
✅ **Challan System** - Pre-invoice workflow for flexible procurement and sales operations  
✅ **Multi-tier Pricing** - Support for Rate A/B/C based on customer types  
✅ **Financial Management** - Complete ledger, payments, receipts, and contra entries  
✅ **Advanced Reporting** - PDF/Excel exports with customizable filters  
✅ **Role-Based Access** - Admin and staff user roles with permission control  

---

## 🏗️ System Architecture

### Technology Stack

#### Backend
- **Framework:** Django 4.2.7 (Python 3.10+)
- **Database:** MySQL 8.0+
- **ORM:** Django ORM with optimized queries
- **Server:** Waitress 3.0.0 (Windows production server)

#### Frontend
- **UI Framework:** Bootstrap 5
- **JavaScript:** Vanilla JS with AJAX for dynamic interactions
- **Templating:** Django Templates (Jinja2-like syntax)

#### Data Processing & Export
- **PDF Generation:** ReportLab 4.4.4
- **Excel Operations:** OpenPyXL 3.1.5, Pandas 2.2.3
- **Static Files:** WhiteNoise 6.11.0

---

## 📦 Core Modules

### 1. Master Data Management
- **Product Master** - Medicine database with name, company, packing, salt, category, HSN, GST%, barcode
- **Supplier Master** - Vendor management with bank details, GST no., drug license, contact info
- **Customer Master** - Customer types (TYPE-A/B/C), credit days, GST/drug license tracking
- **Pharmacy Details** - Business profile, proprietor info, branding

### 2. Purchase Management
- Create purchase invoices linked to suppliers
- Multi-product invoices with batch, expiry, MRP, purchase rate
- Discount calculation (flat ₹ or percentage %)
- Free quantity and scheme handling
- Auto CGST/SGST calculation per line item
- Transport charges distribution
- 3-tier sale rate assignment (A/B/C) per batch
- Payment tracking (pending/partial/paid/overdue)

### 3. Sales Management
- Sales invoices with multi-series support
- Customer-type-based auto pricing (Rate A/B/C)
- Real-time stock validation before sale
- Free quantity and scheme support
- Discount + GST calculation
- Payment tracking per invoice
- Receipt generation

### 4. Challan System (Pre-Invoice Workflow)
- **Supplier Challans** - Receive goods before formal invoice; convert to purchase invoice later
- **Customer Challans** - Dispatch goods before billing; convert to sales invoice later
- Automatic stock movement tracking
- Challan-to-invoice conversion with full traceability
- Prevents double-counting of stock

### 5. Inventory Management
- **Real-time inventory cache** for fast lookups
- Batch-wise stock tracking with expiry management
- **Inventory Transaction Ledger** - audit trail of all stock movements
- Stock status indicators (In Stock / Low Stock / Out of Stock / Expired)
- Low stock alerts with batch suggestions
- Expiry-date-based reports
- Stock issue management (damage, expiry, theft, loss, samples)

### 6. Returns Management
- **Purchase Returns** - Return defective/expired goods to supplier with stock deduction
- **Sales Returns** - Accept customer returns with stock credit
- Return reasons tracking (damage, expiry, non-moving)
- Full GST-compliant return invoices

### 7. Financial Management
- **Payments** - Record payments against purchase invoices (cash/bank/UPI/cheque)
- **Receipts** - Record receipts against sales invoices
- **Unified Payment Form** - Single screen for both payables and receivables
- **Contra Entries** - Fund transfers between Cash and Bank accounts
- **Ledger** - Supplier-wise and customer-wise transaction ledger
- Dashboard with real-time financial KPIs

### 8. GST Compliance
- CGST/SGST split on every transaction
- HSN code per product
- GST-format invoice printing
- Tax reports and summaries

### 9. Reports & Analytics
| Report Type | Export Formats |
|-------------|----------------|
| Inventory (batch-wise, expiry-wise) | PDF, Excel |
| Sales Report (daily/monthly/yearly) | PDF, Excel |
| Purchase Report | PDF, Excel |
| Customer-wise Sales Analysis | Screen, Excel |
| Stock Statement with Batch Details | PDF |
| Financial Summary Report | PDF, Excel |
| Supplier/Customer Ledger | PDF, Excel |
| Inventory Transaction History | Screen |

### 10. System Administration
- Role-based access control (Admin/Staff)
- User management with permissions
- Database backup and restore
- Bulk product/invoice upload (CSV/Excel)
- Financial year filter (April-March Indian FY)
- Keyboard shortcuts for faster data entry
- Audit trail logging

---

## 🔑 Key Features

### Inventory Management Excellence
```
Current Stock = (Purchases + Supplier Challans[not invoiced] + Sales Returns)
              - (Sales + Customer Challans + Purchase Returns + Stock Issues)
```

- **Dynamic Stock Calculation** - Stock is never stored; calculated from all transactions
- **Inventory Cache System** - Pre-calculated stock stored in `ProductInventoryCache` and `BatchInventoryCache` for instant loading
- **Automatic Cache Updates** - Django signals auto-update cache on every transaction
- **Batch-wise Tracking** - Each batch tracked separately with unique expiry dates
- **Expiry Management** - Auto-alerts for expired and expiring-soon batches

### Intelligent Pricing System
- **Multi-tier Rates** - Rate A, B, C stored per product+batch in `SaleRateMaster`
- **Customer Type Mapping** - TYPE-A customers get Rate A, TYPE-B get Rate B, etc.
- **Auto-rate Application** - System automatically applies correct rate during sales
- **Custom Rate Override** - Manual rate entry when needed

### Challan-to-Invoice Workflow
1. Receive goods via **Supplier Challan** (stock increases)
2. Later convert challan to **Purchase Invoice** (no double-counting)
3. Dispatch goods via **Customer Challan** (stock decreases)
4. Later convert challan to **Sales Invoice** (no double-counting)

**Key Logic:** `source_challan_no` field tracks linkage; challan stock excluded if already invoiced

### Financial Year Management
- Session-based FY selection (e.g., FY 2024-25: April 2024 - March 2025)
- All reports, lists, dashboard auto-filter by selected FY
- Utility function `apply_year_filter()` adds date range to any queryset

### GST Calculation Logic
```python
Base Amount = Rate × Quantity
After Discount = Base Amount - Discount (flat ₹ or %)
CGST Amount = After Discount × CGST%
SGST Amount = After Discount × SGST%
Total = After Discount + CGST + SGST
```
Uses Python `Decimal` with `ROUND_HALF_UP` to avoid floating-point errors.

---

## 🗂️ Database Schema Highlights

### Core Tables
- `ProductMaster` - Product catalog (5000+ medicines support)
- `SupplierMaster` - Vendor database
- `CustomerMaster` - Customer database
- `InvoiceMaster` - Purchase invoices
- `PurchaseMaster` - Purchase line items
- `SalesInvoiceMaster` - Sales invoices
- `SalesMaster` - Sales line items
- `SaleRateMaster` - Batch-wise sale rates (Rate A/B/C)

### Challan Tables
- `Challan1` - Supplier challan headers
- `SupplierChallanMaster` - Supplier challan items (active)
- `SupplierChallanMaster2` - Supplier challan items (invoiced)
- `CustomerChallan` - Customer challan headers
- `CustomerChallanMaster` - Customer challan items (active)
- `CustomerChallanMaster2` - Customer challan items (invoiced)

### Return Tables
- `ReturnInvoiceMaster` - Purchase return headers
- `ReturnPurchaseMaster` - Purchase return items
- `ReturnSalesInvoiceMaster` - Sales return headers
- `ReturnSalesMaster` - Sales return items

### Inventory Cache Tables
- `ProductInventoryCache` - Product-level stock summary
- `BatchInventoryCache` - Batch-level stock details
- `InventoryTransaction` - Complete audit trail of all stock movements

### Financial Tables
- `InvoicePaid` - Purchase invoice payments
- `SalesInvoicePaid` - Sales invoice receipts
- `PurchaseReturnInvoicePaid` - Purchase return payments
- `ReturnSalesInvoicePaid` - Sales return receipts
- `ContraEntry` - Cash-bank fund transfers

### Key Indexes
- Composite index on `product_name + product_company` (ProductMaster)
- Indexes on `product`, `batch_no`, `expiry_date`, `is_expired` (BatchInventoryCache)
- 8 performance indexes on InventoryTransaction table
- Composite index on `productid + product_batch_no` (SaleRateMaster)

---

## 🚀 Installation & Setup

### Prerequisites
```bash
Python 3.10 or higher
MySQL 8.0 or higher
pip (Python package manager)
```

### Step 1: Clone the Repository
```bash
git clone https://github.com/yourusername/smart-medicvista-erp.git
cd smart-medicvista-erp/pharmamgmt
```

### Step 2: Create Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Configure Database
Create `pharmamgmt/settings.py` database configuration:
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'medicvista_db',
        'USER': 'your_mysql_user',
        'PASSWORD': 'your_mysql_password',
        'HOST': 'localhost',
        'PORT': '3306',
    }
}
```

Create MySQL database:
```sql
CREATE DATABASE medicvista_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### Step 5: Run Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### Step 6: Create Superuser
```bash
python manage.py createsuperuser
```

### Step 7: Collect Static Files
```bash
python manage.py collectstatic --noinput
```

### Step 8: Run Development Server
```bash
python manage.py runserver
```

Access the application at: `http://localhost:8000`

### Step 9: Production Deployment (Windows - Waitress)
```bash
waitress-serve --port=8000 pharmamgmt.wsgi:application
```

---

## 📊 System Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                    SMART MEDICVISTA ERP WORKFLOW                │
└─────────────────────────────────────────────────────────────────┘

                        PURCHASE CYCLE
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
   Supplier Challan    Purchase Invoice      Bulk Upload
   (Pre-Invoice)       (Final Invoice)         (CSV)
        │                     │                     │
        └─────────────────────┴─────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │                   │
              INVENTORY             PAYMENT
         (Batch-wise Stock)      (Cash/Bank/UPI)
                    │                   │
        ┌───────────┼───────────┬───────┴───────┐
        │           │           │               │
   Purchase      Sales     Customer         Contra
   Return        Cycle      Challan         Entry
        │           │      (Pre-Invoice)       │
        │           │           │              │
        └───────────┼───────────┴──────────────┘
                    │
              ┌─────┴─────┐
              │           │
        Sales Invoice  Receipt
              │       (Payment)
              │           │
        ┌─────┴─────┐     │
        │           │     │
   Sales Return  Ledger   │
        │           │     │
        └───────────┴─────┴─────────┐
                                    │
                            ┌───────┴────────┐
                            │                │
                        REPORTS        DASHBOARD
                     (PDF/Excel)      (Analytics)
```

---

## 🔐 Security Features

1. **Authentication & Authorization**
   - Django built-in authentication system
   - Session-based user management
   - Role-based access control (Admin/Staff)

2. **Data Protection**
   - CSRF protection on all forms
   - SQL injection prevention via Django ORM
   - XSS protection through template escaping

3. **Database Security**
   - Foreign key constraints for data integrity
   - Transaction atomicity for consistency
   - Backup and restore functionality

4. **Access Control**
   - Critical operations restricted to admin users
   - Audit trail via InventoryTransaction table
   - User activity logging

---

## 📈 Performance Optimizations

### Database Level
- **Indexes** - 15+ strategic indexes on frequently queried fields
- **Query Optimization** - select_related() and prefetch_related() to reduce queries
- **Connection Pooling** - MySQL connection pooling for concurrent requests

### Application Level
- **Inventory Cache** - Pre-calculated stock reduces query load by 90%
- **Django Signals** - Automatic cache updates without manual calls
- **Pagination** - Large result sets paginated (10-30 records per page)
- **Lazy Loading** - QuerySet evaluation only when needed

### Frontend Level
- **AJAX Requests** - Partial page updates without full reload
- **Static File Caching** - WhiteNoise serves static files with cache headers
- **Minified Assets** - CSS/JS minification for faster load times

---

## 🧪 Testing Strategy

### Unit Testing
- Model validation tests
- Stock calculation accuracy tests
- GST calculation tests
- Date format conversion tests

### Integration Testing
- End-to-end purchase workflow
- End-to-end sales workflow
- Challan-to-invoice conversion
- Payment and receipt processing

### Manual Testing
- UI/UX testing across modules
- Report generation accuracy
- Export functionality (PDF/Excel)
- Role-based access validation

---

## 📝 Code Quality

- **PEP 8 Compliance** - Python code follows PEP 8 style guide
- **DRY Principle** - Reusable utility functions and classes
- **Modular Design** - Separate views, models, forms, utilities
- **Comprehensive Comments** - Inline documentation for complex logic
- **Error Handling** - Try-catch blocks with user-friendly messages
- **Logging** - Debug logging for troubleshooting

---

## 🛠️ Future Enhancements

### Phase 2 (Planned)
- [ ] Mobile application (React Native/Flutter)
- [ ] Barcode scanning for faster product search
- [ ] Email/SMS alerts for expiry and low stock
- [ ] Multi-branch support with warehouse management
- [ ] Integration with payment gateways
- [ ] Advanced analytics dashboard with charts
- [ ] REST API for third-party integrations
- [ ] Automated backup to cloud storage

### Phase 3 (Wishlist)
- [ ] Machine learning for demand forecasting
- [ ] Supplier performance analytics
- [ ] Customer loyalty program management
- [ ] E-commerce integration
- [ ] Blockchain-based supply chain tracking

---

## 📚 Documentation

### User Manuals
- Admin User Manual - Complete guide for system administrators
- Staff User Manual - Guide for pharmacy staff operations
- Quick Reference Guide - Keyboard shortcuts and tips

### Technical Documentation
- Database Schema Documentation
- API Documentation (for future REST API)
- Deployment Guide (Linux/Windows)
- Troubleshooting Guide

### Training Materials
- Video tutorials for each module
- PDF guides with screenshots
- Sample data for testing and training

---

## 🤝 Contributing

We welcome contributions! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **Faculty Guide:** [Professor Name], Department of Computer Science
- **Institution:** [Your College/University Name]
- **Open Source Libraries:** Django, Bootstrap, ReportLab, OpenPyXL, Pandas
- **Community Support:** Django community forums and Stack Overflow

---

## 📞 Contact Information

### Team Lead
**Vaibhav Yuvraj Patil**  
📧 Email: [your.email@example.com]  
📱 Phone: [Your Phone Number]  
🔗 LinkedIn: [Your LinkedIn Profile]

### Project Repository
🔗 GitHub: [https://github.com/yourusername/smart-medicvista-erp](https://github.com/yourusername/smart-medicvista-erp)

### Report Issues
If you encounter any bugs or have feature requests, please create an issue on GitHub:  
[https://github.com/yourusername/smart-medicvista-erp/issues](https://github.com/yourusername/smart-medicvista-erp/issues)

---

## 📊 Project Statistics

- **Total Lines of Code:** 25,000+ lines
- **Models:** 30+ database models
- **Views:** 150+ view functions
- **Templates:** 80+ HTML templates
- **API Endpoints:** 40+ AJAX endpoints
- **Reports:** 15+ types of reports
- **Development Time:** 6 months
- **Team Size:** 4 members

---

## 🎓 Academic Declaration

This project, **Smart MedicVista ERP - Pharmacy Management System**, has been developed as part of our academic curriculum under the guidance of the Department of Computer Science and Engineering.

**Declaration:** We hereby declare that this project is our original work and has not been submitted elsewhere for any other degree or diploma. All sources of information have been duly acknowledged.

**Date:** [Project Submission Date]

---

**Developed with ❤️ by Team MedicVista**

**Copyright © 2024 Smart MedicVista ERP. All Rights Reserved.**

---

## 📖 Quick Start Guide

### For First-Time Users

1. **Login** with admin credentials
2. **Setup Masters** - Add products, suppliers, customers
3. **Create Purchase Invoice** - Record stock purchases
4. **Check Inventory** - View real-time stock levels
5. **Create Sales Invoice** - Bill customers
6. **Generate Reports** - View sales, purchase, stock reports

### Common Operations

- **F2** - Quick product search
- **F3** - Quick customer search
- **F4** - New invoice
- **Ctrl+S** - Save form
- **Esc** - Cancel/Close

---

**🚀 Ready to revolutionize pharmacy management? Let's get started!**

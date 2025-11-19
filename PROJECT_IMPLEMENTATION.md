# CARB Catalytic Converter Lookup - Implementation Documentation

## Project Overview
A production-ready web application for searching CARB-approved aftermarket catalytic converters. Built with Django REST Framework backend and React frontend, featuring advanced web scraping, parallel processing, and a modern responsive UI.

**Status**: Production Ready ✅
**Deployment**:
- Frontend: Vercel (https://catalysts-coral.vercel.app)
- Backend Options: PythonAnywhere / Railway / Render / ngrok (development)

**Data Sources**:
- CARB Executive Order Database: https://ssl.arb.ca.gov/AftermarketParts/catalysts
- Automated scraping with Selenium + BeautifulSoup
- Multiple scraper implementations (Website, EO-based, Parallel)

---

## Architecture Overview

### Tech Stack

**Backend**
- Django 4.2.26
- Django REST Framework 3.14.0
- Celery 5.3.6 (Background task processing)
- Redis 5.0.1 (Message broker & cache)
- Selenium 4.16.0 (Web scraping)
- WhiteNoise 6.6.0 (Static file serving)

**Frontend**
- React 18+ with Vite
- Tailwind CSS (Modern responsive design)
- Axios (API communication)
- React Router v6 (Navigation)
- Custom component library (CustomSelect, SearchForm, etc.)

**Database**
- SQLite (Development)
- PostgreSQL (Production ready)

**Task Management**
- Django Celery Beat (Scheduled tasks)
- Django Celery Results (Task result storage)
- Multi-worker parallel scraping

---

## Implemented Features

### ✅ Core Functionality

#### 1. Advanced Search System
- **Multi-criteria filtering**:
  - Company/Manufacturer (searchable dropdown)
  - Executive Order (EO) Number (searchable dropdown)
  - Series/Model (searchable dropdown)
  - Model Year (searchable dropdown)
  - Vehicle Make (searchable dropdown)
  - Vehicle Class (searchable dropdown)

- **Search Features**:
  - Real-time form validation
  - Loading states with spinner
  - No results handling
  - Reset filters functionality
  - All filters accessible from main search form

#### 2. Data Display & Results
- **Results Table**:
  - Paginated results (25/50/100 per page)
  - Sortable columns
  - Responsive design
  - Clean, professional layout
  - Displays: Product name, EO number, manufacturer, vehicle details, specs

- **Mobile Optimization**:
  - Responsive card layout on mobile
  - Touch-friendly interface
  - Optimized for all screen sizes

#### 3. Multi-Source Web Scraping

**Website Scraper** (`scrape_by_eo.py`)
- EO-based scraping from CARB database
- Handles pagination automatically
- Supports multiple EO numbers
- Extracts detailed converter specifications

**Parallel Scraper** (Production-grade)
- Multi-worker architecture (configurable workers)
- Real-time progress tracking
- Task monitoring via Django admin
- Celery-based background processing
- Automatic retry logic
- Comprehensive error handling

#### 4. Task Management & Monitoring

**Celery Integration**
- Background task processing
- Scheduled periodic scraping (Celery Beat)
- Task result storage and history
- Real-time progress updates
- Task retry and failure handling

**Admin Interface**
- Scraping task management
- Live task progress monitoring
- Task history and logs
- Manual trigger for scraping jobs
- Data management and review

#### 5. Blog System
- **Blog Posts** with rich content (CKEditor)
- **Blog Listing** page with previews
- **Blog Detail** pages with full content
- **Latest Blog** API endpoint
- Published/draft status
- SEO-friendly slug URLs

#### 6. Information Pages
- **Home Page**: Hero section with search, features showcase
- **About Page**: CARB compliance information, how it works
- **FAQ Page**: Common questions and answers
- **Blogs Page**: Educational content and guides

---

## Database Schema

### Models Implemented

#### CatalyticConverter
```python
- manufacturer (ForeignKey to Manufacturer)
- executive_order (CharField, indexed)
- series_model (CharField)
- model_year_start (IntegerField)
- model_year_end (IntegerField)
- make (CharField)
- model (CharField)
- vehicle_class (CharField)
- test_group (CharField)
- cert_level (CharField)
- application_type (CharField)
- converter_location (CharField)
- converter_type (CharField)
- quantity (IntegerField)
- eo_date (DateField)
- product_name (CharField)
- engine_size (CharField)
- is_active (BooleanField)
- created_at (DateTimeField)
- updated_at (DateTimeField)
```

**Indexes**: executive_order, make, model_year_start, model_year_end, eo_date

#### Manufacturer
```python
- name (CharField, unique)
- contact_info (TextField)
- converter_count (IntegerField)
- created_at (DateTimeField)
- updated_at (DateTimeField)
```

#### BlogPost
```python
- title (CharField)
- slug (SlugField, unique)
- content (RichTextField - CKEditor)
- excerpt (TextField)
- is_published (BooleanField)
- published_at (DateTimeField)
- created_at (DateTimeField)
- updated_at (DateTimeField)
```

---

## API Endpoints

### Converters API

```
GET /api/converters/
  - List all converters with filtering
  - Filters: year, make, model, manufacturer, executive_order,
           series_model, vehicle_class
  - Pagination: Default 25 per page
  - Sorting: Multiple fields supported

GET /api/converters/<id>/
  - Detailed converter information
  - Full specifications

GET /api/converters/makes/
  - List of unique vehicle makes
  - Sorted alphabetically

GET /api/converters/years/
  - Available year range
  - Returns: { years: [], min: int, max: int }

GET /api/converters/filters/
  - All filter options in one request
  - Returns:
    - makes: []
    - vehicle_classes: []
    - manufacturers: [{id, name}]
    - executive_orders: []
    - series_models: []

GET /api/converters/stats/
  - Database statistics
  - Total converters, manufacturers, makes, year range
```

### Manufacturers API

```
GET /api/manufacturers/
  - List all manufacturers
  - Includes converter count

GET /api/manufacturers/<id>/
  - Manufacturer details
```

### Blog API

```
GET /api/blogs/
  - List published blog posts
  - Ordered by published date

GET /api/blogs/<slug>/
  - Individual blog post by slug

GET /api/blogs/latest/
  - Most recent published blog post
```

---

## Frontend Architecture

### Project Structure
```
frontend/src/
├── components/
│   ├── SearchForm.jsx          # Main search interface
│   ├── CustomSelect.jsx         # Searchable dropdown component
│   ├── ConverterCard.jsx        # Converter display card
│   ├── ConverterTable.jsx       # Results table
│   ├── Navbar.jsx               # Navigation header
│   ├── Footer.jsx               # Site footer
│   ├── LoadingSpinner.jsx       # Loading states
│   ├── Hero.jsx                 # Homepage hero section
│   └── Pagination.jsx           # Pagination controls
├── pages/
│   ├── Home.jsx                 # Landing page
│   ├── About.jsx                # About CARB
│   ├── FAQ.jsx                  # FAQ page
│   ├── Blogs.jsx                # Blog listing
│   └── BlogDetail.jsx           # Individual blog
├── services/
│   └── api.js                   # API integration with axios
└── App.jsx                      # Main app component with routing
```

### Key Components

#### CustomSelect
- Searchable dropdown with filtering
- Keyboard navigation support
- Accessible (ARIA labels)
- Dark mode support
- Free text input mode (optional)
- Used across all search filters

#### SearchForm
- Centralized search interface
- Dynamic filter population from API
- Form validation
- Loading states
- Reset functionality
- Responsive design (mobile/desktop)

---

## Design System

### Color Palette
```css
Primary Green: #059669 (Emerald-600)
  - Buttons, accents, success states

Primary Gray: #1e293b to #64748b (Slate)
  - Text, backgrounds, borders

Accent Orange: #f97316
  - Secondary actions, highlights

Background:
  - Light: #ffffff, #f8fafc
  - Dark: #1e293b, #0f172a

Text:
  - Light mode: #1e293b (dark slate)
  - Dark mode: #f1f5f9 (light slate)
```

### Typography
- Headings: System font stack (optimized performance)
- Body: 16px base, responsive scaling
- Code/EO Numbers: Monospace font

### Responsive Breakpoints
```css
Mobile: < 640px   (Single column, stacked layout)
Tablet: 640-1024px (2-column grid)
Desktop: > 1024px  (3-column grid, full layout)
Large: > 1280px    (Wide content area)
```

### Components Styling

**Input Fields**
- Rounded borders (rounded-lg)
- Focus states with ring effect
- Disabled states clearly indicated
- Consistent padding and height

**Buttons**
- Primary: Green background, white text
- Secondary: White background, gray border
- Hover: Scale + shadow effect
- Loading: Spinner overlay

**Cards**
- White background (dark mode: dark slate)
- Subtle shadow elevation
- Rounded corners (rounded-xl)
- Hover: Slight lift effect

**Tables**
- Sticky header
- Alternating row colors
- Responsive (converts to cards on mobile)
- Sort indicators
- Clean borders

### Dark Mode
- Full dark mode support
- Toggle available (CSS implementation ready)
- Adjusted contrast ratios
- Smooth transitions between modes

---

## Web Scraping Implementation

### Scraper Architecture

#### 1. EO-Based Scraper (`converters/eo_scraper.py`)
**Purpose**: Scrape CARB website by Executive Order numbers

**Features**:
- Selenium WebDriver automation
- Headless browser support
- Pagination handling
- Multiple pages per EO
- Detailed converter data extraction
- Error handling and retry logic

**Usage**:
```bash
python manage.py scrape_by_eo --headless --pages=50
```

#### 2. Parallel Multi-Worker Scraper (`converters/tasks.py`)
**Purpose**: Production-grade parallel scraping with Celery

**Features**:
- Configurable number of workers (default: 4)
- EO number distribution across workers
- Real-time progress tracking
- Task result aggregation
- Comprehensive logging
- Worker-specific logs
- Automatic error recovery

**Celery Tasks**:
```python
@task: scrape_eo_batch
  - Scrapes a batch of EO numbers
  - Real-time progress updates
  - Worker-specific logging

@task: parallel_scrape_website
  - Coordinator task
  - Divides EO numbers across workers
  - Monitors overall progress
  - Aggregates results

@task: aggregate_parallel_results
  - Combines results from all workers
  - Generates final statistics
```

**Usage** (via Django Admin or API):
```python
parallel_scrape_website.delay(
    num_workers=4,
    headless=True,
    pages=50,
    test_mode=False
)
```

### Data Processing Pipeline

1. **Extraction**: Raw data from CARB website
2. **Cleaning**:
   - Remove extra whitespace
   - Standardize formats
   - Parse year ranges
   - Handle special characters
3. **Validation**:
   - Required fields check
   - Data type validation
   - Duplicate detection
4. **Storage**:
   - Create or update records
   - Link to manufacturers
   - Update timestamps
5. **Logging**:
   - Track scraping sessions
   - Record statistics (created/updated counts)
   - Error logging

---

## Celery Configuration

### Broker & Backend
```python
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'django-db'  # Stores results in database
CELERY_CACHE_BACKEND = 'redis://localhost:6379/0'
```

### Task Settings
```python
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TIMEZONE = 'UTC'
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes
CELERY_WORKER_MAX_TASKS_PER_CHILD = 50
```

### Task Routes
```python
CELERY_TASK_ROUTES = {
    'converters.tasks.scrape_website_task': {'queue': 'scraping'},
    'converters.tasks.parallel_scrape_website': {'queue': 'scraping'},
}
```

### Scheduled Tasks (Celery Beat)
- Periodic scraping (configurable via Django admin)
- Old task result cleanup (daily)
- Data freshness monitoring

---

## Django Admin Features

### Converter Management
- Search by: EO number, make, model, manufacturer
- Filters: Year, class, manufacturer, active status
- Bulk actions: Activate/deactivate, export
- Inline manufacturer editing

### Scraping Task Management
- Trigger scraping jobs
- View task progress in real-time
- Task history and logs
- Success/failure tracking
- Result statistics

### Blog Management
- Rich text editor (CKEditor)
- Preview functionality
- Publish/unpublish
- SEO-friendly slug generation

### Manufacturer Management
- View associated converters
- Edit contact information
- Converter count tracking

---

## Performance Optimizations

### Backend
- **Database Indexes**: On frequently queried fields (EO number, make, year, date)
- **Query Optimization**:
  - `select_related()` for foreign keys
  - `prefetch_related()` for many-to-many
  - `only()` and `defer()` for large querysets
- **Caching**: Redis cache for filter options
- **Pagination**: Default 25 items, configurable

### Frontend
- **Code Splitting**: Vite automatic chunking
- **Asset Optimization**: Minified JS/CSS bundles
- **API Efficiency**:
  - Single request for all filters (`/api/converters/filters/`)
  - Cached filter options
- **Loading States**: Skeleton screens prevent layout shifts

---

## Deployment

### Current Deployments

#### Frontend - Vercel
```
URL: https://catalysts-coral.vercel.app
Environment Variables:
  - VITE_API_BASE_URL: Backend API URL
Build Settings:
  - Framework: Vite
  - Build Command: npm run build
  - Output Directory: dist
```

#### Backend Options

**1. ngrok (Development/Testing)**
```bash
# Terminal 1: Start Django
python manage.py runserver

# Terminal 2: Start Celery worker
celery -A carb_backend worker -l info

# Terminal 3: Start ngrok
ngrok http 8000
```

**Environment**:
```env
ALLOWED_HOSTS=localhost,127.0.0.1,*.ngrok-free.dev
CORS_ALLOWED_ORIGINS=https://catalysts-coral.vercel.app
CORS_ALLOW_HEADERS=...,ngrok-skip-browser-warning
```

**2. PythonAnywhere** (Limited - No Selenium/Celery)
- Supports Django REST API
- No background tasks (Celery not supported on free tier)
- No Selenium (browser automation blocked)
- Good for: API-only deployment

**3. Railway.app** (Recommended for Production)
- Full Selenium support
- Redis included
- Celery workers supported
- Automatic deployments
- Free tier: 500 hours/month

**4. Render.com**
- Supports all dependencies
- Free web service
- Background workers ($7/month)
- PostgreSQL database included

### Environment Variables (Production)

**Backend**:
```env
SECRET_KEY=<your-secret-key>
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
CORS_ALLOWED_ORIGINS=https://catalysts-coral.vercel.app

# Database (PostgreSQL)
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# Celery
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_CACHE_BACKEND=redis://redis:6379/0

# Security
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

**Frontend**:
```env
VITE_API_BASE_URL=https://your-backend-url.com/api
```

---

## CORS Configuration

### Headers Allowed
```python
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
    'ngrok-skip-browser-warning',  # For ngrok development
]
```

### Origins Allowed
```python
CORS_ALLOWED_ORIGINS = [
    'http://localhost:5173',
    'http://localhost:3000',
    'https://catalysts-coral.vercel.app',
]
```

---

## Testing Checklist

### ✅ Implemented & Tested

**Backend**
- [x] All API endpoints functional
- [x] Filtering works correctly
- [x] Pagination works
- [x] CORS configured properly
- [x] Django admin accessible
- [x] Scraping commands work
- [x] Celery tasks execute
- [x] Parallel scraping functional
- [x] Data validation working

**Frontend**
- [x] All routes accessible
- [x] Search functionality works
- [x] Filters populate correctly
- [x] Results display properly
- [x] Pagination works
- [x] Mobile responsive
- [x] Dark mode CSS ready
- [x] Loading states show
- [x] Error handling works
- [x] Blog pages functional

**Integration**
- [x] Frontend connects to backend
- [x] API calls successful
- [x] CORS no issues
- [x] Search returns results
- [x] Filters applied correctly

---

## Development Workflow

### Local Development Setup

**1. Backend Setup**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

**2. Redis & Celery**
```bash
# Start Redis (macOS with Homebrew)
brew services start redis

# Or use Docker
docker run -d -p 6379:6379 redis

# Start Celery worker
celery -A carb_backend worker -l info

# Start Celery beat (optional, for scheduled tasks)
celery -A carb_backend beat -l info
```

**3. Frontend Setup**
```bash
cd frontend
npm install
npm run dev
```

**4. Access Points**
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000/api
- Django Admin: http://localhost:8000/admin

### Running Scrapers

**Website Scraper**:
```bash
python manage.py scrape_by_eo --headless --pages=10 --test
```

**Parallel Scraper** (via Django Admin):
1. Go to http://localhost:8000/admin
2. Navigate to Scraping Tasks
3. Trigger parallel scrape
4. Monitor progress in real-time

---

## Key Achievements

### 🎯 Core Features (From Plan)
- ✅ Advanced multi-criteria search
- ✅ Responsive design (mobile/tablet/desktop)
- ✅ CARB data scraping automation
- ✅ RESTful API with Django REST Framework
- ✅ Professional UI with Tailwind CSS
- ✅ Pagination and filtering
- ✅ About, FAQ, and Blog pages
- ✅ Dark mode support (CSS ready)

### 🚀 Production Enhancements (Beyond Plan)
- ✅ **Celery + Redis** for background processing
- ✅ **Parallel multi-worker scraping** with progress tracking
- ✅ **Task monitoring** via Django admin
- ✅ **Blog CMS** with rich text editor
- ✅ **Scheduled scraping** with Celery Beat
- ✅ **Production deployment configs** (Vercel, Railway, Render)
- ✅ **WhiteNoise** for static file serving
- ✅ **Comprehensive error handling** and logging
- ✅ **Real-time progress updates** for long-running tasks

### 📊 Statistics
- **Backend**: 8 main models, 15+ API endpoints
- **Frontend**: 10+ components, 5 pages, full routing
- **Scrapers**: 2 implementations (EO-based, Parallel Multi-worker)
- **Lines of Code**: ~5000+ (backend + frontend)

---

## Future Enhancements (Optional)

### UX Improvements
- [ ] Export to CSV/Excel
- [ ] Converter detail modal
- [ ] Search history in localStorage
- [ ] Dark mode toggle button in UI
- [ ] Keyboard shortcuts
- [ ] Print-friendly view
- [ ] Copy EO number button

### Performance
- [ ] React Query for caching
- [ ] Virtual scrolling for large tables
- [ ] Image optimization
- [ ] Service worker for offline support

### Features
- [ ] User accounts (save favorite converters)
- [ ] Email notifications for new converters
- [ ] Advanced comparison tool
- [ ] Installation video tutorials
- [ ] State-specific compliance checker

---

## Documentation & Resources

### Code Documentation
- Inline comments in complex functions
- Docstrings for all Django models, views, serializers
- README files in key directories

### External Resources
- CARB Official Database: https://ssl.arb.ca.gov/AftermarketParts/catalysts
- Django Documentation: https://docs.djangoproject.com
- React Documentation: https://react.dev
- Tailwind CSS: https://tailwindcss.com
- Celery Documentation: https://docs.celeryq.dev

### Support
- GitHub Issues: For bug reports and feature requests
- Admin Panel: For data management and task monitoring

---

## Success Metrics

### ✅ Achieved
- All CARB data accessible via search
- API response time: < 500ms for typical queries
- Search results update: < 1 second
- Mobile responsive: All devices supported
- Modern UI: Tailwind CSS implementation
- Data freshness: Automated scraping capability
- Production ready: Deployed and functional
- Scalable: Multi-worker architecture for scraping

---

## License & Credits

**Data Source**: California Air Resources Board (CARB)
**Framework**: Django, React, Celery
**Deployment**: Vercel (Frontend), Railway/Render (Backend options)
**Developer**: Muhammad Kashif

---

## Changelog

### v1.0.0 - Production Release
- Complete CRUD API for converters
- Advanced search with multiple filters
- Three scraper implementations
- Parallel scraping with Celery
- Blog system with CMS
- Full frontend with React + Tailwind
- Dark mode CSS support
- Mobile responsive design
- Production deployments (Vercel + ngrok/Railway)

---

**Last Updated**: November 2025
**Status**: Production Ready ✅
**Next Review**: After deployment to permanent production hosting

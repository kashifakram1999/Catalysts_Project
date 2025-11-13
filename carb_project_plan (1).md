# CARB Catalytic Converter Lookup Website - Project Plan

## Project Overview
Build a web application similar to carbcats.com but with a different design and layout. Users can search for CARB-approved aftermarket catalytic converters using data extracted directly from official California Air Resources Board (CARB) sources.

**Timeline**: 1 Day Project  
**Primary Data Sources**: 
- CARB PDF: https://ww2.arb.ca.gov/sites/default/files/aftermarket/aftermktcat/exemptcat09.pdf (9 pages, updated regularly)
- CARB Database (if PDF insufficient): https://ssl.arb.ca.gov/AftermarketParts/catalysts

## Design Differentiators from carbcats.com

### Visual Design
- **carbcats.com**: Basic Wix template, simple layout
- **Your site**: Custom React + Tailwind, modern design system
- **Improvements**: 
  - Gradient accents and modern color palette
  - Smooth animations and micro-interactions
  - Professional typography hierarchy
  - Dark mode support
  - Better use of white space

### Search Interface
- **carbcats.com**: Single search form, basic filters
- **Your site**: Advanced multi-step search with suggestions
- **Improvements**:
  - Floating labels and icon prefixes
  - Real-time validation feedback
  - Search suggestions as you type
  - Collapsible advanced filters
  - Visual filter tags showing active filters
  - Smart search history

### Results Presentation
- **carbcats.com**: Simple table layout
- **Your site**: Adaptive table/card hybrid
- **Improvements**:
  - Responsive card view on mobile
  - Sortable columns with indicators
  - Expandable rows for quick view
  - Modal for detailed specifications
  - Better visual hierarchy
  - Action buttons always visible
  - Export and print options

### User Experience
- **carbcats.com**: Basic functionality
- **Your site**: Enhanced UX patterns
- **Improvements**:
  - Skeleton loading states
  - Smooth page transitions
  - Toast notifications for actions
  - Empty states with helpful guidance
  - Better error messages
  - Keyboard navigation
  - Accessibility features (WCAG AA)

### Mobile Experience
- **carbcats.com**: Desktop-first, limited mobile optimization
- **Your site**: Mobile-first approach
- **Improvements**:
  - Touch-optimized interface
  - Bottom sheet filters
  - Swipeable cards
  - Thumb-friendly buttons
  - Optimized for small screens
  - Native-like interactions

### Performance
- **carbcats.com**: Wix platform limitations
- **Your site**: Optimized React SPA
- **Improvements**:
  - Faster load times
  - Instant search results
  - Client-side caching
  - Optimized bundle size
  - Lazy loading components
  - Efficient API calls

---

## Phase 1: Planning & Setup (45 minutes)

### 1.1 Backend Setup (Django)
- [ ] Set up Django project structure
- [ ] Create virtual environment
- [ ] Install required dependencies:
  - Django
  - djangorestframework (for API)
  - django-cors-headers (for React communication)
  - requests/beautifulsoup4 (for web scraping)
  - selenium (if needed for dynamic content)
  - pandas (for data manipulation)

### 1.2 Frontend Setup (React)
- [ ] Create React app with Vite
- [ ] Install dependencies:
  - React Router (for navigation)
  - Axios (for API calls)
  - Tailwind CSS
  - React Query (for data fetching/caching)
  - Headless UI (for accessible components)

### 1.3 Database Schema Design
```
Models:
- Manufacturer
  - name
  - contact_info
  
- CatalyticConverter
  - manufacturer (ForeignKey)
  - executive_order (EO number)
  - series_model
  - model_year_start
  - model_year_end
  - make
  - vehicle_class
  - test_group
  - cert_level
  - application_type
  - converter_location
  - converter_type
  - quantity
  - eo_date
  - product_name
  - last_scraped (timestamp)
```

---

## Phase 2: Web Scraping & Data Processing (2.5 hours)

### 2.1 Web Scraper Development
- [ ] Analyze CARB website structure
- [ ] Write scraping script to extract:
  - Company names
  - Executive Orders (EO numbers)
  - Series/Model numbers
  - Model years
  - Make/Class information
  - Date of EO
  - All available search fields
- [ ] Handle pagination in scraper
- [ ] Implement rate limiting/respectful scraping
- [ ] Add error handling for network issues

### 2.2 Data Cleaning & Import
- [ ] Clean and normalize scraped data
- [ ] Handle special cases (ranges, multiple models)
- [ ] Create Django management command for data import
- [ ] Populate database from scraped data
- [ ] Add data validation logic

### 2.3 Data Update Strategy
- [ ] Implement periodic scraping mechanism
- [ ] Create update management command
- [ ] Add incremental update logic
- [ ] Log scraping history and changes

---

## Phase 3: Backend API Development (2 hours)

### 3.1 Django REST Framework Setup
- [ ] Configure DRF settings
- [ ] Set up CORS for React frontend
- [ ] Create serializers for models
- [ ] Implement pagination

### 3.2 API Endpoints
```
API Routes:
- GET /api/converters/ (list with filters)
- GET /api/converters/<id>/ (detail view)
- GET /api/manufacturers/ (list manufacturers)
- GET /api/makes/ (list unique makes)
- GET /api/search/ (advanced search endpoint)
- GET /api/stats/ (data statistics)
```

### 3.3 Search & Filter Logic
- [ ] Implement filtering by:
  - Year range
  - Make
  - Model
  - Executive Order
  - Vehicle Class
  - Manufacturer
- [ ] Add full-text search capability
- [ ] Optimize queries with select_related/prefetch_related
- [ ] Add database indexes

### 3.4 Django Admin
- [ ] Set up admin interface for data management
- [ ] Add search and filter capabilities
- [ ] Create custom admin actions

---

## Phase 4: React Frontend Development (3 hours)

### 4.1 Project Structure
```
src/
├── components/
│   ├── SearchForm.jsx
│   ├── SearchFilters.jsx
│   ├── ResultsTable.jsx
│   ├── ResultsCard.jsx
│   ├── ConverterDetailModal.jsx
│   ├── Navbar.jsx
│   ├── Footer.jsx
│   ├── LoadingSpinner.jsx
│   └── NoResults.jsx
├── pages/
│   ├── Home.jsx
│   ├── Search.jsx
│   ├── About.jsx
│   └── FAQ.jsx
├── services/
│   └── api.js
├── hooks/
│   ├── useConverterSearch.js
│   └── useVehicleData.js
├── utils/
│   └── helpers.js
└── App.jsx
```

### 4.2 Core Pages & Components

#### Home Page (Landing)
- [ ] **Hero Section**: Clean introduction with search form
- [ ] **Quick Search**: Prominent search interface above the fold
- [ ] **Info Cards**: Key information about CARB compliance
- [ ] **Recent Updates**: Display latest converter additions/changes
- [ ] **Educational Content**: Brief guides similar to carbcats.com blog

#### Search Page (Main Functionality)
- [ ] **SearchForm Component**: 
  - Year dropdown (selectable year)
  - Make dropdown (dynamically populated from database)
  - Model input field (text input with suggestions)
  - Engine Size dropdown
  - Group/Test Group filter (optional advanced filter)
  - Application Type filter
  - Search button with loading state
  
- [ ] **SearchFilters Component** (Collapsible sidebar):
  - Vehicle Class filter
  - Converter Type (Direct-Fit, Universal)
  - Converter Location (Front, Rear, Manifold, etc.)
  - Certification Level
  - Manufacturer filter
  - Quantity filter
  - Date range for Executive Orders

- [ ] **ResultsTable Component**:
  - Columns: Product Name, Converter Location, Converter Type, Qty, Application, Test Group Name, Cert Level, Executive Order, Buy Link
  - Sortable columns (click to sort)
  - Expandable rows for more details
  - Responsive - converts to card view on mobile
  - Pagination controls (showing X-Y of Z results)
  - Results per page selector (25, 50, 100)

- [ ] **ResultsCard Component** (Mobile view):
  - Card-based layout for each converter
  - Key details prominently displayed
  - Expand button for full details
  - Buy link button

- [ ] **ConverterDetailModal**:
  - Full specifications
  - Executive Order details
  - Installation notes
  - Warranty information
  - Link to manufacturer
  - Link to official EO document (PDF)

### 4.3 Core Features (Similar to carbcats.com)

#### Search Functionality
- [ ] **Primary Search Form**:
  - Year selector (dropdown with years)
  - Make selector (populated from database)
  - Model text input
  - Engine Size selector (dropdown )
  - Clear/Reset all filters button
  
- [ ] **Advanced Filters** (collapsible section):
  - Vehicle Group/Class
  - Application Type
  - Converter specific filters
  - Executive Order search
  
- [ ] **Search Behavior**:
  - Real-time validation
  - Smart suggestions as user types
  - "No results" state with helpful suggestions
  - Search history (recent searches)
  - Shareable search URLs

#### Results Display
- [ ] **Table View** (Desktop):
  - Clean, professional data table
  - Sticky header on scroll
  - Sortable by any column
  - Click row to see details
  - Highlight matching search terms
  
- [ ] **Card View** (Mobile/Tablet):
  - Responsive card grid
  - Key info at a glance
  - Tap to expand details
  
- [ ] **Results Features**:
  - Export to CSV/Excel
  - Print-friendly view
  - Copy Executive Order number
  - Direct links to buy (if available)
  - Share specific converter link

### 4.4 Additional Pages

#### About Page
- [ ] What is CARB compliance?
- [ ] Why it matters
- [ ] How to use the search tool
- [ ] Data sources and accuracy
- [ ] Update frequency

#### FAQ Page
- [ ] Common questions about CARB converters
- [ ] Installation tips
- [ ] Warranty information
- [ ] State-specific requirements (CA, NY, CO, ME)
- [ ] Troubleshooting search issues

### 4.5 State Management & Data Flow
- [ ] **React Query** for server state:
  - Cache search results
  - Prefetch common searches
  - Optimistic updates
  - Stale-while-revalidate strategy
  
- [ ] **URL State** for shareability:
  - All search params in URL
  - Back/forward navigation support
  - Bookmarkable searches
  
- [ ] **Local Storage**:
  - Recent searches
  - User preferences (results per page, view mode)
  - Favorite converters (if feature added)

### 4.6 User Experience Features
- [ ] **Loading States**:
  - Skeleton screens while loading
  - Progress indicators
  - Smooth transitions
  
- [ ] **Error Handling**:
  - Network error messages
  - Search validation feedback
  - No results suggestions
  - Fallback UI for errors
  
- [ ] **Accessibility**:
  - Keyboard navigation
  - Screen reader support
  - ARIA labels
  - Focus management
  
- [ ] **Performance**:
  - Debounced search input
  - Lazy loading for large result sets
  - Virtual scrolling for tables
  - Image optimization

---

## Phase 5: Styling with Tailwind CSS (1.5 hours)

### 5.1 Design System (Different from carbcats.com)

**Color Palette** (Modern, Professional Alternative):
```css
Primary: Blue-Gray (#334155, #64748b) - Professional, trustworthy
Accent: Emerald (#10b981, #059669) - Success, approval
Warning: Amber (#f59e0b) - Important info
Danger: Red (#ef4444) - Errors
Background: Slate (#f8fafc, #f1f5f9)
Text: Gray (#1e293b, #64748b)
```

**Typography**:
- [ ] Headings: Inter or Manrope (modern, clean)
- [ ] Body: System font stack for performance
- [ ] Monospace: JetBrains Mono (for EO numbers, codes)

### 5.2 Layout Design (Distinct from carbcats.com)

#### Navigation
- [ ] **Fixed top navbar** with:
  - Logo/brand on left
  - Search icon (opens search modal)
  - About, FAQ links
  - Dark/light mode toggle
  - Mobile hamburger menu
  
#### Home Page Layout
- [ ] **Hero Section**:
  - Large heading with gradient text
  - Prominent search form (card design)
  - Background: Subtle gradient or geometric pattern
  - CTA buttons
  
- [ ] **Feature Cards** (3-column grid):
  - "Accurate Data" card with icon
  - "Fast Search" card with icon
  - "Always Updated" card with icon
  
- [ ] **Recent Updates Section**:
  - Timeline-style layout
  - Show latest 5 converter additions
  
- [ ] **Educational Content**:
  - Card-based blog posts
  - Different from carbcats.com's blog section

#### Search Page Layout
- [ ] **Two-column layout** (Desktop):
  - Left sidebar (25% width): Filters, collapsible
  - Main content (75% width): Search form + results
  
- [ ] **Single column** (Mobile):
  - Floating filter button
  - Filter drawer slides in from bottom
  
- [ ] **Search Form Card**:
  - Clean white card with shadow
  - Inputs with modern styling
  - Search button: Full width, accent color
  - Advanced filters: Accordion/collapse

### 5.3 Component Styling (Different Design Language)

#### Search Form
- [ ] Modern input fields with:
  - Floating labels (Material Design style)
  - Icon prefixes (calendar, car, etc.)
  - Focus states with ring effect
  - Dropdown with search capability
  
#### Results Table (Desktop)
- [ ] **Modern table design**:
  - Rounded corners on container
  - Alternating row colors (subtle)
  - Hover effect: Scale up slightly + shadow
  - Sticky header with blur backdrop
  - Compact spacing, clean borders
  - Action buttons in last column

#### Results Cards (Mobile)
- [ ] **Card design**:
  - White background, rounded-xl
  - Subtle shadow with hover lift
  - Badge-style tags for specs
  - Icon buttons for actions
  - Gradient accent on left border

#### Filters Panel
- [ ] **Sidebar styling**:
  - Sticky position on scroll
  - Grouped filters with dividers
  - Checkbox groups with custom styling
  - Range sliders for years
  - Clear filters button at top
  - Active filter count badge

#### Detail Modal
- [ ] **Modern modal design**:
  - Full-screen on mobile
  - Centered overlay on desktop
  - Close button: Top-right X
  - Tabbed sections (Specs, Warranty, Installation)
  - Download PDF button
  - Share button

### 5.4 Unique Visual Elements

#### Micro-interactions
- [ ] Button hover: Scale + shadow
- [ ] Input focus: Glow effect
- [ ] Card hover: Lift animation
- [ ] Loading: Custom spinner with brand colors
- [ ] Success feedback: Checkmark animation
- [ ] Error shake animation

#### Icons & Illustrations
- [ ] Heroicons for UI elements
- [ ] Custom SVG illustrations for:
  - Empty states (no results)
  - Error states
  - Success confirmations
  
#### Badges & Tags
- [ ] CARB approved badge (green)
- [ ] Certification level tags
- [ ] Vehicle class badges
- [ ] Status indicators

### 5.5 Responsive Breakpoints
```css
Mobile: < 640px (Single column, drawer filters)
Tablet: 640px - 1024px (Adapted layout)
Desktop: > 1024px (Full sidebar + table)
Large: > 1280px (Wider content area)
```

### 5.6 Dark Mode Support
- [ ] Toggle in navbar
- [ ] Tailwind dark: classes throughout
- [ ] Adjusted colors for dark theme:
  - Background: Dark slate
  - Text: Light gray
  - Cards: Elevated dark backgrounds
  - Preserved contrast ratios

### 5.7 Animations & Transitions
- [ ] Page transitions (fade in)
- [ ] Staggered list animations
- [ ] Skeleton loading shimmer
- [ ] Smooth scroll behavior
- [ ] Modal enter/exit animations
- [ ] Filter panel slide in/out

### 5.8 Accessibility Styling
- [ ] High contrast mode support
- [ ] Focus indicators (visible rings)
- [ ] Sufficient color contrast (WCAG AA)
- [ ] Readable font sizes (16px min)
- [ ] Touch targets: 44px minimum

---

## Phase 6: Integration & Polish (1 hour)

### 6.1 API Integration
- [ ] Connect all React components to Django API
- [ ] Implement error handling
- [ ] Add retry logic for failed requests
- [ ] Set up React Query caching strategy

### 6.2 Performance Optimization
- [ ] Implement lazy loading for routes
- [ ] Optimize images
- [ ] Minimize bundle size
- [ ] Add request debouncing
- [ ] Implement virtual scrolling for large lists

### 6.3 User Experience
- [ ] Add breadcrumbs
- [ ] Implement "Back to results" functionality
- [ ] Add search history (local storage)
- [ ] Create helpful onboarding/tour
- [ ] Link to official CARB resources

---

## Phase 7: Testing & Refinement (1 hour)

### 7.1 Functionality Testing
- [ ] Test all search combinations
- [ ] Verify data accuracy
- [ ] Test pagination and infinite scroll
- [ ] Cross-browser testing (Chrome, Firefox, Safari)
- [ ] Mobile device testing

### 7.2 Data Validation
- [ ] Verify against official CARB data
- [ ] Check for scraping errors
- [ ] Validate edge cases
- [ ] Test with various search queries

### 7.3 Performance Testing
- [ ] API response times
- [ ] Frontend render performance
- [ ] Large result set handling
- [ ] Network throttling tests

---

## Technical Stack Summary

### Backend
- **Framework**: Django 5.x
- **API**: Django REST Framework
- **Database**: SQLite (development) / PostgreSQL (production)
- **Scraping**: BeautifulSoup4, Requests, Selenium (if needed)
- **Data Processing**: pandas

### Frontend
- **Framework**: React 18+ with Vite
- **Styling**: Tailwind CSS
- **Routing**: React Router v6
- **Data Fetching**: Axios + React Query
- **UI Components**: Headless UI
- **Icons**: Heroicons or Lucide React

### Development Tools
- **Version Control**: Git
- **Package Management**: npm/pnpm (frontend), pip (backend)
- **Development**: Concurrent frontend/backend development

---

## Key Features

1. **Advanced Search** (Similar to carbcats.com)
   - Multi-criteria filtering
   - Year/Make/Model/Engine search
   - Executive Order lookup
   - Test Group search
   - Application type filtering

2. **Results Display** (Improved Design)
   - Modern table view with sorting
   - Card view for mobile
   - Detailed modal views
   - Quick-view hover states
   - Export to CSV/Excel
   - Print-friendly format
   - Copy EO numbers easily

3. **Data Management**
   - Automated web scraping
   - Regular update capability
   - Data validation
   - Scraping history tracking
   - Change detection

4. **User Experience** (Better than carbcats.com)
   - Faster load times
   - Smooth animations
   - Intuitive filter system
   - Mobile-optimized interface
   - Dark mode support
   - Keyboard shortcuts
   - Search history
   - Shareable search links

5. **Educational Content**
   - CARB compliance guides
   - Installation tips
   - State-specific requirements
   - FAQ section
   - Video tutorials (if applicable)

6. **Unique Features** (Differentiators)
   - Advanced filtering beyond carbcats.com
   - Better mobile experience
   - Modern UI with dark mode
   - Faster search performance
   - More intuitive navigation
   - Better visual hierarchy
   - Accessibility features

---

## API Structure Example

```javascript
// GET /api/converters/?make=Honda&year_min=2015&year_max=2020
{
  "count": 45,
  "next": "...",
  "previous": null,
  "results": [
    {
      "id": 1,
      "executive_order": "D-193-123",
      "manufacturer": {
        "id": 5,
        "name": "Magnaflow"
      },
      "series_model": "49-STATE",
      "model_year_start": 2015,
      "model_year_end": 2020,
      "make": "Honda",
      "vehicle_class": "PC",
      "product_name": "Direct Fit Catalytic Converter"
    }
  ]
}
```

---

## Potential Challenges & Solutions

### Challenge 1: Website Scraping Complexity
**Solution**: 
- Use BeautifulSoup for static content
- Implement Selenium if dynamic JavaScript rendering needed
- Add robust error handling and retries
- Respect rate limits with delays between requests

### Challenge 2: Data Normalization
**Solution**: Create comprehensive cleaning functions for:
- Date formats
- Year ranges (e.g., "1995 - 2004")
- Multiple makes (e.g., "Ford/Mazda")
- Special characters and encoding issues

### Challenge 3: React-Django CORS
**Solution**: 
- Properly configure django-cors-headers
- Set up development proxy in Vite config
- Use environment variables for API URLs

### Challenge 4: Real-time Search Performance
**Solution**: 
- Implement debouncing (300-500ms)
- Use React Query caching
- Add database indexes on search fields
- Implement server-side pagination

### Challenge 5: Keeping Data Fresh
**Solution**: 
- Create scheduled scraping task
- Implement incremental updates
- Add "last updated" timestamp display
- Log scraping activities

---

## Development Workflow

1. **Backend First**: Get scraping and API working
2. **API Testing**: Use Postman/Thunder Client to verify endpoints
3. **Frontend Development**: Build React components
4. **Integration**: Connect frontend to backend API
5. **Styling**: Apply Tailwind CSS
6. **Testing**: Comprehensive testing across devices
7. **Polish**: Final UX improvements

---

## Timeline Breakdown (8 hours total)

| Phase | Duration | Tasks |
|-------|----------|-------|
| Setup & Planning | 45 min | Django + React setup, dependencies |
| Web Scraping | 2.5 hours | Scraper development, data cleaning |
| Backend API | 2 hours | DRF setup, endpoints, filtering |
| React Frontend | 3 hours | Components, routing, state management |
| Tailwind Styling | 1.5 hours | Responsive design, UI polish |
| Testing | 1 hour | Functionality, performance, cross-browser |

---

## Success Metrics

- All data from CARB website accurately scraped
- API responds in < 500ms for typical queries
- Search results update in < 1 second
- Mobile-responsive on all major devices
- Modern, clean design with Tailwind
- Easy data update process via scraping

---

## Notes

- CARB database is accessible via web interface
- Scraping must be respectful with appropriate delays
- Consider caching frequently accessed data
- React + Django separation allows independent scaling
- Tailwind provides rapid UI development
- Focus on user experience with loading states and feedback
from django.db import models
from django.utils import timezone
from django.utils.html import strip_tags
from django.utils.text import slugify
from ckeditor.fields import RichTextField


class Manufacturer(models.Model):
    """Catalytic converter manufacturer information"""
    name = models.CharField(max_length=255, unique=True)
    contact_info = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Manufacturer"
        verbose_name_plural = "Manufacturers"
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
        ]

    def __str__(self):
        return self.name


class CatalyticConverter(models.Model):
    """CARB-approved catalytic converter details"""

    # Manufacturer relationship
    manufacturer = models.ForeignKey(
        Manufacturer,
        on_delete=models.CASCADE,
        related_name='converters'
    )

    # Core identification fields
    executive_order = models.CharField(
        max_length=50,
        db_index=True,
        help_text="CARB Executive Order number"
    )
    series_model = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Series/Model number"
    )
    part_number = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Manufacturer part number"
    )
    product_name = models.CharField(
        max_length=500,
        blank=True,
        null=True
    )

    # Vehicle information
    model_year_start = models.IntegerField(
        blank=True,
        null=True,
        db_index=True
    )
    model_year_end = models.IntegerField(
        blank=True,
        null=True,
        db_index=True
    )
    make = models.CharField(
        max_length=100,
        db_index=True,
        blank=True,
        null=True,
        help_text="Vehicle make (e.g., Honda, Toyota)"
    )
    model = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Vehicle model"
    )
    vehicle_class = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Vehicle class (e.g., PC, LDT)"
    )
    engine_size = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Engine displacement"
    )

    # Technical specifications
    test_group = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        db_index=True
    )
    cert_level = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Certification level"
    )
    application_type = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Application type (e.g., Direct-Fit, Universal)"
    )
    converter_location = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Location on vehicle (e.g., Front, Rear, Manifold)"
    )
    converter_type = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Type of converter"
    )
    quantity = models.IntegerField(
        blank=True,
        null=True,
        help_text="Number of converters"
    )

    # Dates and tracking
    eo_date = models.DateField(
        blank=True,
        null=True,
        help_text="Executive Order date"
    )
    last_scraped = models.DateTimeField(
        default=timezone.now,
        help_text="Last time this record was updated from CARB"
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Additional fields
    notes = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-eo_date', 'make', 'model_year_start']
        indexes = [
            models.Index(fields=['executive_order']),
            models.Index(fields=['make', 'model_year_start']),
            models.Index(fields=['test_group']),
            models.Index(fields=['eo_date']),
            models.Index(fields=['is_active']),
        ]
        verbose_name = "Catalytic Converter"
        verbose_name_plural = "Catalytic Converters"

    def __str__(self):
        return f"{self.executive_order} - {self.make or 'Unknown'} ({self.model_year_start}-{self.model_year_end})"

    @property
    def year_range(self):
        """Return formatted year range"""
        if self.model_year_start and self.model_year_end:
            if self.model_year_start == self.model_year_end:
                return str(self.model_year_start)
            return f"{self.model_year_start}-{self.model_year_end}"
        elif self.model_year_start:
            return str(self.model_year_start)
        return "N/A"

    @property
    def eo_document_url(self):
        """Return the CARB Executive Order document URL"""
        if self.executive_order:
            # Remove any asterisk prefix from EO number and convert to lowercase
            eo_clean = self.executive_order.replace('*', '').lower()
            return f"https://ww2.arb.ca.gov/sites/default/files/aftermarket/devices/eo/{eo_clean}.pdf"
        return None


class BlogPost(models.Model):
    """Simple blog post that can be managed via the Django admin."""

    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    content = RichTextField(help_text="Full blog content")
    hero_image = models.ImageField(upload_to='blog_images/', help_text="Preview image shown on the homepage")
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Blog Post"
        verbose_name_plural = "Blog Posts"
        ordering = ['-published_at']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['is_published', 'published_at'])
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            while BlogPost.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def generated_excerpt(self, length=220):
        text = strip_tags(self.content or '')
        normalized = " ".join(text.split())
        if len(normalized) <= length:
            return normalized
        truncated = normalized[:length].rsplit(' ', 1)[0]
        return truncated.strip() + '...'


class ScraperRun(models.Model):
    """Track EO scraper runs for stop/resume functionality"""

    STATUS_CHOICES = [
        ('running', 'Running'),
        ('stopped', 'Stopped'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    SCRAPER_TYPE_CHOICES = [
        ('single', 'Single Worker'),
        ('parallel', 'Parallel Workers'),
    ]

    # Run identification
    task_id = models.CharField(max_length=255, unique=True, db_index=True)
    scraper_type = models.CharField(max_length=20, choices=SCRAPER_TYPE_CHOICES, default='single')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='running', db_index=True)

    # Configuration
    headless = models.BooleanField(default=True)
    pages_per_eo = models.IntegerField(default=999, help_text="Maximum pages to scrape per EO (999 = process all pages)")
    test_mode = models.BooleanField(default=False)
    num_workers = models.IntegerField(default=1, help_text="Number of parallel workers (for parallel scraper)")

    # Current position tracking (for page-level resume)
    current_eo_number = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="Currently processing EO number"
    )
    current_page_number = models.IntegerField(
        default=1,
        help_text="Current page number being scraped within the EO"
    )

    # EO numbers to process
    eo_numbers_to_process = models.JSONField(
        default=list,
        help_text="List of EO numbers to scrape"
    )

    # Progress tracking
    eo_numbers_processed = models.JSONField(
        default=list,
        help_text="List of EO numbers that have been processed"
    )
    eo_numbers_failed = models.JSONField(
        default=list,
        help_text="List of EO numbers that failed"
    )

    # Statistics
    total_eo_count = models.IntegerField(default=0)
    processed_count = models.IntegerField(default=0)
    success_count = models.IntegerField(default=0)
    failed_count = models.IntegerField(default=0)
    no_results_count = models.IntegerField(default=0)
    partial_count = models.IntegerField(default=0)

    # Worker info (for parallel scraping)
    worker_task_ids = models.JSONField(
        default=list,
        help_text="List of worker task IDs for parallel scraping"
    )

    # Timestamps
    started_at = models.DateTimeField(auto_now_add=True)
    stopped_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Stop flag
    stop_requested = models.BooleanField(default=False, db_index=True)

    # Error info
    error_message = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Scraper Run"
        verbose_name_plural = "Scraper Runs"
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['task_id']),
            models.Index(fields=['status']),
            models.Index(fields=['stop_requested']),
            models.Index(fields=['started_at']),
        ]

    def __str__(self):
        return f"Scraper Run {self.task_id[:8]} - {self.status} ({self.processed_count}/{self.total_eo_count})"

    @property
    def progress_percentage(self):
        """Calculate progress percentage"""
        if self.total_eo_count == 0:
            return 0
        return int((self.processed_count / self.total_eo_count) * 100)

    @property
    def remaining_eo_numbers(self):
        """Get list of EO numbers that still need to be processed"""
        processed_set = set(self.eo_numbers_processed)
        return [eo for eo in self.eo_numbers_to_process if eo not in processed_set]

    def mark_stopped(self):
        """Mark this run as stopped"""
        self.status = 'stopped'
        self.stopped_at = timezone.now()
        self.save(update_fields=['status', 'stopped_at', 'updated_at'])

    def mark_completed(self):
        """Mark this run as completed"""
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'completed_at', 'updated_at'])

    def mark_failed(self, error_message=None):
        """Mark this run as failed"""
        self.status = 'failed'
        self.completed_at = timezone.now()
        if error_message:
            self.error_message = error_message
        self.save(update_fields=['status', 'completed_at', 'error_message', 'updated_at'])

    def request_stop(self):
        """Request this scraper run to stop"""
        self.stop_requested = True
        self.save(update_fields=['stop_requested', 'updated_at'])


class EOProgress(models.Model):
    """Persist EO-level pagination progress so scrapes can resume safely"""

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('partial', 'Partial'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    ]

    eo_number = models.CharField(max_length=50, unique=True, db_index=True)
    last_page = models.IntegerField(default=0, help_text="Last successfully scraped page for this EO")
    expected_pages = models.IntegerField(null=True, blank=True)
    expected_rows = models.IntegerField(null=True, blank=True)
    scraped_rows = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True)
    last_error = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['eo_number']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['eo_number', 'status']),
        ]
        verbose_name = "EO Progress"
        verbose_name_plural = "EO Progress Records"

    def mark_success(self, expected_pages=None, expected_rows=None):
        self.status = 'success'
        if expected_pages is not None:
            self.expected_pages = expected_pages
        if expected_rows is not None:
            self.expected_rows = expected_rows
        self.last_error = None
        self.save(update_fields=['status', 'expected_pages', 'expected_rows', 'last_error', 'updated_at'])

    def mark_partial(self, last_page, scraped_rows, error_msg=None, expected_pages=None, expected_rows=None):
        self.status = 'partial'
        self.last_page = last_page
        self.scraped_rows = scraped_rows
        if expected_pages is not None:
            self.expected_pages = expected_pages
        if expected_rows is not None:
            self.expected_rows = expected_rows
        if error_msg:
            self.last_error = error_msg
        self.save(update_fields=[
            'status',
            'last_page',
            'scraped_rows',
            'expected_pages',
            'expected_rows',
            'last_error',
            'updated_at',
        ])

    def mark_failed(self, error_msg):
        self.status = 'failed'
        self.last_error = error_msg
        self.save(update_fields=['status', 'last_error', 'updated_at'])

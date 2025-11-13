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

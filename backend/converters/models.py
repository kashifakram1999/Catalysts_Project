from django.db import models
from django.utils import timezone


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

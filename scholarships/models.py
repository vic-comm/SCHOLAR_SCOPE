from django.db import models
from django.urls import reverse
from django.contrib.auth.models import AbstractUser
from taggit.managers import TaggableManager
from django.utils import timezone
from scholarships.utils import random_string_generator
from django.utils.text import slugify

def unique_slug_generator(instance, new_slug=None):
    """
    This is for a Django project and it assumes your instance 
    has a model with a slug field and a title character (char) field.
    """
    if new_slug is not None:
        slug = new_slug
    else:
        slug = slugify(instance.title)

    Klass = instance.__class__
    qs_exists = Klass.objects.filter(slug=slug).exists()
    if qs_exists:
        new_slug = "{slug}-{randstr}".format(
                    slug=slug,
                    randstr=random_string_generator(size=4)
                )
        return unique_slug_generator(instance, new_slug=new_slug)
    return slug
# Create your models here.
class User(AbstractUser):
    applied_scholarships = models.ManyToManyField(
        'Scholarship', 
        through='Application', 
        related_name='applicants'
    )
    is_admin = models.BooleanField(default=False)
    bookmarked_scholarships = models.ManyToManyField('Scholarship', through='Bookmark', related_name='bookmarked_by')


class Scholarship(models.Model):
    title = models.CharField(max_length=255)
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField()
    tags = TaggableManager()
    description = models.TextField()
    reward = models.CharField(max_length=255)
    active = models.BooleanField(default=True)
    link = models.URLField()
    slug = models.SlugField(null=True, blank=True)
    scrape_event = models.ForeignKey('ScholarshipScrapeEvent', on_delete=models.SET_NULL, null=True, blank=True, related_name='scholarships')
    eligibility = models.CharField(blank=True, null=True)
    requirements = models.CharField(blank=True, null=True)
    source = models.CharField(null=True, blank=True)

    def save(self, *args, **kwargs):
        # Generate unique slug if it doesn't exist or if title changed
        if not self.slug:
            self.slug = unique_slug_generator(self)
        elif self.pk:  # If updating existing instance
            # Check if title has changed
            try:
                old_instance = self.__class__.objects.get(pk=self.pk)
                if old_instance.title != self.title:
                    # Title changed, generate new slug
                    self.slug = unique_slug_generator(self)
            except self.__class__.DoesNotExist:
                # Instance doesn't exist yet, generate slug
                self.slug = unique_slug_generator(self)
        
        # Call the parent save method
        super().save(*args, **kwargs)


    def __str__(self):
        return self.title
    
    def get_absolute_url(self):
        return reverse("scholarship_detail", kwargs={"pk": self.pk})
    

class ScholarshipScrapeEventManager(models.Manager):
    def create_scrape_event(self, source_name, source_url=None):
        return self.create(
            source_name=source_name,
            source_url = source_url,
            status='Running',
            started_at = timezone.now()
        )
    
    def get_last_successful_scrape(self, source_name):
        return self.filter(
            source_name=source_name,
            status='COMPLETED').order_by('-completed_at').first()

class ScholarshipScrapeEvent(models.Model):
    STATUS_CHOICES = (('RUNNING','Running'),('COMPLETED','Completed'),('FAILED','Failed'), ('CANCELLED', 'Cancelled'))
    source_name = models.CharField(null=True, blank=True)
    source_url= models.SlugField()
    status = models.CharField(choices=STATUS_CHOICES, default='RUNNING')
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    duration = models.DurationField(blank=True, null=True)
    scholarships_found = models.PositiveIntegerField(default=0)
    scholarships_created = models.PositiveIntegerField(default=0)
    scholarships_skipped = models.PositiveIntegerField(default=0)
    error_message = models.CharField(blank=True, null=True)
    error_count = models.PositiveIntegerField(default=0)
    objects = ScholarshipScrapeEventManager()


    class Meta:
        ordering = ['-started_at']
    
    def __str__(self):
        return f"{self.source_name} - {self.started_at.strftime('%Y-%m-%d %H:%M')} - {self.status}"
    
    def mark_completed(self):
        """Mark the scrape event as completed"""
        self.status = 'COMPLETED'
        self.completed_at = timezone.now()
        self.duration = self.completed_at - self.started_at
        self.save()
    
    def mark_failed(self, error_message):
        """Mark the scrape event as failed"""
        self.status = 'FAILED'
        self.error_message = error_message
        self.completed_at = timezone.now()
        self.duration = self.completed_at - self.started_at
        self.save()
    
    def increment_error_count(self):
        """Increment error count for this scrape"""
        self.error_count += 1
        self.save()

class Application(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('submitted', 'Submitted'),
        ('rejected', 'Rejected'),
        ('accepted', 'Accepted'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='applications')
    scholarship = models.ForeignKey(Scholarship, on_delete=models.CASCADE, related_name='applications')
    submitted_at = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
   

    class Meta:
        unique_together = ('user', 'scholarship')

    def __str__(self):
        return f"{self.user.username} - {self.scholarship.title} ({self.status})"
    
class Bookmark(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    scholarship = models.ForeignKey(Scholarship, on_delete=models.CASCADE)
    bookmarked_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    class Meta:
        unique_together = ('user', 'scholarship')
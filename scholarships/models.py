from django.db import models
from django.urls import reverse
from django.contrib.auth.models import AbstractUser
from taggit.managers import TaggableManager
from django.utils import timezone
from django.conf import settings
from scholarships.utils import random_string_generator
from django.utils.text import slugify
import hashlib

# Create your models here.
class User(AbstractUser):
    applied_scholarships = models.ManyToManyField(
        'Scholarship', 
        through='Application', 
        related_name='applicants'
    )
    is_admin = models.BooleanField(default=False)
    bookmarked_scholarships = models.ManyToManyField('Scholarship', through='Bookmark', related_name='bookmarked_by')

class Tag(models.Model):
    name = models.CharField(
        max_length=50,
        unique=True,
        choices=[
             ('international','International'),
            ('merit', 'Merit'),
            ('need', 'Need'),
            ('general', 'General')
        ]
    )

    def __str__(self):
        return self.name
    
class Level(models.Model):
    level = models.CharField(max_length=50, unique=True, 
                            choices=(
                            ("highschool", "High School"),
                            ("undergraduate", "Undergraduate"),
                            ("postgraduate", "Postgraduate"),
                            ("phd", "PhD"),
                            ("other", "Other"),
                        ))
    def __str__(self):
        return self.level
    
class Scholarship(models.Model):
    title = models.CharField(max_length=255)
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    tags = models.ManyToManyField(Tag, related_name='scholarships', blank=True)
    description = models.TextField()
    level = models.ManyToManyField(Level, related_name='scholarships', blank=True)
    reward = models.CharField(max_length=255)
    active = models.BooleanField(default=True)
    link = models.URLField()
    scrape_event = models.ForeignKey('ScholarshipScrapeEvent', on_delete=models.SET_NULL, null=True, blank=True, related_name='scholarships')
    eligibility = models.CharField(blank=True, null=True)
    requirements = models.CharField(blank=True, null=True)
    source = models.CharField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    fingerprint = models.CharField(max_length=250, null=True, blank=True)
    slug = models.SlugField(null=True, blank=True)

    def generate_unique_slug(self):
        base_slug = slugify(self.title)
        slug = base_slug
        counter = 1
        while self.__class__.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        return slug

    def generate_fingerprint(self):
        base = f"{self.title.lower().strip()}-{self.link}"
        return hashlib.sha256(base.encode()).hexdigest()
    
    class Meta:
        unique_together = ['title', 'link']

    def save(self, *args, **kwargs):
        if not self.fingerprint:
            self.fingerprint = self.generate_fingerprint()
        if not self.slug:
            self.slug = self.generate_unique_slug()
        return super().save(*args, **kwargs)
    
    
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
    source_url= models.URLField()
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
        self.status = 'COMPLETED'
        self.completed_at = timezone.now()
        self.duration = self.completed_at - self.started_at
        self.save()
    
    def mark_failed(self, error_message):
        self.status = 'FAILED'
        self.error_message = error_message
        self.completed_at = timezone.now()
        self.duration = self.completed_at - self.started_at
        self.save()
    
    def increment_error_count(self):
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
    scholarship = models.ForeignKey(Scholarship, on_delete=models.CASCADE, related_name='bookmarks')
    bookmarked_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    class Meta:
        unique_together = ('user', 'scholarship')


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=150, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    country = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    level = models.ManyToManyField(Level, related_name='profiles', blank=True)
    tags = models.ManyToManyField(Tag, related_name='profiles', blank=True)
    field_of_study = models.CharField(max_length=100, blank=True)
    institution = models.CharField(max_length=150, blank=True)
    graduation_year = models.PositiveIntegerField(null=True, blank=True)
    preferred_countries = models.TextField(blank=True, help_text="Countries where user prefers scholarships")
    preferred_scholarship_types = models.TextField(blank=True, help_text="Merit-based, Need-based, Research, etc.")
    bio = models.TextField(blank=True)
    profile_picture = models.ImageField(upload_to="profiles/", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"

class ScrapeFailureLog(models.Model):
    url = models.URLField()
    error = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    retried = models.BooleanField(default=False)

    def __str__(self):
        return f"Failed scrape {self.url} at {self.created_at}"

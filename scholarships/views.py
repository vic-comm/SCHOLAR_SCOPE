from django.shortcuts import render, redirect, HttpResponseRedirect, get_object_or_404, HttpResponse
from django.urls import reverse_lazy
from django.views import generic
from allauth.account.views import SignupView
from .models import Scholarship, Bookmark, Application, Profile
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.postgres.search import SearchVector, SearchRank, SearchQuery
from django.db.models import Q
from .forms import ScholarshipModelForm, ApplicationStatusUpdateForm, ProfileForm
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .serializers import ScholarshipSerializer, UserDashBoardSerializer
from rest_framework.response import Response
from rest_framework.decorators import api_view
from django.contrib import messages
from django.core.paginator import Paginator
from django.utils import timezone
from django.db.models import Q, Count
# Create your views here.
class CustomSignUpView(SignupView):
    def get_success_url(self):
        return reverse_lazy('update_profile')

class ScholarshipList(LoginRequiredMixin, generic.View):
    template_name = 'scholarships/list.html'

    def get(self, request):
        scholarships = Scholarship.objects.all()
        if request.GET.get('q'):
            query = request.GET.get('q')
            queryset = Scholarship.objects.all()
            scholarships = queryset.filter(
                Q(title__icontains=query) |
                Q(description__icontains=query) |
                Q(tags__name__icontains=query)
            ).distinct().order_by('-created_at')
        if request.GET.get('level'):
            level = request.GET.get('level')
            scholarships = Scholarship.objects.filter(level__level__iexact=level)
        paginator = Paginator(scholarships, 10)
        page = int(request.GET.get('page', 1))
        try:
            scholarships = paginator.page(page)
        except:
            return HttpResponse('')
        bookmarks = Bookmark.objects.filter(user=request.user).values_list("scholarship_id", flat=True)
        context = {'scholarships':scholarships, 'page':page, 'bookmarked_ids':set(bookmarks)}
        if request.htmx:
            return render(request, 'scholarships/loop_scholarships.html', context)
        return render(request, self.template_name, context)
    
@login_required
def recommend_scholarships(request):
    profile = request.user.profile
    bookmarked_ids = Bookmark.objects.filter(user=request.user).values_list('scholarship_id', flat=True)
    applications_ids = Application.objects.filter(user=request.user).values_list('scholarship_id', flat=True)

    result = (Scholarship.objects.filter(Q(level__in=profile.level.all()) | Q(tags__in=profile.tags.all()))\
    .exclude(id__in=list(bookmarked_ids) + list(applications_ids))\
    .annotate(match_count=Count("tags", filter=Q(tags__in=profile.tags.all()))).order_by("-match_count", "end_date").distinct())

    return result

class ScholarshipDetail(LoginRequiredMixin, generic.DetailView):
    model = Scholarship
    template_name = 'scholarships/detail2.html'
    context_object_name = 'scholarship'

    def get_queryset(self):
        return Scholarship.objects.filter(active=True)
    
    def get_context_data(self, **kwargs):
        scholarship = self.object
        context = super().get_context_data(**kwargs)
        similar_scholarships = Scholarship.objects.filter(Q(tags__in=scholarship.tags.all()) | Q(level__in=scholarship.level.all())).exclude(id=scholarship.id)\
                                .annotate(match_count = Count('tags', filter=Q(tags__in=scholarship.tags.all()))).order_by('-match_count', 'end_date').distinct()[:10]
        recommended_scholarships = recommend_scholarships(self.request)[:5]
        context['similar_scholarships'] = similar_scholarships
        context['recommended_scholarships'] = recommended_scholarships

        return context

class CreateScholarship(LoginRequiredMixin, generic.CreateView):
    model = Scholarship
    template_name = 'scholarships/create.html'
    form_class = ScholarshipModelForm

    def get_success_url(self):
        return redirect('scholarship_list')

class UpdateScholarship(LoginRequiredMixin, generic.UpdateView):
    model = Scholarship
    template_name = 'scholarships/update.html'
    form_class = ScholarshipModelForm

    def get_success_url(self):
        return redirect('scholarship_detail', kwargs={'pk':self.get_object().id})

class DeleteScholarship(LoginRequiredMixin, generic.DeleteView):
    model = Scholarship

    def get_success_url(self):
        return reverse_lazy('scholarship_list')

@login_required
def bookmark(request, sch_id):
    scholarship = get_object_or_404(Scholarship, id=sch_id)
    Bookmark.objects.get_or_create(user=request.user, scholarship=scholarship)
    bookmarked_ids = Bookmark.objects.filter(user=request.user).values_list("scholarship_id", flat=True)
    
    return render(request, "partials/bookmark_button.html", {"scholarship": scholarship, 'bookmarked_ids':bookmarked_ids})

@login_required
def remove_bookmark(request, sch_id):
    scholarship = get_object_or_404(Scholarship, id=sch_id)
    # Bookmark.objects.filter(user=request.user, scholarship=scholarship).delete()
    request.user.bookmarked_scholarships.remove(scholarship)
    bookmarked_ids = Bookmark.objects.filter(user=request.user).values_list("scholarship_id", flat=True)
    return render(request, "partials/bookmark_button.html", {"scholarship": scholarship, 'bookmarked_ids':bookmarked_ids})

@login_required
def apply(request, sch_id):
    user = request.user
    scholarship = get_object_or_404(Scholarship, id=sch_id)
    application, created = Application.objects.get_or_create(user=user, scholarship=scholarship)
    return HttpResponseRedirect(scholarship.link)
    
@login_required
def unsave_scholarship(request, app_id):
   application = get_object_or_404(Application, user=request.user, id=app_id)
   application.delete()
   return redirect('dashboard')


@login_required
def save_scholarship(request, sch_id):
    user = request.user
    scholarship = get_object_or_404(Scholarship, id=sch_id)
    application, created = Application.objects.get_or_create(user=user, scholarship=scholarship)
    return redirect("scholarship_detail", scholarship.id)


@login_required
def change_application_status(request, app_id):
    application = get_object_or_404(Application, id=app_id)
    if request.method == 'POST':
        form = ApplicationStatusUpdateForm(request.POST, instance=application)
        if form.is_valid():
            form.save()
            return redirect('dashboard')
    else:
        form = ApplicationStatusUpdateForm(instance=application)
    return render(request, 'scholarship/dashboard2.html', {'status_form':form})



@login_required
def user_dashboard(request):
    user = request.user

    applied_scholarships = user.applied_scholarships.all()
    bookmarked_scholarships = user.bookmarked_scholarships.all()

    recent_applications = Application.objects.filter(
        user=user
    ).select_related('scholarship').order_by('-submitted_at')[:5]

    recent_bookmarks = Bookmark.objects.filter(
        user=user
    ).select_related('scholarship').order_by('-bookmarked_at')[:10]

    recommended_scholarships = recommend_scholarships(request)[:5]

    upcoming_deadlines = Scholarship.objects.filter(
        Q(applications__user=user) | Q(bookmarks__user=user),
        end_date__gte=timezone.now()
    ).order_by('end_date')[:5]

    application_status_counts = Application.objects.filter(user=user).values('status').annotate(total=Count('id'))

    recent_scholarships = Scholarship.objects.order_by('-created_at')[:5]

    stats = {
        'total_applications': applied_scholarships.count(),
        'total_bookmarks': bookmarked_scholarships.count(),
        'pending_applications': Application.objects.filter(user=user, status='pending').count(),
        'accepted_applications': Application.objects.filter(user=user, status='accepted').count(),
        'rejected_applications': Application.objects.filter(user=user, status='rejected').count(),
        'submitted_applications': Application.objects.filter(user=user, status='submitted').count(),
    }

    return render(request, 'scholarships/dashboard2.html', {
        'recent_applications': recent_applications,
        'recent_bookmarks': recent_bookmarks,
        'recommended_scholarships': recommended_scholarships,
        'upcoming_deadlines': upcoming_deadlines,
        'application_status_counts': application_status_counts,
        'recent_scholarships': recent_scholarships,
        'stats': stats,
        'applied_scholarships': applied_scholarships,
        'bookmarked_scholarships': bookmarked_scholarships
    })

@login_required
def update_profile(request):
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=request.user.profile)
        if form.is_valid():
            profile = form.save(commit=False)
            profile.user = request.user
            profile.save()
        return redirect('dashboard')
    form = ProfileForm(instance=request.user.profile)
    return render(request, 'scholarships/profile.html', {'form': form})


    
























# services:
#   - type: web
#     name: scholarscope-web
#     env: python
#     buildCommand: |
#       pip install --upgrade pip setuptools wheel
#       pip install -r requirements.txt
#       npm install --prefix theme/static_src
#       npm run build --prefix theme/static_src
#       python manage.py collectstatic --noinput

#     startCommand: |
#       python manage.py migrate
#       gunicorn scholarscope.wsgi:application --bind 0.0.0.0:$PORT
#     envVars:
#       - key: REDIS_URL
#         sync: false
#       - key: DATABASE_URL
#         sync: false

#   - type: worker
#     name: scholarscope-worker
#     env: python
#     buildCommand: |
#       pip install --upgrade pip setuptools wheel
#       pip install -r requirements.txt
#     startCommand: celery -A scholarscope worker -l info
#     envVars:
#       - key: REDIS_URL
#         sync: false
#       - key: DATABASE_URL
#         sync: false

#   - type: worker
#     name: scholarscope-beat
#     env: python
#     buildCommand: |
#       pip install --upgrade pip setuptools wheel
#       pip install -r requirements.txt
#     startCommand: celery -A scholarscope beat -l info
#     envVars:
#       - key: REDIS_URL
#         sync: false
#       - key: DATABASE_URL
#         sync: false

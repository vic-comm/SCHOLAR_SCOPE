from django.shortcuts import render, redirect, HttpResponseRedirect, get_object_or_404
from django.views import generic
from .models import Scholarship, Bookmark, Application
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.postgres.search import SearchVector, SearchRank, SearchQuery
from django.db.models import Q
from .forms import ScholarshipModelForm, ApplicationStatusUpdateForm
# Create your views here.
class ScholarshipList(LoginRequiredMixin, generic.ListView):
    model = Scholarship
    template_name = 'scholarships/list.html'
    context_object_name = 'scholarships'
    paginate_by = 10
    
    # def get_queryset(self):
    #     query = self.request.GET.get('q')
    #     query = SearchQuery(query)
    #     query_set = Scholarship.objects.all()

    #     if query:
    #         vector = SearchVector('title', weight='A') + SearchVector('description', weight='C')
    #         query_set = query_set.annotate(rank=SearchRank(vector, query)).filter(rant_gte=0.1).order_by('-rank')
    #     return query_set

    def get_queryset(self):
        query = self.request.GET.get('q')
        queryset = Scholarship.objects.all()

        if query:
            queryset = queryset.filter(
                Q(title__icontains=query) |
                Q(description__icontains=query) |
                Q(tags__name__icontains=query)
            ).distinct()

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('q', '')
        return context


class ScholarshipDetail(LoginRequiredMixin, generic.DetailView):
    model = Scholarship
    template_name = 'scholarships/detail.html'
    context_object_name = 'scholarship'

    def get_queryset(self):
        return Scholarship.objects.filter(active=True)
    

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
    template_name = 'scholarships/delete.html'

    def get_success_url(self):
        return redirect('scholarship_list')


    
def bookmark(request, sch_id):
    user = request.user
    scholarship = Scholarship.objects.get(id=sch_id)
    Bookmark.objects.get_or_create(user, scholarship)


def apply(request, sch_id):
    user = request.user
    scholarship = get_object_or_404(Scholarship, id=sch_id)
    application, created = Application.objects.get_or_create(user=user, scholarship=scholarship)
    return HttpResponseRedirect(scholarship.link)
    
def save_scholarship(request, sch_id):
    user = request.user
    scholarship = get_object_or_404(Scholarship, id=sch_id)
    application, created = Application.objects.get_or_create(user=user, schoarship=scholarship)
    return redirect("scholarship_detail")

def change_application_status(request, app_id):
    application = get_object_or_404(Application, id=app_id)
    if request.method == 'POST':
        form = ApplicationStatusUpdateForm(request.POST, instance=application)
        if form.is_valid():
            form.save()
            return redirect('')
    else:
        form = ApplicationStatusUpdateForm()
    return render(request, 'scholarship/dashboard.html', {'form':form})

def user_dashboard(request):
    """Dashboard showing both applied and bookmarked scholarships"""
    user = request.user
    applied_scholarships = user.applied_scholarships.all()
    bookmarked_scholarships = user.bookmarked_scholarships.all()
    # Recent applications (last 5)
    recent_applications = Application.objects.filter(
        user=user
    ).select_related('scholarship').order_by('-submitted_at')[:5]
    
    # Recent bookmarks (last 10)
    recent_bookmarks = Bookmark.objects.filter(
        user=user
    ).select_related('scholarship').order_by('-bookmarked_at')[:10]
    
    # Statistics
    stats = {
        'total_applications': user.applied_scholarships.count(),
        'total_bookmarks': user.bookmarked_scholarships.count(),
        'pending_applications': Application.objects.filter(
            user=user, status='pending'
        ).count()
    }
    
    return render(request, 'scholarships/dashboard.html', {
        'recent_applications': recent_applications,
        'recent_bookmarks': recent_bookmarks,
        'stats': stats,
        'applied_scholarships': applied_scholarships,
        'bookmarked_scholarships': bookmarked_scholarships
    })


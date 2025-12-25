from django.shortcuts import render, redirect, HttpResponseRedirect, get_object_or_404, HttpResponse
from django.urls import reverse_lazy
from django.views import generic
from allauth.account.views import SignupView
from .models import Scholarship, Bookmark, Application, Profile, SiteConfig
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.postgres.search import SearchVector, SearchRank, SearchQuery
from django.db.models import Q
from .forms import ScholarshipModelForm, ApplicationStatusUpdateForm, ProfileForm
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .serializers import (ScholarshipSerializer, UserDashBoardSerializer, ApplicationStatusSerializer, 
                          ApplicationSerializer, BookmarkSerializer, ProfileUpdateSerializer, SiteConfigSerializer)
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework import viewsets, status
from django.contrib import messages
from django.core.paginator import Paginator
from django.utils import timezone
from django.db.models import Q, Count
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from dj_rest_auth.registration.views import SocialLoginView
from django.conf import settings
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from .utils import get_cached_recommendations
from .serializers import ProfileSerializer
from rest_framework import permissions

class GoogleLogin(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter
    callback_url = settings.GOOGLE_OAUTH_CALLBACK_URL
    client_class = OAuth2Client
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
    
class ScholarshipViewset(viewsets.ModelViewSet):
    serializer_class = ScholarshipSerializer
    permission_classes = [IsAuthenticated]
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        else:
            return [IsAdminUser()]
    
    def get_queryset(self):
        queryset = Scholarship.objects.all()
        query = self.request.query_params.get('q')
        level = self.request.query_params.get('level') 
        tag = self.request.query_params.get('tag')        
        if query:
            scholarships = queryset.filter(
                Q(title__icontains=query) |
                Q(description__icontains=query) |
                Q(tags__name__icontains=query)
            ).distinct().order_by('-created_at')
        if level:
            scholarships = Scholarship.filter(level__level__iexact=level)
        if tag:
            scholarships = Scholarship.objects.filter(tag__name__iexact=tag)
        return scholarships.order_by('-created_at')
    
    @action(detail=True, methods=['post'])
    def bookmark_scholarship(self, request, pk=None):
        scholarship = get_object_or_404(Scholarship, id=pk)
        Bookmark.objects.get_or_create(user=request.user, scholarship=scholarship)
        return Response({'message':'Scholarship bookmarked'})

    @action(detail=True, methods=['post'])
    def unbookmark(self, request, pk=None):
        scholarship = get_object_or_404(Scholarship, id=pk)
        # Bookmark.objects.filter(user=request.user, scholarship=scholarship).delete()
        request.user.bookmarked_scholarships.remove(scholarship)
        return Response({'message':"Scholarship unbookmarked"})

    @action(detail=True, methods=['post'])
    def save(self, request, pk=None):
        user = request.user
        scholarship = get_object_or_404(Scholarship, id=pk)
        application, created = Application.objects.get_or_create(user=user, scholarship=scholarship)
        return Response({'message':'Scholarship saved'})

    @action(detail=True, methods=['post'])
    def unsave_scholarship(self, request, pk=None):
        scholarship = get_object_or_404(Scholarship, id=pk)
        application = get_object_or_404(Application, user=request.user, scholarship=scholarship)
        application.delete()
        return Response({'message':'Scholarship saved'})

    @action(detail=True, methods=['get'])
    def details(self, request, pk=None):
        scholarship = self.get_object()
        data = self.get_serializer(scholarship).data

        similar = Scholarship.objects.filter(Q(tags__in=scholarship.tags.all()) | Q(level__in=scholarship.level.all())).exclude(id=scholarship.id)\
                                .annotate(match_count = Count('tags', filter=Q(tags__in=scholarship.tags.all()))).order_by('-match_count', 'end_date').distinct()[:10]
        recommended = get_cached_recommendations(request.user)[:5]
        similar_data = self.get_serializer(similar, many=True).data
        recommended_data = self.get_serializer(recommended, many=True).data
        return Response({'data':data, 'similar_scholarships':similar_data, 'recommended_scholarships':recommended_data})
    
    @action(detail=True, methods=['post'])
    def apply(self, request, pk=None):
        user = self.request.user
        scholarship = get_object_or_404(Scholarship, id=pk)
        application, created = Application.objects.get_or_create(user=user, scholarship=scholarship)
        return Response({'message':"Application created", 'scholarship_link':scholarship.link, 'already_applied':not created})

def recommend_scholarships(request):
    profile = request.user.profile
    # user_vec = get_profile_embedding(profile)
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

class ApplicationStatusUpdateView(APIView):
    serializer_class = ApplicationStatusSerializer
    permission_classes = [IsAuthenticated]

    def patch(self, request, id):
        application =Application.objects.get(id=id)
        serializer = self.serializer_class(application, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
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

class ProfileViewSet(viewsets.ModelViewSet):
    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Profile.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def perform_update(self, serializer):
        serializer.save(user=self.request.user)

class UserViewset(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get', 'post'])
    def update_profile(self, request):
        profile = request.user.profile
        if request.method == 'POST':
            serializer = ProfileUpdateSerializer(data=request.data, instance=profile, partial=True)
            if serializer.is_valid():
                # serializer.user = request.user
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors)
        serializer = ProfileUpdateSerializer(instance=profile)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def user_dashboard(self, request):
        user = request.user
        applied_scholarships = user.applied_scholarships.all()
        bookmarked_scholarships = user.bookmarked_scholarships.all()

        recent_applications = Application.objects.filter(user=user).select_related('scholarship').order_by('-submitted_at')[:5]
        recent_bookmarks = Bookmark.objects.filter(
            user=user
        ).select_related('scholarship').order_by('-bookmarked_at')[:10]

        recommended_scholarships = get_cached_recommendations(user)[:5]

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

        data = {
            'recent_applications': ApplicationSerializer(recent_applications, many=True, context={'request': request}).data,
            'recent_bookmarks': BookmarkSerializer(recent_bookmarks,many=True, context={'request': request}).data,
            'recommended_scholarships': ScholarshipSerializer(recommended_scholarships, many=True, context={'request': request}).data,
            'upcoming_deadlines': ScholarshipSerializer(upcoming_deadlines, many=True, context={'request': request}).data,
            'application_status_counts': list(application_status_counts),
            'recent_scholarships': ScholarshipSerializer(recent_scholarships, many=True, context={'request': request}).data,
            'stats': stats,
            'applied_scholarships': ScholarshipSerializer(applied_scholarships, many=True, context={'request': request}).data,
            'bookmarked_scholarships': ScholarshipSerializer(bookmarked_scholarships, many=True, context={'request': request}).data
        }

        serializer = UserDashBoardSerializer(instance=data)
        return Response(serializer.data)





@api_view(['GET'])
@permission_classes([IsAuthenticated])
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

    data = {
        'recent_applications': ApplicationSerializer(recent_applications, many=True).data,
        'recent_bookmarks': BookmarkSerializer(recent_bookmarks,many=True).data,
        'recommended_scholarships': ScholarshipSerializer(recommended_scholarships, many=True).data,
        'upcoming_deadlines': ScholarshipSerializer(upcoming_deadlines, many=True).data,
        'application_status_counts': application_status_counts,
        'recent_scholarships': ScholarshipSerializer(recent_scholarships, many=True).data,
        'stats': stats,
        'applied_scholarships': ScholarshipSerializer(applied_scholarships, many=True).data,
        'bookmarked_scholarships': ScholarshipSerializer(bookmarked_scholarships, many=True).data
    }

    serializer = UserDashBoardSerializer(instance=data)
    return Response(serializer.data)

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


    
class SiteConfigViewset(viewsets.ModelViewSet):
    serializer_class = SiteConfigSerializer
    queryset = SiteConfig.objects.filter(active=True)

    def get_permissions(self):
        if self.request.method in ["GET", "HEAD", "OPTIONS"]:
            return [AllowAny()]
        else:
            return [IsAdminUser()]






















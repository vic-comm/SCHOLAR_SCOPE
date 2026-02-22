from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from allauth.account.views import SignupView
from .models import Scholarship, Bookmark, Application, Profile, SiteConfig, WatchedScholarship, ScrapeSubmission
from .tasks import process_new_submission
from rest_framework import status
from django.contrib.postgres.search import SearchVector, SearchRank, SearchQuery
from django.db.models import Q
from .serializers import (ScholarshipSerializer, UserDashBoardSerializer, ApplicationStatusSerializer, ScrapeSubmissionSerializer,
                          ApplicationSerializer, BookmarkSerializer, ProfileUpdateSerializer, SiteConfigSerializer)
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework import viewsets
from django.utils import timezone
from django.db.models import Q, Count
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from dj_rest_auth.registration.views import SocialLoginView
from django.conf import settings
from .utils import get_cached_recommendations
from .serializers import ProfileSerializer
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from asgiref.sync import async_to_sync
import datetime
import dateparser
from .models import Scholarship
from .utils import ScholarshipExtractor
from ..scholarscope_scrapers.scholarscope_scrapers.utils.llm_engine import LLMEngine
from ..scholarscope_scrapers.scholarscope_scrapers.utils.quality import QualityCheck
import logging

logger = logging.getLogger(__name__)

class GoogleOAuth2Client(OAuth2Client):
    def __init__(self, *args, **kwargs):
        if 'scope_delimiter' in kwargs:
            del kwargs['scope_delimiter']
        super().__init__(*args, **kwargs)

class GoogleLogin(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter
    client_class = GoogleOAuth2Client 
    callback_url = settings.GOOGLE_OAUTH_CALLBACK_URL 
    permission_classes = [AllowAny]

class CustomSignUpView(SignupView):
    def get_success_url(self):
        return reverse_lazy('update_profile')
    
class ScholarshipViewset(viewsets.ModelViewSet):
    serializer_class = ScholarshipSerializer
    permission_classes = [IsAuthenticated]
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'details']:
            return [AllowAny()] 
        elif self.action in ['bookmark_scholarship', 'unbookmark', 'save', 'unsave_scholarship', 'apply']:
            return [IsAuthenticated()]
        else:
            return [IsAdminUser()]
    
    # def get_queryset(self):
    #     queryset = Scholarship.objects.all()

    #     query = self.request.query_params.get("q")
    #     level = self.request.query_params.get("level")
    #     tag = self.request.query_params.get("tag")

    #     if level:
    #         queryset = queryset.filter(level__level__iexact=level)
    #     if tag:
    #         queryset = queryset.filter(tags__name__iexact=tag)

    #     if query:
    #         search_vector = (
    #             SearchVector("title", weight="A") +
    #             SearchVector("description", weight="B") +
    #             SearchVector("tags__name", weight="C")
    #         )
    #         search_query = SearchQuery(query)
            
    #         queryset = (
    #             queryset
    #             .annotate(rank=SearchRank(search_vector, search_query))
    #             .filter(rank__gte=0.1) 
    #             .order_by("-rank", "-created_at") 
    #             .distinct()
    #         )
    #     else:
    #         queryset = queryset.order_by("-created_at")

    #     return queryset
    def get_queryset(self):
        queryset = Scholarship.objects.all()
        
        query = self.request.query_params.get('q')
        level = self.request.query_params.get('level') 
        tag = self.request.query_params.get('tag')        
        
        if query:
            queryset = queryset.filter(
                Q(title__icontains=query) |
                Q(description__icontains=query) |
                Q(tags__name__icontains=query)
            ).distinct()
            
        if level:
            queryset = queryset.filter(level__level__iexact=level)
            
        if tag:
            queryset = queryset.filter(tags__name__iexact=tag)
            
        return queryset.order_by('-created_at')
    
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

    # @action(detail=True, methods=['get'])
    # def details(self, request, pk=None):
    #     scholarship = self.get_object()
    #     data = self.get_serializer(scholarship).data

    #     similar = Scholarship.objects.filter(Q(tags__in=scholarship.tags.all()) | Q(level__in=scholarship.level.all())).exclude(id=scholarship.id)\
    #                             .annotate(match_count = Count('tags', filter=Q(tags__in=scholarship.tags.all()))).order_by('-match_count', 'end_date').distinct()[:10]
    #     recommended = get_cached_recommendations(request.user)[:5]
    #     similar_data = self.get_serializer(similar, many=True).data
    #     recommended_data = self.get_serializer(recommended, many=True).data
    #     return Response({'data':data, 'similar_scholarships':similar_data, 'recommended_scholarships':recommended_data})
    
    @action(detail=True, methods=['get'])
    def details(self, request, pk=None):
        scholarship = self.get_object()
        data = self.get_serializer(scholarship).data

        similar = Scholarship.objects.filter(
            Q(tags__in=scholarship.tags.all()) | 
            Q(level__in=scholarship.level.all())
        ).exclude(id=scholarship.id).annotate(
            match_count=Count('tags', filter=Q(tags__in=scholarship.tags.all()))
        ).order_by('-match_count', 'end_date').distinct()[:10]
        
        similar_data = self.get_serializer(similar, many=True).data

        recommended_data = []
        if request.user.is_authenticated:
            try:
                recommended = get_cached_recommendations(request.user)[:5]
                recommended_data = self.get_serializer(recommended, many=True).data
            except Exception as e:
                print(f"Recommendation error: {e}")
                recommended_data = []

        return Response({
            'data': data, 
            'similar_scholarships': similar_data, 
            'recommended_scholarships': recommended_data
        })
    
    @action(detail=True, methods=['post'])
    def apply(self, request, pk=None):
        user = self.request.user
        scholarship = get_object_or_404(Scholarship, id=pk)
        application, created = Application.objects.get_or_create(user=user, scholarship=scholarship)
        return Response({'message':"Application created", 'scholarship_link':scholarship.link, 'already_applied':not created})

    @action(detail=True, methods=['post'])
    def toggle_watch_scholarship(self, request, pk=None):
        try:
            scholarship = Scholarship.objects.get(pk=pk)
        except Scholarship.DoesNotExist:
            return Response({"error": "Scholarship not found"}, status=404)

        watch_instance, created = WatchedScholarship.objects.get_or_create(
            user=request.user,
            scholarship=scholarship
        )

        if not created:
            watch_instance.delete()
            return Response({"status": "unwatched", "message": "You are no longer watching this scholarship."})

        return Response({
            "status": "watched", 
            "message": "You will be notified when this scholarship reopens next year."
        })
    
def recommend_scholarships(request):
    profile = request.user.profile
    bookmarked_ids = Bookmark.objects.filter(user=request.user).values_list('scholarship_id', flat=True)
    applications_ids = Application.objects.filter(user=request.user).values_list('scholarship_id', flat=True)

    result = (Scholarship.objects.filter(Q(level__in=profile.level.all()) | Q(tags__in=profile.tags.all()))\
    .exclude(id__in=list(bookmarked_ids) + list(applications_ids))\
    .annotate(match_count=Count("tags", filter=Q(tags__in=profile.tags.all()))).order_by("-match_count", "end_date").distinct())

    return result

# class ProfileViewSet(viewsets.ModelViewSet):
#     serializer_class = ProfileSerializer
#     permission_classes = [permissions.IsAuthenticated]

#     def get_queryset(self):
#         return Profile.objects.filter(user=self.request.user)

#     def perform_create(self, serializer):
#         serializer.save(user=self.request.user)

#     def perform_update(self, serializer):
#         serializer.save(user=self.request.user)

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
        watched_records = WatchedScholarship.objects.filter(user=user).select_related('scholarship')
        watched_scholarships = [record.scholarship for record in watched_records]
        recent_applications = Application.objects.filter(user=user).select_related('scholarship').order_by('-submitted_at')
        recent_apps = list(ApplicationSerializer(recent_applications, many=True, context={'request': request}).data)
        recent_bookmarks = Bookmark.objects.filter(
            user=user
        ).select_related('scholarship').order_by('-bookmarked_at')
        personal_scrapes = ScrapeSubmission.objects.filter(user=user).order_by('-created_at')

        normalized_scrapes = []
        for item in personal_scrapes:
            scholarship_details = item.scholarship
            normalized_scrapes.append({
                'id': item.id,               
                'status': item.application_status, 
                'submitted_at': item.created_at,
                'scholarship': {
                    # Check if relationship exists first
                    'id': item.scholarship.id if item.scholarship else None,
                    'title': item.title,
                    'link': item.link,
                    'reward': item.reward,
                    'end_date': item.deadline,
                    'is_official': False 
                },
                'is_scrape': True 
            })

        # 5. Merge and Sort
        # Add a flag to official apps too
        for item in recent_apps:
            item['is_scrape'] = False
            item['scholarship']['is_official'] = True

        all_tracked_items = sorted(
            recent_apps + normalized_scrapes, 
            key=lambda x: x['submitted_at'], 
            reverse=True
        )
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
            'profile_completion': user.profile.completion_percentage,
            'submitted_applications': Application.objects.filter(user=user, status='submitted').count(),
        }

        data = {
            # 'recent_applications': ApplicationSerializer(recent_applications, many=True, context={'request': request}).data,
            'recent_bookmarks': BookmarkSerializer(recent_bookmarks,many=True, context={'request': request}).data,
            'recommended_scholarships': ScholarshipSerializer(recommended_scholarships, many=True, context={'request': request}).data,
            'upcoming_deadlines': ScholarshipSerializer(upcoming_deadlines, many=True, context={'request': request}).data,
            'application_status_counts': list(application_status_counts),
            'recent_scholarships': ScholarshipSerializer(recent_scholarships, many=True, context={'request': request}).data,
            'stats': stats,
            'applied_scholarships': ScholarshipSerializer(applied_scholarships, many=True, context={'request': request}).data,
            'bookmarked_scholarships': ScholarshipSerializer(bookmarked_scholarships, many=True, context={'request': request}).data,
            # 'personal_scrapes': ScrapeSubmissionSerializer(personal_scrapes, many=True).data,
            'recent_applications': all_tracked_items,
            'watched_scholarships': ScholarshipSerializer(watched_scholarships, many=True, context={'request': request}).data
        }

        serializer = UserDashBoardSerializer(instance=data)
        return Response(data)


    
class SiteConfigViewset(viewsets.ModelViewSet):
    serializer_class = SiteConfigSerializer
    queryset = SiteConfig.objects.filter(active=True)

    def get_permissions(self):
        if self.request.method in ["GET", "HEAD", "OPTIONS"]:
            return [AllowAny()]
        else:
            return [IsAdminUser()]


class ScrapeSubmissionViewset(viewsets.ModelViewSet):
    queryset = ScrapeSubmission.objects.all()
    serializer_class = ScrapeSubmissionSerializer
    
    def get_queryset(self):
        return ScrapeSubmission.objects.filter(user=self.request.user)

    def partial_update(self, request, *args, **kwargs):
        submission = self.get_object()
        
        new_status = request.data.get('application_status')
        if new_status:
            submission.application_status = new_status
            submission.save()
            return Response({'status': 'updated', 'application_status': new_status})
        return Response({'error': 'No status provided'}, status=status.HTTP_400_BAD_REQUEST)
    
    def create(self, request, *args, **kwargs):
        data = request.data
        link = data.get('link')

        submission = ScrapeSubmission.objects.create(
            user=request.user,
            link=link,
            title=data.get('title'),
            raw_data=data,
            application_status='pending'
        )

        existing_scholarship = Scholarship.objects.filter(link=link).first()
        
        if existing_scholarship:
            submission.scholarship = existing_scholarship
            submission.status = 'APPROVED'
            submission.save()
            Application.objects.get_or_create(user=request.user, scholarship=existing_scholarship)
            return Response({"message": "Scholarship found! Added to your applications."}, status=status.HTTP_200_OK)        
        else:
            process_new_submission.delay(submission.id)
            return Response({"message": "Saved! Processing for public verification..."}, status=status.HTTP_201_CREATED)

# @api_view(['POST'])
# @permission_classes([IsAuthenticated])
# def extract_from_html(request):
#     raw_html = request.data.get('raw_html')
#     url = request.data.get('url')
#     title_from_ext = request.data.get('title', 'Unknown Title')

#     if not raw_html:
#         return Response({"error": "No HTML provided"}, status=400)

#     # 1. Initialize our unified Extractor
#     extractor = ScholarshipExtractor(raw_html=raw_html, url=url)

#     # 2. Extract initial structured data from the messy HTML
#     item = {
#         "title": extractor.extract_title() or title_from_ext,
#         "description": extractor.extract_description(),
#         "reward": extractor.extract_reward(),
#         "link": url,
#         "end_date": extractor.extract_date('end'),
#         "start_date": extractor.extract_date('start'),
#         "requirements": extractor.extract_requirements(),
#         "eligibility": extractor.extract_eligibility(),
#         "tags": extractor.extract_tags(),
#         "levels": extractor.extract_levels(),
#         "scraped_at": datetime.now().isoformat(),
#     }

#     # 3. Quality Check
#     quality_report = QualityCheck.get_quality_score(
#         item, 
#         ["title", "reward", "end_date", "description", "requirements", "eligibility"]
#     )
    
#     # 4. The LLM Engine Integration (Using async_to_sync)
#     llm_engine = LLMEngine()
    
#     if QualityCheck.should_full_regenerate(quality_report):
#         print(f"Data corrupted. Requesting FULL LLM extraction. Score: {quality_report['quality_score']}")
        
#         # async_to_sync wraps the async method so it runs synchronously in this view
#         recovered_data = async_to_sync(llm_engine.extract_data)(extractor.clean_text, url)
        
#         if isinstance(recovered_data, list) and len(recovered_data) > 0:
#             recovered_data = recovered_data[0]
            
#             # Parse dates safely
#             if recovered_data.get("end_date"):
#                 recovered_data["end_date"] = dateparser.parse(recovered_data["end_date"]).date()
#             if recovered_data.get("start_date"):
#                 recovered_data["start_date"] = dateparser.parse(recovered_data["start_date"]).date()
            
#             # Overwrite the weak regex data with the AI data
#             item.update(recovered_data)
            
#     elif quality_report['needs_llm']:
#         fields_to_fix = list(set(quality_report['failed_fields'] + [x[0] for x in quality_report['low_confidence_fields']]))
        
#         if fields_to_fix:
#             print(f"Asking Gemini to fix: {fields_to_fix}")
#             recovered_data = async_to_sync(llm_engine.recover_specific_fields)(extractor.clean_text, fields_to_fix)
            
#             # Parse dates safely if the AI fixed them
#             if recovered_data.get("end_date") and isinstance(recovered_data["end_date"], str):
#                 dt = dateparser.parse(recovered_data["end_date"])
#                 if dt: recovered_data["end_date"] = dt.date()
                
#             if recovered_data.get("start_date") and isinstance(recovered_data["start_date"], str):
#                 dt = dateparser.parse(recovered_data["start_date"])
#                 if dt: recovered_data["start_date"] = dt.date()
                
#             item.update(recovered_data)

#     # 5. Ensure lists are actually lists before DB insertion
#     for field in ["requirements", "eligibility", "tags", "levels"]:
#         if item.get(field) is None:
#             item[field] = []

#     # 6. Save to Database
#     try:
#         scholarship = Scholarship.objects.create(
#             title=item.get('title', 'Unknown Title')[:255],
#             link=item.get('link', url),
#             description=item.get('description', 'No description'),
#             eligibility=item.get('eligibility', []),
#             requirements=item.get('requirements', []),
#             reward=item.get('reward', ''),
#             tags=item.get('tags', []),
#             levels=item.get('levels', []),
#             source="Chrome Extension",
#             status="active",
#             end_date=item.get('end_date'),
#             start_date=item.get('start_date')
#         )

#         return Response({
#             "message": "Successfully extracted and saved!", 
#             "id": scholarship.id
#         }, status=201)
        
#     except Exception as e:
#         print(f"Error saving scholarship: {str(e)}")
#         return Response({"error": "Failed to save to database."}, status=500)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def extract_from_html(request):
    raw_html        = request.data.get("raw_html")
    url             = request.data.get("url", "")
    title_from_ext  = request.data.get("title", "Unknown Title")

    if not raw_html:
        return Response({"error": "No HTML provided"}, status=400)

    # ── 1. Extract with the shared engine ────────────────────────────────────
    extractor = ScholarshipExtractor(raw_html=raw_html, url=url)

    item = {
        "title":        extractor.extract_title() or title_from_ext,
        "description":  extractor.extract_description(),
        "reward":       extractor.extract_reward(),
        "link":         url,
        "end_date":     extractor.extract_date("end"),
        "start_date":   extractor.extract_date("start"),
        "requirements": extractor.extract_requirements(),
        "eligibility":  extractor.extract_eligibility(),
        "tags":         extractor.extract_tags(),
        "levels":       extractor.extract_levels(),
        "scraped_at":   datetime.now().isoformat(),
    }

    # ── 2. Quality check ──────────────────────────────────────────────────────
    quality_report = QualityCheck.get_quality_score(
        item,
        ["title", "reward", "end_date", "description", "requirements", "eligibility"],
    )
    llm_engine = LLMEngine()

    if QualityCheck.should_full_regenerate(quality_report):
        print(f"Data corrupted — full LLM extraction. Score: {quality_report['quality_score']}")
        recovered = async_to_sync(llm_engine.extract_data)(extractor.clean_text, url)
        if isinstance(recovered, list) and recovered:
            recovered = recovered[0]
        _parse_dates_inplace(recovered)
        item.update(recovered)

    elif quality_report["needs_llm"]:
        fields = list(set(
            quality_report["failed_fields"]
            + [f for f, _ in quality_report["low_confidence_fields"]]
        ))
        if fields:
            print(f"Partial LLM fix for: {fields}")
            recovered = async_to_sync(llm_engine.recover_specific_fields)(
                extractor.clean_text, fields
            )
            _parse_dates_inplace(recovered)
            item.update(recovered)

    # ── 3. Guard rails ────────────────────────────────────────────────────────
    for field in ["requirements", "eligibility", "tags", "levels"]:
        if item.get(field) is None:
            item[field] = []

    # ── 4. Persist ────────────────────────────────────────────────────────────
    try:
        scholarship = Scholarship.objects.create(
            title=item.get("title", "Unknown Title")[:255],
            link=item.get("link", url),
            description=item.get("description", "No description"),
            eligibility=item.get("eligibility", []),
            requirements=item.get("requirements", []),
            reward=item.get("reward", ""),
            tags=item.get("tags", []),
            levels=item.get("levels", []),
            source="Chrome Extension",
            status="active",
            end_date=item.get("end_date"),
            start_date=item.get("start_date"),
        )
        return Response({"message": "Successfully extracted and saved!", "id": scholarship.id}, status=201)

    except Exception as e:
        print(f"DB save error: {e}")
        return Response({"error": "Failed to save to database."}, status=500)


# ─────────────────────────────────────────────────────────────────────────────
# Shared helper (also used by the spider)
# ─────────────────────────────────────────────────────────────────────────────

def _parse_dates_inplace(data: dict) -> None:
    for key in ("end_date", "start_date"):
        val = data.get(key)
        if isinstance(val, str):
            dt = dateparser.parse(val)
            data[key] = dt.date() if dt else None

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def draft_application_essays(request):
    """
    POST /api/scholarships/draft_essays/

    Body:
        {
            "prompts": [
                {"id": "scholarscope-ta-0", "prompt": "Why do you deserve this?", "max_words": 200},
                ...
            ]
        }

    Returns:
        {
            "drafts": [
                {"id": "...", "draft": "...", "word_count": 143, "confidence": "high"},
                ...
            ],
            "profile_completeness": 72   // % of profile fields filled — UI can warn user
        }
    """
    prompts_list = request.data.get("prompts", [])

    if not prompts_list:
        return Response({"error": "No prompts provided."}, status=400)

    if len(prompts_list) > 10:
        return Response({"error": "Maximum 10 prompts per request."}, status=400)

    # ── Build user profile from the authenticated user ──────────────────────
    user = request.user

    # Safely access the related profile — handle missing profile gracefully
    profile = getattr(user, "profile", None)
    def prof(attr, default=""):
        return getattr(profile, attr, default) if profile else default

    user_profile = {
        "first_name":      user.first_name,
        "last_name":       user.last_name,
        "field_of_study":  prof("field_of_study"),
        "institution":     prof("institution"),
        "year_of_study":   prof("year_of_study"),
        "gpa":             prof("gpa"),
        "country":         prof("country"),
        "bio":             prof("bio"),
        "achievements":    prof("achievements"),
        "career_goals":    prof("career_goals"),
        "extracurriculars":prof("extracurriculars"),
        "financial_need":  prof("financial_need"),
    }

    # Compute profile completeness score so the frontend can warn sparse users
    key_fields = ["bio", "achievements", "career_goals", "extracurriculars", "field_of_study", "institution"]
    filled = sum(1 for f in key_fields if user_profile.get(f))
    completeness_pct = round((filled / len(key_fields)) * 100)

    # Warn, but still proceed — let the LLM do its best with what's available
    if completeness_pct < 30:
        logger.warning(
            f"User {user.id} has a very sparse profile ({completeness_pct}%) — essay quality will be low."
        )

    # ── Call LLM ────────────────────────────────────────────────────────────
    llm = LLMEngine()

    try:
        drafted_responses = async_to_sync(llm.draft_essays)(user_profile, prompts_list)
    except Exception as exc:
        logger.exception(f"draft_application_essays: LLM failure for user {user.id}: {exc}")
        return Response({"error": "Essay drafting failed. Please try again."}, status=500)

    # Surface any per-prompt failures without crashing the whole response
    failures = [d for d in drafted_responses if d.get("confidence") == "failed"]
    if failures:
        logger.warning(f"{len(failures)} prompt(s) failed for user {user.id}: {failures}")

    return Response({
        "drafts":               drafted_responses,
        "profile_completeness": completeness_pct,
    }, status=200)

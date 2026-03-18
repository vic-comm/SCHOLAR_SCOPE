from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from allauth.account.views import SignupView
from scholarships.models import Scholarship, Bookmark, Application, Profile, SiteConfig, WatchedScholarship, ScrapeSubmission, Tag, Level
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
from rest_framework.decorators import api_view, permission_classes
from asgiref.sync import async_to_sync
import datetime
import dateparser
from .utils import ScholarshipExtractor
from scholarscope_scrapers.scholarscope_scrapers.utils.llm_engine import LLMEngine
from scholarscope_scrapers.scholarscope_scrapers.utils.quality import QualityCheck
import uuid
from django.core.cache import cache
from scholarships.tasks import draft_essays_batch
import logging
from urllib.parse import urlparse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from scholarships.pagination import ScholarshipCursorPagination
from django.db.models import Exists, OuterRef
from .pagination import ScholarshipCursorPagination
from .models import Scholarship, Bookmark, WatchedScholarship
from django.shortcuts import get_object_or_404, render
from django.contrib.auth import get_user_model
from django.core.signing import Signer, BadSignature
from django.http import HttpResponseBadRequest
from scholarships.authentication import OptionalJWTAuthentication
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

logger = logging.getLogger(__name__)
User = get_user_model()
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
    pagination_class = ScholarshipCursorPagination
    authentication_classes = [OptionalJWTAuthentication]

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'details']:
            return [AllowAny()] 
        elif self.action in ['bookmark_scholarship', 'unbookmark', 'save', 'unsave_scholarship', 'apply', 'create']:
            return [IsAuthenticated()]
        else:
            return [IsAdminUser()]
        
    def get_queryset(self):
        queryset = Scholarship.objects.all()

        query = self.request.query_params.get("q")
        level = self.request.query_params.get("level")
        tag = self.request.query_params.get("tag")

        user = self.request.user
        if user and user.is_authenticated:
            queryset = queryset.annotate(
                _bookmarked_by_user=Exists(
                    Bookmark.objects.filter(
                        user=user, scholarship=OuterRef('pk')
                    )
                ),
                _saved_by_user=Exists(
                    Application.objects.filter(
                        user=user, scholarship=OuterRef('pk')
                    )
                ),
                _watched_by_user=Exists(
                    WatchedScholarship.objects.filter(
                        user=user, scholarship=OuterRef('pk')
                    )
                ),
            )

        if level:
            queryset = queryset.filter(level__level__iexact=level)
        if tag:
            queryset = queryset.filter(tags__name__iexact=tag)

        if query:
            search_vector = (
                SearchVector("title", weight="A") +
                SearchVector("description", weight="B") +
                SearchVector("tags__name", weight="C")
            )
            search_query = SearchQuery(query)
            
            queryset = (
                queryset
                .annotate(rank=SearchRank(search_vector, search_query))
                .filter(rank__gte=0.1) 
                .order_by("-rank", "-created_at") 
                .distinct()
            )
        else:
            queryset = queryset.order_by("-created_at")

        return queryset
    
    @action(detail=True, methods=['post'])
    def bookmark_scholarship(self, request, pk=None):
        scholarship = get_object_or_404(Scholarship, id=pk)
        Bookmark.objects.get_or_create(user=request.user, scholarship=scholarship)
        return Response({'message':'Scholarship bookmarked'})

    @action(detail=True, methods=['post'])
    def unbookmark(self, request, pk=None):
        scholarship = get_object_or_404(Scholarship, id=pk)
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

class ApplicationViewSet(viewsets.ModelViewSet):
    serializer_class = ApplicationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Application.objects.filter(user=self.request.user)

    @action(detail=True, methods=['patch'])
    def update_status(self, request, pk=None):
        application = self.get_object()
        new_status = request.data.get('status')

        valid_statuses = [choice[0] for choice in Application.STATUS_CHOICES]
        if new_status not in valid_statuses:
            return Response(
                {"error": f"Invalid status. Must be one of: {valid_statuses}"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        application.status = new_status
        application.save()
        return Response({"status": "Status updated successfully", "new_status": application.status})

class UserViewset(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get', 'post'])
    def update_profile(self, request):
        profile = request.user.profile
        if request.method == 'POST':
            serializer = ProfileUpdateSerializer(data=request.data, instance=profile, partial=True)
            if serializer.is_valid():
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
        # recent_apps = list(ApplicationSerializer(recent_applications, many=True, context={'request': request}).data)
        recent_bookmarks = Bookmark.objects.filter(
            user=user
        ).select_related('scholarship').order_by('-bookmarked_at')
        personal_scrapes = ScrapeSubmission.objects.filter(user=user).exclude(status='APPROVED').order_by('-created_at')
        recent_apps = []
        for app in recent_applications:
            app_dict = ApplicationSerializer(app, context={'request': request}).data
            app_dict['is_scrape'] = False
            
            # Replace the integer ID with a full dictionary
            if app.scholarship:
                app_dict['scholarship'] = {
                    'id': app.scholarship.id,
                    'title': app.scholarship.title,
                    'link': getattr(app.scholarship, 'link', ''),
                    'reward': getattr(app.scholarship, 'reward', None),
                    'end_date': getattr(app.scholarship, 'end_date', None),
                    'is_official': True  
                }
            else:
                app_dict['scholarship'] = None
                
            recent_apps.append(app_dict)

        normalized_scrapes = []
        for item in personal_scrapes:
            normalized_scrapes.append({
                'id': item.id,               
                'status': item.application_status, 
                'submitted_at': item.created_at.isoformat() if item.created_at else None,
                'scholarship': {
                    # Check if relationship exists first
                    'id': item.scholarship.id if item.scholarship else None,
                    'title': item.title,
                    'link': item.link,
                    'reward': getattr(item, 'reward', None),
                    'end_date': getattr(item, 'deadline', None),
                    'is_official': False 
                },
                'is_scrape': True 
            })

       
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
            'total_applications': len(all_tracked_items),
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
        data  = request.data
        link  = data.get('url')
        title = data.get('title', '')

        # ── Fast path: scholarship already in DB ──────────────────────────────
        existing_scholarship = Scholarship.objects.filter(link=link).first()
        if existing_scholarship:
            submission, _ = ScrapeSubmission.objects.get_or_create(
                user=request.user,
                link=link,
                defaults={
                    'title':              title,
                    'raw_data':           data,
                    'application_status': 'pending',
                    'scholarship':        existing_scholarship,
                    'status':             'APPROVED',
                }
            )
            Application.objects.get_or_create(
                user=request.user,
                scholarship=existing_scholarship,
            )
            sparse_fields = _sparse_scholarship_fields(existing_scholarship)
            return Response(
                {
                    "id":            existing_scholarship.id,
                    "submission_id": submission.id,
                    "message":       "Scholarship found! Added to your applications.",
                    # data_quality drives the frontend notice:
                    # 'full'   → success screen, no warnings
                    # 'sparse' → success screen + "missing fields" notice
                    "data_quality":  "sparse" if sparse_fields else "full",
                    "sparse_fields": sparse_fields,
                },
                status=status.HTTP_200_OK,
            )

        # ── New submission: queue processing, return submission ID ────────────
        # The frontend polls /submissions/<id>/status/ to find out what happened.
        # We do NOT try to predict quality here — the Celery task already has
        # QualityCheck built in, and it knows far more than the view does.
        submission, created = ScrapeSubmission.objects.get_or_create(
            user=request.user,
            link=link,
            defaults={
                'title':              title,
                'raw_data':           data,
                'application_status': 'pending',
                'status':             'PENDING',
            }
        )

        if not created and submission.status in ['REJECTED', 'FAILED']:
            submission.status = 'PENDING'
            submission.raw_data = data 
            submission.save()
            
        if created or submission.status == 'PENDING':
            process_new_submission.delay(submission.id)

        return Response(
            {
                "id":            None,           # scholarship ID not known yet
                "submission_id": submission.id,  # frontend polls this
                "message":       "Saved! Processing…",
                "data_quality":  "processing",
                "sparse_fields": [],
            },
            status=status.HTTP_201_CREATED,
        )

    # ── Polling endpoint ──────────────────────────────────────────────────────
    # GET /submissions/<id>/status/
    # Called by the frontend every ~2s until status is no longer PENDING.
    # Returns data_quality so the frontend knows what toast/notice to show.
    @action(detail=True, methods=['get'])
    def submission_status(self, request, pk=None):
        sub = self.get_object()

        if sub.status == 'PENDING':
            return Response({
                "submission_status": "processing",
                "data_quality":      "processing",
                "sparse_fields":     [],
            })

        if sub.status == 'REJECTED':
            # QualityCheck flagged it as garbage or AI confirmed not a scholarship.
            # raw_data['rejection_reason'] is set by process_new_submission.
            reason = sub.raw_data.get('rejection_reason', '')
            return Response({
                "submission_status": "rejected",
                "data_quality":      "none",
                "rejection_reason":  reason,
                "sparse_fields":     [],
            })

        if sub.status == 'APPROVED' and sub.scholarship:
            sparse_fields = _sparse_scholarship_fields(sub.scholarship)
            return Response({
                "submission_status": "approved",
                "scholarship_id":    sub.scholarship.id,
                "data_quality":      "sparse" if sparse_fields else "full",
                "sparse_fields":     sparse_fields,
            })

        # Fallback: still transitioning
        return Response({
            "submission_status": "processing",
            "data_quality":      "processing",
            "sparse_fields":     [],
        })

    @action(detail=True, methods=['patch'])
    def update_status(self, request, pk=None):
        scrape     = self.get_object()
        new_status = request.data.get('status')
        valid      = ['pending', 'submitted', 'rejected', 'accepted']
        if new_status not in valid:
            return Response(
                {"error": f"Invalid status. Must be one of: {valid}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        scrape.application_status = new_status
        scrape.save()
        return Response({
            "status":     "Status updated successfully",
            "new_status": scrape.application_status,
        })


def _sparse_scholarship_fields(scholarship) -> list:
    """
    Returns names of fields that are missing or thin on a Scholarship record.
    Used to warn the frontend when a saved record won't produce good essay drafts.
    """
    sparse = []
    if not scholarship.description or len(scholarship.description.strip()) < 20:
        sparse.append('description')
    if not scholarship.eligibility or scholarship.eligibility == []:
        sparse.append('eligibility')
    if not scholarship.requirements or scholarship.requirements == []:
        sparse.append('requirements')
    if not scholarship.reward or len(str(scholarship.reward).strip()) < 3:
        sparse.append('reward')
    if not scholarship.end_date:
        sparse.append('deadline')
    return sparse

@extend_schema(request=dict, responses={201: dict, 400: dict, 500: dict})
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def extract_from_html(request):
    raw_html        = request.data.get("raw_html")
    url             = request.data.get("url", "")
    title_from_ext  = request.data.get("title", "Unknown Title")

    if not raw_html:
        return Response({"error": "No HTML provided"}, status=400)

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


# Shared helper (also used by the spider)

def _parse_dates_inplace(data: dict) -> None:
    for key in ("end_date", "start_date"):
        val = data.get(key)
        if isinstance(val, str):
            dt = dateparser.parse(val)
            data[key] = dt.date() if dt else None

def _normalise_url(raw: str) -> str:
    parsed = urlparse(raw)
    return parsed._replace(fragment="").geturl().rstrip("/")

@extend_schema(request=dict, responses={200: dict, 400: dict, 429: dict})
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def regenerate_essay(request):
    """
    POST /api/scholarships/regenerate_essay/

    Regenerates a single essay draft with a user-provided refinement instruction.

    Body:
        {
            "prompt":      "Describe a time you showed leadership.",
            "current_draft": "The current AI-written text...",
            "instruction": "Make this more enthusiastic and mention my coding bootcamp.",
            "max_words":   200
        }

    Returns:
        {
            "draft":      "Revised essay text...",
            "word_count": 187,
            "confidence": "high"
        }
    """
    prompt        = (request.data.get("prompt") or "").strip()
    current_draft = (request.data.get("current_draft") or "").strip()
    instruction   = (request.data.get("instruction") or "").strip()
    max_words     = int(request.data.get("max_words") or 200)

    if not prompt:
        return Response({"error": "Essay prompt is required."}, status=400)
    if not instruction:
        return Response({"error": "Refinement instruction is required."}, status=400)

    user    = request.user
    profile = getattr(user, "profile", None)

    def _get_profile_dict():
        if not profile:
            return {"first_name": user.first_name}
        return {
            "first_name":   user.first_name,
            "last_name":    user.last_name,
            "field_of_study": profile.field_of_study,
            "institution":  profile.institution,
            "bio":          profile.bio,
            "career_goals": getattr(profile, "career_goals", ""),
            "achievements": getattr(profile, "academic_achievements", ""),
        }

    llm = LLMEngine()

    try:
        result = async_to_sync(llm.refine_essay)(
            profile_dict=_get_profile_dict(),
            original_prompt=prompt,
            current_draft=current_draft,
            instruction=instruction,
            max_words=max_words,
        )
        return Response(result, status=200)

    except Exception as exc:
        logger.exception(f"regenerate_essay: failed for user {user.id}: {exc}")
        return Response(
        {"error": "AI is currently busy or rate-limited. Please wait a minute and try again."}, 
        status=status.HTTP_429_TOO_MANY_REQUESTS)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_essay_draft_status(request, job_id: str):
    """
    GET /api/scholarships/draft_essays/status/{job_id}/
    
    Returns current job state. Client polls every 2-3 seconds.
    """
    result = cache.get(f"essay_job:{job_id}")

    if result is None:
        return Response({"error": "Job not found or expired."}, status=404)

    return Response(result, status=200)

@extend_schema(
    parameters=[
        OpenApiParameter(name="title", type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
        OpenApiParameter(name="url", type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
    ],
    responses={200: dict}
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def check_scholarship(request):
    """
    GET /api/scholarships/check/?title=<page_title>&url=<page_url>

    Updated strategy — title-based matching + suggestions fallback:
      1. Try exact title match (iexact)
      2. Try partial title match (icontains on first 40 chars)
      3. Try URL match as last resort
      4. If nothing found, return the 5 most recently saved scholarships
         as suggestions so the user can manually link from the popup

    Response when found:
        { "id": 42, "title": "Gates Millennium Scholars", "matched": true }

    Response when not found (with suggestions):
        {
          "id": null,
          "matched": false,
          "suggestions": [
            {"id": 12, "title": "NHEF Scholars Program"},
            {"id": 8,  "title": "MTN Foundation Scholarship"},
            ...
          ]
        }
    """
    raw_title = request.query_params.get("title", "").strip()
    raw_url   = request.query_params.get("url",   "").strip()

    scholarship = None

    # 1. Title exact match
    if raw_title:
        scholarship = Scholarship.objects.filter(
            title__iexact=raw_title
        ).first()

    # 2. Partial title match — use first 40 chars to avoid noise
    if not scholarship and raw_title:
        short = raw_title[:40]
        scholarship = (
            Scholarship.objects.filter(title__icontains=short).first()
            # Also try if the saved title is a substring of the page title
            # e.g. saved "NHEF" matches page "NHEF Scholars Program Application"
            or _fuzzy_title_match(raw_title)
        )

    # 3. URL fallback (still useful if user is on the exact saved URL)
    if not scholarship and raw_url:
        normalised = _normalise_url(raw_url)
        scholarship = (
            Scholarship.objects.filter(link=normalised).first()
            or Scholarship.objects.filter(link=raw_url).first()
        )

    if scholarship:
        return Response({
            "id":      scholarship.id,
            "title":   scholarship.title,
            "matched": True,
        }, status=200)

    # 4. No match — return recent scholarships as manual-link suggestions
    suggestions = (
        Scholarship.objects
        .order_by("-id")
        .values("id", "title")[:5]
    )
    return Response({
        "id":          None,
        "matched":     False,
        "suggestions": list(suggestions),
    }, status=200)


def _fuzzy_title_match(page_title: str):
    """
    Check if any saved scholarship title appears as a substring of the page title.
    Handles: page title = "NHEF Scholars Program Application 2026"
             saved title = "NHEF"  or  "NHEF Scholars Program"
    """
    # Only worth doing for short saved titles (long ones use icontains above)
    for s in Scholarship.objects.only("id", "title").order_by("-id")[:100]:
        if s.title and len(s.title) >= 4 and s.title.lower() in page_title.lower():
            return s
    return None


def _normalise_url(raw: str) -> str:
    parsed = urlparse(raw)
    return parsed._replace(query="", fragment="").geturl().rstrip("/")


@extend_schema(request=dict, responses={202: dict, 400: dict, 404: dict})
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def start_essay_draft(request):
    """
    POST /api/scholarships/draft_essays/

    Body:
        {
            "prompts": [...],

            // Tier 1 — ID of a saved scholarship record (best)
            "scholarship_id": 42,

            // Tier 2 — inline form fields (good)
            "scholarship_context": {
                "name": "...", "audience": "...", "values": "..."
            },

            // Tier 3 — always sent, page title/URL (minimum baseline)
            "page_metadata": {
                "title": "NHEF Scholars Program Application",
                "url":   "https://portal.thenhef.org/..."
            }
        }
    """
    # ── Deduplicate + cap prompts ─────────────────────────────────────────
    raw_prompts = request.data.get("prompts", [])
    seen, deduped = set(), []
    for item in raw_prompts:
        key = item.get("prompt", "").strip().lower()[:100]
        if key and key not in seen:
            seen.add(key)
            deduped.append(item)
    prompts_list = deduped[:10]

    if not prompts_list:
        return Response({"error": "No prompts provided."}, status=400)

    # ── Profile ───────────────────────────────────────────────────────────
    user    = request.user
    profile = getattr(user, "profile", None)
    if not profile:
        return Response({"error": "Profile not found."}, status=404)

    # ── Build context in priority order ──────────────────────────────────
    structured_context = _build_profile_context(user, profile)

    scholarship_id      = request.data.get("scholarship_id")
    scholarship_context = request.data.get("scholarship_context") or {}
    page_metadata       = request.data.get("page_metadata") or {}

    if scholarship_id:
        # Tier 1: Full record from DB — richest context
        rich = _build_rich_scholarship_context(scholarship_id)
        if rich:
            structured_context += rich
        else:
            # Record not found — fall through to tier 2/3
            scholarship_id = None

    if not scholarship_id:
        if isinstance(scholarship_context, dict) and any(
            (scholarship_context.get(k) or "").strip()
            for k in ("name", "audience", "values")
        ):
            # Tier 2: Inline form fields
            structured_context += _build_inline_context_block(scholarship_context)
        elif page_metadata.get("title"):
            # Tier 3: Page title only — at least the LLM knows what it's writing for
            structured_context += _build_page_metadata_block(page_metadata)

    # ── Enqueue ───────────────────────────────────────────────────────────
    job_id = str(uuid.uuid4())
    cache.set(
        f"essay_job:{job_id}",
        {"status": "pending", "drafts": [], "failed": []},
        timeout=3600,
    )

    draft_essays_batch.delay(
        job_id=job_id,
        profile_id=profile.id,
        prompts_list=prompts_list,
        structured_context=structured_context,
    )

    return Response({"job_id": job_id, "status": "pending"}, status=202)


@extend_schema(
    parameters=[OpenApiParameter(name="job_id", type=OpenApiTypes.STR, location=OpenApiParameter.PATH)],
    responses={200: dict, 404: dict}
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_essay_draft_status(request, job_id: str):
    result = cache.get(f"essay_job:{job_id}")
    if result is None:
        return Response({"error": "Job not found or expired."}, status=404)
    return Response(result, status=200)


@extend_schema(responses={200: dict})
@api_view(["GET"])
@permission_classes([AllowAny])
def scholarship_metadata(request):
    from scholarships.models import Tag, Level
    return Response({
        "tags": [
            {"value": c[0], "label": c[1]}
            for c in Tag._meta.get_field("name").choices
        ],
        "levels": [
            {"value": c[0], "label": c[1]}
            for c in Level._meta.get_field("level").choices
        ],
        "scholarship_types": [
            "Merit-based", "Need-based", "Research", "Athletic",
            "Community Service", "Field-specific", "Minority",
            "Women in STEM", "International Student", "Regional",
        ],
    })


# ── Context builders ──────────────────────────────────────────────────────────

def _build_profile_context(user, profile) -> str:
    """Hard profile facts — always the base."""
    return (
        f"Name: {profile.full_name or user.get_full_name() or 'Not provided'}\n"
        f"Field of Study: {profile.field_of_study or 'Not provided'}\n"
        f"Institution: {profile.institution or 'Not provided'}\n"
        f"Graduation Year: {profile.graduation_year or 'Not provided'}\n"
        f"Country: {profile.country or 'Not provided'}\n"
        f"GPA: {profile.gpa or 'Not provided'}"
        f"{f'/{profile.gpa_scale}' if profile.gpa_scale else ''}\n"
        f"Career Goals: {getattr(profile, 'career_goals', None) or 'Not provided'}\n"
    )


def _build_rich_scholarship_context(scholarship_id: int) -> str:
    """
    Tier 1 — build from a full saved Scholarship record.
    Uses all stored fields: description, eligibility, requirements, reward, deadline.
    """
    try:
        s = Scholarship.objects.get(id=scholarship_id)
    except Scholarship.DoesNotExist:
        return ""

    lines = ["\n--- Scholarship Details (verified, from your dashboard) ---"]

    if s.title:
        lines.append(f"Scholarship Name: {s.title}")
    if s.description:
        lines.append(f"About: {s.description}")
    if s.reward:
        lines.append(f"Award: {s.reward}")
    if s.eligibility:
        criteria = s.eligibility if isinstance(s.eligibility, list) else [s.eligibility]
        lines.append(f"Eligibility: {'; '.join(str(c) for c in criteria)}")
    if s.requirements:
        reqs = s.requirements if isinstance(s.requirements, list) else [s.requirements]
        lines.append(f"Requirements: {'; '.join(str(r) for r in reqs)}")
    if s.end_date:
        lines.append(f"Deadline: {s.end_date}")
    if s.tags:
        lines.append(f"Type: {', '.join(s.tags)}")
    if s.levels:
        lines.append(f"Academic Level: {', '.join(s.levels)}")

    lines.append("--- End Scholarship Details ---\n")
    return "\n".join(lines)


def _build_inline_context_block(ctx: dict) -> str:
    """
    Tier 2 — user filled the inline popup form.
    Clearly labelled as self-reported to reduce LLM hallucination risk.
    """
    lines = ["\n--- Scholarship Context (provided by applicant) ---"]
    if name := (ctx.get("name") or "").strip():
        lines.append(f"Scholarship Name: {name}")
    if audience := (ctx.get("audience") or "").strip():
        lines.append(f"Target Audience: {audience}")
    if values := (ctx.get("values") or "").strip():
        lines.append(f"What This Scholarship Values: {values}")
    lines.append("--- End Scholarship Context ---\n")
    return "\n".join(lines)


def _build_page_metadata_block(meta: dict) -> str:
    """
    Tier 3 — page title and URL scraped from the active tab.
    Minimum viable context: at least the LLM knows which scholarship page
    the user is on, even when they skipped everything else.
    """
    lines = ["\n--- Application Page (inferred from browser tab) ---"]
    if title := (meta.get("title") or "").strip():
        lines.append(f"Page Title: {title}")
    if url := (meta.get("url") or "").strip():
        lines.append(f"URL: {url}")
    lines.append(
        "Note: No scholarship details were saved. Use the page title as a "
        "hint about what scholarship this is for, but do not invent details.\n"
        "--- End Application Page ---\n"
    )
    return "\n".join(lines)

def unsubscribe_view(request, token):
    signer = Signer()
    try:
        user_id = signer.unsign(token)
    except BadSignature:
        return HttpResponseBadRequest("Invalid or tampered unsubscribe link.")
        
    user = get_object_or_404(User, id=user_id)
    user.receives_email_reminders = False
    user.save()
    
    return render(request, "emails/unsubscribed_success.html")
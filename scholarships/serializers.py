from rest_framework import serializers
from .models import Scholarship, ScholarshipScrapeEvent, Application, Bookmark, User

class ScholarshipSerializer(serializers.ModelSerializer):
    class Meta:
        model = Scholarship
        fields = ['title','start_date','end_date','tags','description','reward','active','link', 'eligibility']
        
class ApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Application
        fields = ['user', 'status', 'notes', 'scholarship', 'submitted_at']

class BookMarkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bookmark
        fields = ['user', 'scholarship', 'bookmarked_at']

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        field = ['is_admin', 'applied_scholarships', 'bookmarked_scholarships']

class UserDashBoardSerializer(serializers.Serializer):
    recent_applications = ApplicationSerializer(many=True)
    recent_bookmarks = BookMarkSerializer(many=True)
    applied_scholarships = ScholarshipSerializer(many=True)
    bookmarked_scholarships = ScholarshipSerializer(many=True)
    stats = serializers.DictField()

from rest_framework import serializers
from .models import Scholarship, Application, Bookmark, User, Profile, SiteConfig
from .models import Profile, Level, Tag

class SiteConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteConfig
        fields = '__all__'
        
class ScholarshipSerializer(serializers.ModelSerializer):
    is_bookmarked = serializers.SerializerMethodField()
    is_saved = serializers.SerializerMethodField()
    class Meta:
        model = Scholarship
        fields = ['id','title','start_date','end_date','tags','description','reward','active','link', 'eligibility', 'is_bookmarked']
    
    def get_is_bookmarked(self, obj):
        user = self.context['request'].user
        return Bookmark.objects.filter(user=user, scholarship=obj).exists()
    
    def get_is_saved(self, obj):
        user = self.context['request'].user
        return Application.objects.filter(user=user, scholarship=obj).exists() 

class ApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Application
        fields = ['user', 'status', 'notes', 'scholarship', 'submitted_at']

    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['user'] = user
        return super().create(validated_data)

class BookmarkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bookmark
        fields = ['user', 'scholarship', 'bookmarked_at']

    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['user'] = user
        return super().create(validated_data)

class UserSerializer(serializers.ModelSerializer):
    applied_scholarships = ScholarshipSerializer(many=True, read_only=True)
    bookmarked_scholarships = ScholarshipSerializer(many=True, read_only=True)
    class Meta:
        model = User
        fields = ['is_admin', 'applied_scholarships', 'bookmarked_scholarships']

class UserDashBoardSerializer(serializers.Serializer):
    recent_applications = ApplicationSerializer(many=True)
    recent_bookmarks = BookmarkSerializer(many=True)
    applied_scholarships = ScholarshipSerializer(many=True)
    bookmarked_scholarships = ScholarshipSerializer(many=True)
    stats = serializers.DictField()

class ApplicationStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Application
        fields = ['status']

class ProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model= Profile
        exclude = ['created_at', 'updated_at', 'user']

class LevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Level
        fields = ['id', 'level']

class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name']

class ProfileSerializer(serializers.ModelSerializer):
    # Nested ManyToMany fields
    level = LevelSerializer(many=True, read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    
    # For writable M2M (accept IDs)
    level_ids = serializers.PrimaryKeyRelatedField(
        queryset=Level.objects.all(),
        many=True,
        write_only=True,
        required=False
    )
    tag_ids = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True,
        write_only=True,
        required=False
    )

    # Convert text fields to lists for the frontend
    preferred_countries = serializers.SerializerMethodField()
    preferred_scholarship_types = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = [
            'id', 'user', 'full_name', 'date_of_birth', 'country', 'city',
            'field_of_study', 'institution', 'graduation_year', 'bio',
            'profile_picture', 'level', 'tags', 'level_ids', 'tag_ids',
            'preferred_countries', 'preferred_scholarship_types',
        ]
        read_only_fields = ['user']

    # Convert text field → list for frontend
    def get_preferred_countries(self, obj):
        if not obj.preferred_countries:
            return []
        return [c.strip() for c in obj.preferred_countries.split(",") if c.strip()]

    def get_preferred_scholarship_types(self, obj):
        if not obj.preferred_scholarship_types:
            return []
        return [t.strip() for t in obj.preferred_scholarship_types.split(",") if t.strip()]

    # Override create/update to handle lists
    def create(self, validated_data):
        level_ids = validated_data.pop("level_ids", [])
        tag_ids = validated_data.pop("tag_ids", [])
        profile = Profile.objects.create(**validated_data)
        profile.level.set(level_ids)
        profile.tags.set(tag_ids)
        return profile

    def update(self, instance, validated_data):
        level_ids = validated_data.pop("level_ids", None)
        tag_ids = validated_data.pop("tag_ids", None)

        # Handle text list fields
        preferred_countries = self.context['request'].data.get('preferred_countries', [])
        preferred_types = self.context['request'].data.get('preferred_scholarship_types', [])

        if isinstance(preferred_countries, list):
            instance.preferred_countries = ", ".join(preferred_countries)
        if isinstance(preferred_types, list):
            instance.preferred_scholarship_types = ", ".join(preferred_types)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()

        if level_ids is not None:
            instance.level.set(level_ids)
        if tag_ids is not None:
            instance.tags.set(tag_ids)

        return instance

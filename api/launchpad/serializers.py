import uuid

from django.db.models import Sum, Max, Prefetch, F, OuterRef, Subquery, IntegerField

from rest_framework import serializers

from db.user import User
from db.organization import UserOrganizationLink, Organization, LaunchpadClgUserLink, College
from db.task import KarmaActivityLog


class LaunchpadLeaderBoardSerializer(serializers.ModelSerializer):
    rank = serializers.SerializerMethodField()
    karma = serializers.IntegerField()
    actual_karma = serializers.IntegerField(source="wallet_user.karma", default=None)
    org = serializers.CharField()
    district_name = serializers.CharField()
    state = serializers.CharField()

    class Meta:
        model = User
        fields = ("rank", "full_name", "actual_karma", "karma", "org", "district_name", "state")

    def get_rank(self, obj):
        total_karma_subquery = KarmaActivityLog.objects.filter(
            user=OuterRef('id'),
            task__event='launchpad',
            appraiser_approved=True,
        ).values('user').annotate(
            total_karma=Sum('karma')
        ).values('total_karma')
        allowed_org_types = ["College", "School", "Company"]

        intro_task_completed_users = KarmaActivityLog.objects.filter(
            task__event='launchpad',
            appraiser_approved=True,
            task__hashtag='#lp24-introduction',
        ).values('user')
        
        users = User.objects.filter(
            karma_activity_log_user__task__event="launchpad",
            karma_activity_log_user__appraiser_approved=True,
            id__in=intro_task_completed_users
        ).prefetch_related(
            Prefetch(
                "user_organization_link_user",
                queryset=UserOrganizationLink.objects.filter(org__org_type__in=allowed_org_types),
            )
        ).filter(
            user_organization_link_user__id__in=UserOrganizationLink.objects.filter(
                org__org_type__in=allowed_org_types
            ).values("id")
        ).annotate(
            karma=Subquery(total_karma_subquery, output_field=IntegerField()),
            time_=Max("karma_activity_log_user__created_at"),
        ).order_by("-karma", "time_")
        
        # high complexity
        rank = 0
        for data in users:
            rank += 1
            if data.id == obj.id:
                break    
        
        return rank


class LaunchpadParticipantsSerializer(serializers.ModelSerializer):
    org = serializers.CharField()
    district_name = serializers.CharField()
    state = serializers.CharField()
    level = serializers.CharField()

    class Meta:
        model = User
        fields = ("full_name", "level", "org", "district_name", "state")


class CollegeDataSerializer(serializers.ModelSerializer):
    district_name = serializers.CharField()
    state = serializers.CharField()
    total_users = serializers.IntegerField()
    level1 = serializers.IntegerField()
    level2 = serializers.IntegerField()
    level3 = serializers.IntegerField()
    level4 = serializers.IntegerField()
    
    class Meta:
        model = Organization
        fields = (
            "title", 
            "district_name", 
            "state", 
            "total_users", 
            "level1", 
            "level2",
            "level3", 
            "level4"
        )


class AssignCollegeSerializer(serializers.ModelSerializer):

    class Meta:
        model = LaunchpadClgUserLink
        fields = []

    def create(self, validated_data):
        validated_data['id'] = uuid.uuid4()
        validated_data['user'] = self.context.get('user')
        validated_data['college'] = self.context.get('college_ids')
        validated_data['created_by'] = self.context.get('user')
        # instance = [LaunchpadClgUserLink(
        #     id=uuid.uuid4(),
        #     college=college_id,
        #     user=user,
        #     created_by=user
        # ) for college_id in college_ids]

        return LaunchpadClgUserLink.objects.create(**validated_data)

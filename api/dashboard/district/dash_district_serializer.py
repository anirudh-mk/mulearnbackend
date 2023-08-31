from datetime import timedelta

from django.db.models import Sum, F, Count, Q
from rest_framework import serializers

from db.organization import UserOrganizationLink, Organization, College
from db.task import TotalKarma, KarmaActivityLog, Level, UserLvlLink
from utils.types import OrganizationType, RoleType
from utils.utils import DateTimeUtils


class DistrictDetailsSerializer(serializers.ModelSerializer):
    district = serializers.CharField(source="org.district.name")
    zone = serializers.CharField(source="org.district.zone.name")
    rank = serializers.SerializerMethodField()
    district_lead = serializers.SerializerMethodField()
    karma = serializers.SerializerMethodField()
    total_members = serializers.SerializerMethodField()
    active_members = serializers.SerializerMethodField()

    class Meta:
        model = UserOrganizationLink
        fields = (
            "district",
            "zone",
            "rank",
            "district_lead",
            "karma",
            "total_members",
            "active_members"
        )

    def get_rank(self, obj):
        org_karma_dict = (
            UserOrganizationLink.objects.all()
            .values("org__district")
            .annotate(total_karma=Sum("user__total_karma_user__karma"))
        )

        rank_dict = {
            data["org__district"]: data["total_karma"]
            if data["total_karma"] is not None
            else 0
            for data in org_karma_dict
        }

        sorted_rank_dict = dict(
            sorted(rank_dict.items(), key=lambda x: x[1], reverse=True)
        )

        if obj.org.district.id in sorted_rank_dict:
            keys_list = list(sorted_rank_dict.keys())
            position = keys_list.index(obj.org.district.id)
            return position + 1

    def get_district_lead(self, obj):
        user_org_link = UserOrganizationLink.objects.filter(
            org__district=obj.org.district,
            user__user_role_link_user__role__title='District Campus Lead').first()
        return user_org_link.user.fullname if user_org_link else None

    def get_karma(self, obj):
        return UserOrganizationLink.objects.filter(
            org__district=obj.org.district
        ).aggregate(total_karma=Sum('user__total_karma_user__karma'))['total_karma']

    def get_total_members(self, obj):
        return UserOrganizationLink.objects.filter(
            org__district=obj.org.district
        ).count()

    def get_active_members(self, obj):
        today = DateTimeUtils.get_current_utc_time()
        start_date = today.replace(day=1)
        end_date = start_date.replace(
            day=1, month=start_date.month % 12 + 1
        ) - timedelta(days=1)

        return KarmaActivityLog.objects.filter(
            user__user_organization_link_user_id__org__district=obj.org.district,
            created_at__range=(start_date, end_date),
        ).count()


class DistrictTopThreeCampusSerializer(serializers.ModelSerializer):
    campus_code = serializers.CharField(source='code')
    rank = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = ["rank", "campus_code"]

    def get_rank(self, obj):
        keys_list = list(self.context.get("ranks").keys())
        position = keys_list.index(obj.id)
        return position + 1


class DistrictStudentLevelStatusSerializer(serializers.ModelSerializer):
    college_name = serializers.CharField(source='title')
    college_code = serializers.CharField(source='code')
    level = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = [
            "college_name",
            "college_code",
            "level"]

    def get_level(self, obj):
        return Level.objects.annotate(
            students_count=Count(
                'user_lvl_link_level',
                filter=Q(
                    user_lvl_link_level__user__user_organization_link_user_id=obj.user_organization_link_org_id
                ),
            )
        ).values('level_order', 'students_count')


class DistrictStudentDetailsSerializer(serializers.Serializer):
    user_id = serializers.CharField()
    fullname = serializers.SerializerMethodField()
    muid = serializers.ReadOnlyField(source="user.mu_id")
    karma = serializers.IntegerField()
    rank = serializers.SerializerMethodField()
    level = serializers.CharField()

    class Meta:
        fields = (
            "user_id"
            "fullname",
            "karma",
            "muid",
            "rank",
            "level",
        )

    def get_rank(self, obj):
        ranks = self.context.get("ranks")
        return ranks.get(obj.id, None)

    def get_fullname(self, obj):
        return obj.fullname


class DistrictCollegeDetailsSerializer(serializers.Serializer):
    id = serializers.CharField()
    title = serializers.CharField()
    code = serializers.CharField()
    level = serializers.CharField()
    lead = serializers.SerializerMethodField()
    lead_number = serializers.SerializerMethodField()

    class Meta:
        fields = (
            'id'
            'title',
            'level',
            'code',
            'lead',
            'lead_number'
        )

    def get_lead(self, obj):
        leads = self.context.get("leads")
        college_lead = [lead for lead in leads if lead.college == obj["id"]]
        return college_lead[0].fullname if college_lead else None

    def get_lead_number(self, obj):
        leads = self.context.get("leads")
        college_lead = [lead for lead in leads if lead.college == obj["id"]]
        return college_lead[0].mobile if college_lead else None

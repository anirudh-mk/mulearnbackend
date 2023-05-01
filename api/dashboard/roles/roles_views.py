from rest_framework.views import APIView

from utils.utils_views import CustomResponse
from rest_framework.response import Response
from user.models import Role

class HelloWorld(APIView):
    def get(self, request):
        return CustomResponse(response={'hey': "hello"}).get_success_response()

#TODO:
# all roles management or user role management?
# list existing roles
# create new role
# edit user role    
# delete user role
# get role of a specific user

ALL_FIELDS = {
    "id" : "id",
    "title" : "title",
    "description" : "description",
    "updated_by" : "updated_by",
    "updated_at" : "updated_at",
    "created_by": "created_by",
    "verified" : "verified",
    "created_at" : "created_at"
}

FIELD_NAMES, FIELD_VALUES = zip(*ALL_FIELDS.items())

FIELD_LENGTH = len(ALL_FIELDS)

# discord_id is not in models
DEFAULT_FIELDS = ["id", "title", "updated_at", "description", "updated_by"]

MAX_COLUMNS = 5

class RolesAPI(APIView):
    def get(self,request):
        # filter fields based on table name
        selected_columns = request.GET.get("fields","").split(",")
        
        roles = Role.objects.select_related("user")
        
        if (len(selected_columns) == MAX_COLUMNS and any(field not in ALL_FIELDS for field in selected_columns)):
            selected_columns = DEFAULT_FIELDS
        
        
        for field in selected_columns:
            selected_columns[selected_columns.index(field)] = ALL_FIELDS[field]
            
        roles = roles.values(*selected_columns)
        
        roles_dicts = [
            {
                selected_columns[i]: role[selected_columns[i]]
                if selected_columns[i] in role
                else None
                for i in range(MAX_COLUMNS)
            }
            for role in roles
        ]
                      
        return CustomResponse(
            general_message={"columns": FIELD_NAMES, "len_columns": FIELD_LENGTH},
            response=roles_dicts,
        ).get_success_response()
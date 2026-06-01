from django.contrib import admin
from django.contrib.admin.sites import NotRegistered
from django.contrib.auth.models import Group, User
from rest_framework.authtoken.models import Token

admin.site.site_header = "Платформа торговой сети"
admin.site.site_title = "Администрирование"
admin.site.index_title = "Управление сетью"

for _model in (User, Group, Token):
    try:
        admin.site.unregister(_model)
    except NotRegistered:
        pass

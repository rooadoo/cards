from django.urls import path
from django.conf.urls import url
from django.views.generic import RedirectView
from django.contrib import admin
from django.contrib.auth import views as django_auth_views
from . import views

urlpatterns = [
    path('table', views.index, name='index'),
    path('table/manage', views.manage),
    path('table/manage/collection/<int:pk>', views.collectionedit, name='table-manage-collection'),

    path('table/lobby', views.lobby, name='table-lobby'),
    path('table/lobby?endgame<int:num>', views.lobby, name='table-lobby'),
    path('table/register', views.register),

    path('table/game/<int:pk>', views.game, name='table-game'),
    path('table/game/<int:pk>/configure', views.configure_game, name="configure-game"),
    path('table/game/<int:gameid>/endgame', views.endgame, name="endgame"),

    url(r'^$', RedirectView.as_view(pattern_name='table-lobby', permanent=False)),  # Nginx should handle this
    path('admin/', admin.site.urls),
    path('login/', django_auth_views.LoginView.as_view(), name='login'),
]

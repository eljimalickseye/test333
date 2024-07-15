# core/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register_user, name='register'),
    path('login_user/', views.login_user, name='login_user'),
    path('logout/', views.logout_user, name='logout'),


    path('adfile/', views.adfile, name='adfile'),
    path('temporaire_drh/', views.temporaire_drh, name='temporaire_drh'),
    path('crbtfile/', views.crbtfile, name='crbtfile'),
    path('user_pretups/', views.user_pretups, name='user_pretups'),

    path('user-deleted/', views.user_deleted, name='user_deleted'),
    path('insert-user-deleted/', views.insert_user_deleted, name='insert_user_deleted'),
    path('supprimer-user-data/', views.supprimer_user_data, name='supprimer_user_data'),

    path('temporaire_drh/', views.temporaire_drh, name='temporaire_drh'),
    path('insert_admp/', views.insert_admp, name='insert_admp'),
    path('insert_tmp_drh/', views.insert_tmp_drh, name='insert_tmp_drh'),
    path('insert_crbt/', views.insert_crbt, name='insert_crbt'),
    path('insert_user_pretups/', views.insert_user_pretups, name='insert_user_pretups'),

    path('supprimer_tmp_data/', views.supprimer_tmp_data, name='supprimer_tmp_data'),
    path('supprimer_ad_data/', views.supprimer_ad_data, name='supprimer_ad_data'),
    path('supprimer_crbt_data/', views.supprimer_crbt_data, name='supprimer_crbt_data'),
    path('supprimer_user_pretups_data/', views.supprimer_user_pretups_data, name='supprimer_user_pretups_data'),

    path('export_gnoc/', views.export_gnoc, name='export_gnoc'),
    path('export_tmp/', views.export_tmp, name='export_tmp'),
    path('export_desc/', views.export_desc, name='export_desc'),

    path('export_user_pretups_fiable/', views.export_user_pretups_fiable, name='export_user_pretups_fiable'),


    
    path('export_all/', views.export_all, name='export_all'),

   
    path('update_from_adm/', views.update_from_adm, name='update_from_adm'),
    path('update_from_temporaireDRH/', views.update_from_temporaireDRH, name='update_from_temporaireDRH'),
    path('update_test_user_pretups/', views.update_test_user_pretups, name='update_test_user_pretups'),
]

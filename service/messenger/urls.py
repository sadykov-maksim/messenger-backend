from django.urls import path
from . import views
from .viewsets import GetMembersPublicKeysView, DistributeRoomKeysView, UploadPublicKeyView

urlpatterns = [
    path("", views.index, name="index"),
    path('room/<int:pk>/', views.room, name='room'),
    path("account/public-key/", UploadPublicKeyView.as_view()),
    path("rooms/distribute-keys/", DistributeRoomKeysView.as_view()),
    path("rooms/<int:room_id>/public-keys/", GetMembersPublicKeysView.as_view()),
]
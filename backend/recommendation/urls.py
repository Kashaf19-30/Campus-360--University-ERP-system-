from django.urls import path
from recommendation.views.profile_views import RecommendationProfileUpdateView
from recommendation.views.recommendation_views import RecommendationResultsView

urlpatterns = [
    path('profile/update/', RecommendationProfileUpdateView.as_view(), name='recommendation-profile-update'),
    path('results/', RecommendationResultsView.as_view(), name='recommendation-results'),
]

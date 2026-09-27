from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from recommendation.models import RecommendationProfile
from recommendation.serializers.profile_serializers import RecommendationProfileSerializer


class RecommendationProfileUpdateView(generics.UpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = RecommendationProfileSerializer

    def get_object(self):
        if self.request.user.user_type != 'applicant':
            return None
        profile, _ = RecommendationProfile.objects.get_or_create(user=self.request.user)
        return profile

    def update(self, request, *args, **kwargs):
        if request.user.user_type != 'applicant':
            return Response(
                {'error': 'Only applicants can use AI degree recommendations.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().update(request, *args, **kwargs)

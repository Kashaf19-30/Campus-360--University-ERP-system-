from rest_framework import status, generics
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from recommendation.models import RecommendationProfile, RecommendationResult
from recommendation.services.recommendation_engine import RecommendationEngine


class RecommendationResultsView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.user_type != 'applicant':
            return Response(
                {'error': 'Only applicants can use AI degree recommendations.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            profile = RecommendationProfile.objects.get(user=request.user)
        except RecommendationProfile.DoesNotExist:
            return Response(
                {'error': 'Complete the recommendation wizard first.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not profile.educational_background or not profile.marks.exists():
            return Response(
                {'error': 'Please submit your background and marks before requesting results.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        engine = RecommendationEngine(profile)
        recommendations = engine.get_recommendations()

        RecommendationResult.objects.filter(profile=profile).delete()
        for rec in recommendations:
            RecommendationResult.objects.create(
                profile=profile,
                program=rec['program'],
                match_score=rec['score'],
                reasons=rec['detailed_reasons'],
            )

        response_data = [{
            'program_name': rec['program'].program_name,
            'program_code': rec['program'].program_code,
            'department_name': rec['program'].department.department_name if rec['program'].department_id else '',
            'match_score': rec['score'],
            'summary': rec['summary'],
            'detailed_reasons': rec['detailed_reasons'],
            'top_strengths': rec['top_strengths'],
        } for rec in recommendations]

        return Response(response_data, status=status.HTTP_200_OK)

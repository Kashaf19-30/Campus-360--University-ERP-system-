from recommendation.models import TrendScore

def calculate_trend_score(background, program_id):
    try:
        trend = TrendScore.objects.get(background=background, degree_id=program_id)
        return trend.score / 10.0
    except TrendScore.DoesNotExist:
        return 0.0

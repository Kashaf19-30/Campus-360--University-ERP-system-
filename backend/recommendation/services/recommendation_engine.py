from academics.models import DegreeProgram
from recommendation.models import DegreeEligibility
from recommendation.services.program_weights import get_program_subject_weights
from .subject_analyzer import calculate_subject_strength
from .interest_analyzer import calculate_interest_match
from .goal_analyzer import calculate_goal_match
from .trend_analyzer import calculate_trend_score
from .explanation_generator import generate_reasons


class RecommendationEngine:
    def __init__(self, profile):
        self.profile = profile
        self.background = profile.educational_background
        self.marks = {mark.subject_name: mark.percentage() for mark in profile.marks.all()}
        self.interests = list(profile.interests.values_list('interest__name', flat=True))
        self.goals = list(profile.goals.values_list('goal__name', flat=True))
        self.has_interests = bool(self.interests)
        self.has_goals = bool(self.goals and 'Not Sure Yet' not in self.goals)

    def _get_scenario_weights(self):
        if self.has_interests and self.has_goals:
            return {'subjects': 0.45, 'interests': 0.35, 'goals': 0.15, 'trend': 0.05}
        if not self.has_interests and self.has_goals:
            return {'subjects': 0.80, 'interests': 0, 'goals': 0.15, 'trend': 0.05}
        if self.has_interests and not self.has_goals:
            return {'subjects': 0.60, 'interests': 0.35, 'goals': 0, 'trend': 0.05}
        return {'subjects': 0.95, 'interests': 0, 'goals': 0, 'trend': 0.05}

    def get_recommendations(self, limit=10):
        weights = self._get_scenario_weights()

        eligible_ids = DegreeEligibility.objects.filter(
            background=self.background,
        ).values_list('degree_id', flat=True)

        programs = DegreeProgram.objects.filter(
            program_id__in=eligible_ids,
            is_active=True,
            accepting_admissions=True,
            degree_level='BS',
        ).select_related('department')

        if not programs.exists():
            return []

        recommendations = []

        for program in programs:
            subject_weights = get_program_subject_weights(program)
            subject_score = calculate_subject_strength(self.marks, subject_weights)
            interest_score = calculate_interest_match(self.interests, program.program_name)
            goal_score = calculate_goal_match(self.goals, program.program_name)
            trend_score = calculate_trend_score(self.background, program.program_id)

            if self.has_interests and self.has_goals:
                if subject_score < 0.4:
                    subject_weight, interest_weight, goal_weight, trend_weight = 0.25, 0.45, 0.25, 0.05
                elif subject_score < 0.7:
                    subject_weight, interest_weight, goal_weight, trend_weight = 0.35, 0.40, 0.20, 0.05
                else:
                    subject_weight = weights['subjects']
                    interest_weight = weights['interests']
                    goal_weight = weights['goals']
                    trend_weight = weights['trend']
            else:
                subject_weight = weights['subjects']
                interest_weight = weights['interests']
                goal_weight = weights['goals']
                trend_weight = weights['trend']

            total_score = (
                subject_score * subject_weight
                + interest_score * interest_weight
                + goal_score * goal_weight
                + trend_score * trend_weight
            ) * 100

            reason_data = generate_reasons(
                degree_name=program.program_name,
                student_marks=self.marks,
                student_interests=self.interests,
                student_goals=self.goals,
                subject_weights=subject_weights,
                trend_score=trend_score,
                background=self.background,
                match_score=total_score,
            )

            recommendations.append({
                'program': program,
                'score': round(total_score, 2),
                'summary': reason_data['summary'],
                'detailed_reasons': reason_data['detailed_reasons'],
                'top_strengths': reason_data['top_strengths'],
            })

        recommendations.sort(key=lambda x: x['score'], reverse=True)
        return recommendations[:limit]

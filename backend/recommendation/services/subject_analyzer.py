def calculate_subject_strength(marks_percentage, subject_weights):
    score = 0.0
    total_weight = 0.0
    for subject, weight in subject_weights.items():
        total_weight += weight
        mark_percent = marks_percentage.get(subject, 0.0)
        strength = mark_percent / 100.0
        score += strength * weight
    return score / total_weight if total_weight > 0 else 0.0

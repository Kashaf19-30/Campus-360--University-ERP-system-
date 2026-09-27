GOAL_MAPPING = {
    "High Salary": ['computer', 'ai', 'data', 'software', 'engineering', 'business', 'medical'],
    "Work Abroad": ['computer', 'ai', 'engineering', 'medical', 'data'],
    "Government Job": ['education', 'psychology', 'sociology', 'international', 'statistics'],
    "Helping People": ['medical', 'psychology', 'education', 'biotechnology', 'dpt'],
    "Entrepreneurship": ['business', 'bba', 'commerce', 'accounting', 'economics'],
    "Research & Academia": ['science', 'statistics', 'mathematics', 'biotechnology', 'bioinformatics'],
    "Remote Work": ['computer', 'ai', 'data', 'software', 'it', 'cyber'],
    "Leadership & Management": ['business', 'bba', 'economics', 'commerce'],
    "Job Security": ['medical', 'engineering', 'education', 'accounting'],
}

def calculate_goal_match(student_goals, degree_name):
    if not student_goals:
        return 0.0
    degree_lower = degree_name.lower()
    match_count = 0
    for goal in student_goals:
        keywords = GOAL_MAPPING.get(goal, [])
        if any(kw in degree_lower for kw in keywords):
            match_count += 1
    return match_count / len(student_goals)

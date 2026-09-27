# recommendation/services/interest_analyzer.py

def calculate_interest_match(student_interests: list, degree_name: str) -> float:
    """Calculate how well student interests match a degree."""
    if not student_interests:
        return 0.0
    
    degree_keywords = degree_name.lower().split()
    match_count = 0
    
    for interest in student_interests:
        interest_lower = interest.lower()
        if any(keyword in interest_lower or interest_lower in keyword 
               for keyword in degree_keywords):
            match_count += 1
    
    return match_count / len(student_interests)
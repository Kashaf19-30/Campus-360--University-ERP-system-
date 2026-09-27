# recommendation/services/explanation_generator.py

def get_subject_emoji(subject: str) -> str:
    emoji_map = {
        "Mathematics": "📐", "Computer Science": "💻", "Physics": "⚛️",
        "Chemistry": "🧪", "Biology": "🧬", "English": "📖",
        "Urdu": "📝", "Statistics": "📊", "Economics": "📈",
        "Accounting": "💰", "Business Studies": "🏢", "Sociology": "👥",
        "Psychology": "🧠", "History": "🏛️", "Education": "🎓"
    }
    return emoji_map.get(subject, "📌")

def get_career_note(degree_name: str, goals: list) -> str:
    if "High Salary" in goals:
        if any(k in degree_name.lower() for k in ['computer', 'ai', 'data', 'software']):
            return "Graduates in this field command competitive starting salaries and have strong earning potential."
        elif "engineering" in degree_name.lower():
            return "Engineering graduates consistently rank among the highest-paid professionals globally."
        elif "mbbs" in degree_name.lower() or "medical" in degree_name.lower():
            return "Medical professionals are among the most respected and well-compensated specialists."
    
    if "Helping People" in goals:
        if any(k in degree_name.lower() for k in ['medical', 'psychology', 'education', 'dpt']):
            return "This degree places you directly in a helping profession where you can make a meaningful impact."
    
    if "Entrepreneurship" in goals:
        if any(k in degree_name.lower() for k in ['bba', 'commerce', 'accounting', 'economics']):
            return "This program develops the strategic, financial, and leadership skills essential for building your own venture."
    
    if "Remote Work" in goals:
        if any(k in degree_name.lower() for k in ['computer', 'ai', 'data', 'software', 'it']):
            return "Technology-focused degrees offer excellent pathways to location-independent, flexible careers."
    
    if "Research & Academia" in goals:
        if any(k in degree_name.lower() for k in ['science', 'statistics', 'mathematics', 'biotechnology']):
            return "This program provides a strong foundation for postgraduate research and academic pursuits."
    
    if "Government Job" in goals:
        return "This degree makes you eligible for various competitive examinations and public sector positions."
    
    return "This degree opens doors to diverse and rewarding career opportunities."

def generate_reasons(
    degree_name: str,
    student_marks: dict,
    student_interests: list,
    student_goals: list,
    subject_weights: dict,
    trend_score: float,
    background: str,
    match_score: float
) -> dict:
    """
    Generate a thorough, professional, and motivating explanation.
    Returns structured data with summary, detailed reasons, and top strengths.
    """
    
    relevant_subjects = list(subject_weights.keys())
    strong_subjects = []
    weak_subjects = []
    
    for subject in relevant_subjects:
        if subject in student_marks:
            score = student_marks[subject]
            if score >= 70:
                strong_subjects.append((subject, score))
            elif score < 50:
                weak_subjects.append((subject, score))
    
    strong_subjects.sort(key=lambda x: x[1], reverse=True)
    
    parts = []

    if strong_subjects:
        top_subject, top_score = strong_subjects[0]
        subject_emoji = get_subject_emoji(top_subject)
        
        if len(strong_subjects) >= 2:
            second_subject, second_score = strong_subjects[1]
            parts.append(
                f"📚 Academic Strengths Identified\n"
                f"Your performance in {subject_emoji} {top_subject} ({top_score}%) and "
                f"{second_subject} ({second_score}%) demonstrates strong foundational knowledge. "
                f"These subjects form the core of {degree_name}, and your aptitude suggests you "
                f"would be well-positioned to succeed in this program."
            )
        else:
            parts.append(
                f"📚 Academic Strength Identified\n"
                f"Your performance in {subject_emoji} {top_subject} ({top_score}%) demonstrates "
                f"strong foundational knowledge in a key area for {degree_name}. This suggests you "
                f"would be well-positioned to succeed in this program."
            )
    else:
        parts.append(
            f"📚 Academic Profile Assessment\n"
            f"While your marks in the core subjects for {degree_name} show room for growth, "
            f"your balanced profile demonstrates the versatility needed to succeed in this program. "
            f"We encourage you to consider your academic strengths when making your final decision."
        )

    if student_interests:
        interests_str = ", ".join(student_interests)
        parts.append(
            f"🎯 Interest Alignment\n"
            f"Your stated interest in {interests_str} aligns well with the curriculum and "
            f"career pathways offered by {degree_name}. This suggests you would find the "
            f"program engaging and professionally fulfilling."
        )

    if student_goals:
        goals_str = ", ".join(student_goals)
        career_note = get_career_note(degree_name, student_goals)
        parts.append(
            f"💼 Career Goal Alignment\n"
            f"Your career aspirations of {goals_str} are well-supported by {degree_name}. "
            f"{career_note}"
        )

    if trend_score >= 0.6:
        trend_phrase = "a highly popular" if trend_score >= 0.8 else "a common"
        parts.append(
            f"📈 Student Trends\n"
            f"{degree_name} is {trend_phrase} choice among students from {background} background, "
            f"indicating strong peer interest and well-established career pipelines for graduates."
        )

    if match_score >= 85:
        final_boost = (
            f"🏆 Strong Recommendation\n"
            f"With a match score of {match_score}%, {degree_name} aligns exceptionally well with "
            f"your academic profile, interests, and career goals. We strongly encourage you to "
            f"explore this program further and consider it as a top choice for your undergraduate studies."
        )
    elif match_score >= 65:
        final_boost = (
            f"📌 Good Fit\n"
            f"With a match score of {match_score}%, {degree_name} is a solid option that aligns "
            f"well with your profile. We recommend scheduling a conversation with the department "
            f"or attending an information session to learn more about this program."
        )
    elif match_score >= 40:
        final_boost = (
            f"📋 Consider This Option\n"
            f"With a match score of {match_score}%, {degree_name} could be a viable option. "
            f"Consider reviewing the program curriculum and speaking with current students to "
            f"determine if it aligns with your interests and goals."
        )
    else:
        final_boost = (
            f"ℹ️ Explore Further\n"
            f"With a match score of {match_score}%, {degree_name} may not be your strongest fit. "
            f"We recommend exploring the higher-ranked options on your list and considering what "
            f"career pathways and academic experiences excite you most."
        )
    parts.append(final_boost)

    return {
        "summary": f"Based on your academic profile, interests, and career goals, {degree_name} has been evaluated as a potential option for your undergraduate studies.",
        "detailed_reasons": parts,
        "top_strengths": [s[0] for s in strong_subjects[:2]]
    }

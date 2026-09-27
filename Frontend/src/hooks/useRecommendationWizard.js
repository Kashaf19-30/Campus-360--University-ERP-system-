import { useState, useCallback, useEffect } from 'react';
import { submitRecommendationProfile, fetchRecommendations } from '../services/recommendationService';
import { SUBJECT_MAP } from '../utils/recommendationConstants';

const STORAGE_KEY = 'campus360_recommendation_wizard';

const emptyForm = () => ({
  background: '',
  marks: {},
  interests: [],
  goals: [],
  isInterestsUnsure: false,
  isGoalsUnsure: false,
});

export function useRecommendationWizard(token) {
  const [currentStep, setCurrentStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [recommendations, setRecommendations] = useState(null);
  const [formData, setFormData] = useState(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) return { ...emptyForm(), ...JSON.parse(saved) };
    } catch { /* ignore */ }
    return emptyForm();
  });

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ ...formData, currentStep }));
    } catch { /* ignore */ }
  }, [formData, currentStep]);

  const { background, marks, interests, goals, isInterestsUnsure, isGoalsUnsure } = formData;

  const validateStep = useCallback((step) => {
    if (step === 1 && !background) {
      setError('Please select your intermediate background.');
      return false;
    }
    if (step === 2) {
      const subjects = SUBJECT_MAP[background] || [];
      const allFilled = subjects.every(s => marks[s] !== undefined && marks[s] !== '' && !Number.isNaN(Number(marks[s])));
      if (!allFilled) {
        setError('Please enter marks for all subjects.');
        return false;
      }
    }
    setError('');
    return true;
  }, [background, marks]);

  const handleSubmit = useCallback(async () => {
    if (!token) {
      setError('Please sign in again.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const payload = {
        educational_background: background,
        marks: Object.entries(marks).map(([subject_name, marks_obtained]) => ({
          subject_name,
          marks_obtained: parseFloat(marks_obtained),
          total_marks: 200,
        })),
        interest_names: isInterestsUnsure ? [] : interests,
        goal_names: isGoalsUnsure ? [] : goals,
      };
      await submitRecommendationProfile(payload, token);
      const results = await fetchRecommendations(token);
      setRecommendations(Array.isArray(results) ? results : []);
      setCurrentStep(5);
    } catch (err) {
      setError(
        err.response?.data?.error
        || err.response?.data?.detail
        || 'Unable to generate recommendations. Please try again.',
      );
    } finally {
      setLoading(false);
    }
  }, [token, background, marks, interests, goals, isInterestsUnsure, isGoalsUnsure]);

  const goToNextStep = useCallback(() => {
    if (!validateStep(currentStep)) return;
    if (currentStep === 4) {
      handleSubmit();
    } else {
      setCurrentStep(prev => prev + 1);
    }
  }, [currentStep, validateStep, handleSubmit]);

  const goToPreviousStep = useCallback(() => {
    setCurrentStep(prev => Math.max(1, prev - 1));
    setError('');
  }, []);

  const updateField = useCallback((field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    if (error) setError('');
  }, [error]);

  const clearAllData = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    setFormData(emptyForm());
    setCurrentStep(1);
    setRecommendations(null);
    setError('');
  }, []);

  return {
    currentStep,
    loading,
    error,
    recommendations,
    background,
    marks,
    interests,
    goals,
    isInterestsUnsure,
    isGoalsUnsure,
    updateField,
    goToNextStep,
    goToPreviousStep,
    clearAllData,
    setCurrentStep,
  };
}

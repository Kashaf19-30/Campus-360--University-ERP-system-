import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../../context/AuthContext';
import { useRecommendationWizard } from '../../../hooks/useRecommendationWizard';
import { WIZARD_STEPS } from '../../../utils/recommendationConstants';
import StepBackground from '../components/recommendation/StepBackground';
import StepMarks from '../components/recommendation/StepMarks';
import StepInterests from '../components/recommendation/StepInterests';
import StepGoals from '../components/recommendation/StepGoals';
import StepResults from '../components/recommendation/StepResults';

const APPLICANT_BASE = '/applicant';

const AiRecommendationPage = () => {
  const navigate = useNavigate();
  const { token } = useAuth();
  const wizard = useRecommendationWizard(token);

  const renderStep = () => {
    switch (wizard.currentStep) {
      case 1:
        return (
          <StepBackground
            value={wizard.background}
            onChange={(val) => wizard.updateField('background', val)}
          />
        );
      case 2:
        return (
          <StepMarks
            background={wizard.background}
            marks={wizard.marks}
            updateField={wizard.updateField}
          />
        );
      case 3:
        return (
          <StepInterests
            selected={wizard.interests}
            onChange={(val) => wizard.updateField('interests', val)}
            unsure={wizard.isInterestsUnsure}
            onUnsureChange={(val) => wizard.updateField('isInterestsUnsure', val)}
          />
        );
      case 4:
        return (
          <StepGoals
            selected={wizard.goals}
            onChange={(val) => wizard.updateField('goals', val)}
            notSure={wizard.isGoalsUnsure}
            onNotSureChange={(val) => wizard.updateField('isGoalsUnsure', val)}
          />
        );
      case 5:
        return (
          <StepResults
            recommendations={wizard.recommendations}
            onApply={() => navigate(`${APPLICANT_BASE}/application-list`)}
          />
        );
      default:
        return null;
    }
  };

  const progress = ((wizard.currentStep - 1) / (WIZARD_STEPS.length - 1)) * 100;

  return (
    <div className="page-container fade-in ai-rec-page">
      <div className="ai-rec-hero">
        <button type="button" className="ai-rec-back" onClick={() => navigate(`${APPLICANT_BASE}/application-list`)}>
          ← Back to applications
        </button>
        <div className="ai-rec-hero-content">
          <div className="ai-rec-hero-glow" aria-hidden="true" />
          <span className="ai-rec-hero-kicker">Campus 360 AI Counselor</span>
          <h1>Find your perfect degree</h1>
          <p>
            Smart matching based on your intermediate background, marks, interests, and career goals —
            aligned with programs open for admission at University of Sialkot.
          </p>
        </div>
        <div className="ai-rec-progress-track" aria-hidden="true">
          <div className="ai-rec-progress-fill" style={{ width: `${progress}%` }} />
        </div>
        <ol className="ai-rec-stepper">
          {WIZARD_STEPS.map(step => (
            <li
              key={step.id}
              className={`ai-rec-stepper-item${wizard.currentStep === step.id ? ' active' : ''}${wizard.currentStep > step.id ? ' done' : ''}`}
            >
              <span className="ai-rec-stepper-icon">{step.icon}</span>
              <span>{step.label}</span>
            </li>
          ))}
        </ol>
      </div>

      <div className="ai-rec-panel">
        {wizard.error && (
          <div className="ai-rec-error" role="alert">{wizard.error}</div>
        )}

        {wizard.loading ? (
          <div className="ai-rec-loading">
            <div className="ai-rec-spinner" />
            <p>Analyzing your profile and ranking programs…</p>
          </div>
        ) : (
          renderStep()
        )}

        {wizard.currentStep < 5 && !wizard.loading && (
          <div className="ai-rec-actions">
            {wizard.currentStep > 1 && (
              <button type="button" className="btn-secondary" onClick={wizard.goToPreviousStep}>
                Back
              </button>
            )}
            <button type="button" className="btn-ai-recommend" onClick={wizard.goToNextStep}>
              {wizard.currentStep === 4 ? 'Generate recommendations' : 'Continue'}
            </button>
          </div>
        )}

        {wizard.currentStep === 5 && !wizard.loading && (
          <div className="ai-rec-actions centered">
            <button type="button" className="btn-secondary" onClick={wizard.clearAllData}>
              Start over
            </button>
            <button type="button" className="btn-ai-recommend" onClick={() => navigate(`${APPLICANT_BASE}/application-list`)}>
              Back to admissions
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default AiRecommendationPage;

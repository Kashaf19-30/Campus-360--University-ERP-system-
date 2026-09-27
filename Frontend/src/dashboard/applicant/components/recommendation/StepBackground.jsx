import React from 'react';
import { BACKGROUND_CHOICES } from '../../../../utils/recommendationConstants';

const StepBackground = ({ value, onChange }) => (
  <div className="ai-rec-step">
    <div className="ai-rec-step-intro">
      <span className="ai-rec-step-badge">Step 1</span>
      <h3>What did you study in intermediate?</h3>
      <p>Select your FSc / ICS / ICom / FA group so we can match eligible BS programs.</p>
    </div>
    <div className="ai-rec-card-grid">
      {BACKGROUND_CHOICES.map(bg => (
        <button
          key={bg}
          type="button"
          className={`ai-rec-select-card${value === bg ? ' selected' : ''}`}
          onClick={() => onChange(bg)}
        >
          <span className="ai-rec-select-card-title">{bg}</span>
          {value === bg && <span className="ai-rec-select-check">✓</span>}
        </button>
      ))}
    </div>
  </div>
);

export default StepBackground;

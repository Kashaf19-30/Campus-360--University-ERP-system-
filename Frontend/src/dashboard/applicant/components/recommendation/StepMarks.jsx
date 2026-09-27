import React from 'react';
import { SUBJECT_MAP } from '../../../../utils/recommendationConstants';

const StepMarks = ({ background, marks, updateField }) => {
  const subjects = SUBJECT_MAP[background] || [];

  if (!background) {
    return (
      <div className="ai-rec-empty-hint">
        Select your background in the previous step first.
      </div>
    );
  }

  return (
    <div className="ai-rec-step">
      <div className="ai-rec-step-intro">
        <span className="ai-rec-step-badge">Step 2</span>
        <h3>Enter your intermediate marks</h3>
        <p>Total marks per subject out of 200 (Part-I + Part-II + Practical combined).</p>
      </div>
      <div className="ai-rec-info-banner">
        <strong>Tip:</strong> Accurate marks improve match quality. Use your official result numbers.
      </div>
      <div className="ai-rec-marks-grid">
        {subjects.map(subject => (
          <label key={subject} className="ai-rec-mark-field">
            <span>{subject}</span>
            <div className="ai-rec-mark-input-wrap">
              <input
                type="number"
                min="0"
                max="200"
                placeholder="e.g. 175"
                value={marks[subject] ?? ''}
                onChange={(e) => updateField('marks', { ...marks, [subject]: e.target.value })}
              />
              <em>/ 200</em>
            </div>
          </label>
        ))}
      </div>
    </div>
  );
};

export default StepMarks;

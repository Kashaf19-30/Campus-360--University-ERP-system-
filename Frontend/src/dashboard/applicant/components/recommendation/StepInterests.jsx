import React from 'react';
import { INTERESTS_LIST } from '../../../../utils/recommendationConstants';

const StepInterests = ({ selected, onChange, unsure, onUnsureChange }) => {
  const toggle = (interest) => {
    if (unsure) return;
    let next = [...selected];
    if (next.includes(interest)) {
      next = next.filter(i => i !== interest);
    } else {
      if (next.length >= 3) return;
      next.push(interest);
    }
    onChange(next);
  };

  return (
    <div className="ai-rec-step">
      <div className="ai-rec-step-intro">
        <span className="ai-rec-step-badge">Step 3</span>
        <h3>What excites you?</h3>
        <p>Pick up to 3 interests — or let AI focus on your academic strengths.</p>
      </div>
      <label className="ai-rec-unsure-toggle">
        <input
          type="checkbox"
          checked={unsure}
          onChange={() => {
            if (selected.length > 0 && !unsure && !window.confirm('This will clear your selected interests.')) return;
            if (!unsure) onChange([]);
            onUnsureChange(!unsure);
          }}
        />
        <span>I'm not sure yet — recommend based on my marks</span>
      </label>
      <div className="ai-rec-chip-grid">
        {INTERESTS_LIST.map(interest => {
          const active = selected.includes(interest);
          return (
            <button
              key={interest}
              type="button"
              className={`ai-rec-chip${active ? ' active' : ''}${unsure ? ' disabled' : ''}`}
              onClick={() => toggle(interest)}
              disabled={unsure}
            >
              {interest}
            </button>
          );
        })}
      </div>
    </div>
  );
};

export default StepInterests;

import React from 'react';
import { GOALS_LIST } from '../../../../utils/recommendationConstants';

const StepGoals = ({ selected, onChange, notSure, onNotSureChange }) => {
  const toggle = (goal) => {
    if (notSure) return;
    let next = [...selected];
    if (next.includes(goal)) {
      next = next.filter(g => g !== goal);
    } else {
      if (next.length >= 2) return;
      next.push(goal);
    }
    onChange(next);
  };

  return (
    <div className="ai-rec-step">
      <div className="ai-rec-step-intro">
        <span className="ai-rec-step-badge">Step 4</span>
        <h3>Where do you want to go?</h3>
        <p>Choose up to 2 career goals to personalize your top program matches.</p>
      </div>
      <label className="ai-rec-unsure-toggle">
        <input
          type="checkbox"
          checked={notSure}
          onChange={() => {
            if (selected.length > 0 && !notSure && !window.confirm('This will clear your selected goals.')) return;
            if (!notSure) onChange([]);
            onNotSureChange(!notSure);
          }}
        />
        <span>Not sure yet — skip career goals</span>
      </label>
      <div className="ai-rec-chip-grid">
        {GOALS_LIST.map(goal => {
          const active = selected.includes(goal);
          return (
            <button
              key={goal}
              type="button"
              className={`ai-rec-chip${active ? ' active' : ''}${notSure ? ' disabled' : ''}`}
              onClick={() => toggle(goal)}
              disabled={notSure}
            >
              {goal}
            </button>
          );
        })}
      </div>
    </div>
  );
};

export default StepGoals;

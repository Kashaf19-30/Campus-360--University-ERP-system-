import React from 'react';
import { renderRecommendationParagraph } from '../../../../utils/formatRecommendationText';

const StepResults = ({ recommendations, onApply }) => {
  if (!recommendations?.length) {
    return (
      <div className="ai-rec-step ai-rec-empty-results">
        <div className="ai-rec-empty-icon">🔍</div>
        <h3>No matches found</h3>
        <p>Try different interests or double-check your marks and background selection.</p>
      </div>
    );
  }

  return (
    <div className="ai-rec-step">
      <div className="ai-rec-step-intro">
        <span className="ai-rec-step-badge">Your matches</span>
        <h3>Recommended BS programs</h3>
        <p>Ranked by academic fit, interests, goals, and admission trends at University of Sialkot.</p>
      </div>
      <div className="ai-rec-results-list">
        {recommendations.map((rec, index) => (
          <article
            key={`${rec.program_code}-${index}`}
            className={`ai-rec-result-card${index === 0 ? ' top-pick' : ''}`}
          >
            <div className="ai-rec-result-header">
              <div>
                {index === 0 && <span className="ai-rec-top-badge">Top match</span>}
                <h4>{rec.program_name}</h4>
                <p className="ai-rec-result-meta">
                  {rec.program_code}
                  {rec.department_name ? ` · ${rec.department_name}` : ''}
                </p>
              </div>
              <div className="ai-rec-score-ring">
                <strong>{Number(rec.match_score).toFixed(0)}%</strong>
                <span>match</span>
              </div>
            </div>
            <p className="ai-rec-result-summary">{renderRecommendationParagraph(rec.summary)}</p>
            {rec.detailed_reasons?.length > 0 && (
              <div className="ai-rec-reasons">
                {rec.detailed_reasons.map((paragraph, i) => (
                  <p key={i}>{renderRecommendationParagraph(paragraph)}</p>
                ))}
              </div>
            )}
            {rec.top_strengths?.length > 0 && (
              <div className="ai-rec-strengths">
                {rec.top_strengths.map(s => (
                  <span key={s} className="ai-rec-strength-pill">{s}</span>
                ))}
              </div>
            )}
            {index === 0 && onApply && (
              <button type="button" className="btn-ai-recommend ai-rec-apply-btn" onClick={onApply}>
                Start admission with this direction →
              </button>
            )}
          </article>
        ))}
      </div>
    </div>
  );
};

export default StepResults;

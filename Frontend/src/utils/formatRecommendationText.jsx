import React from 'react';

/** Render recommendation copy: first line bold, remaining lines normal. Strips legacy ** markers. */
export function renderRecommendationParagraph(text) {
  if (!text) return null;
  const cleaned = String(text).replace(/\*\*/g, '');
  const [title, ...rest] = cleaned.split('\n');
  const body = rest.join('\n').trim();
  return (
    <>
      {title ? <strong>{title}</strong> : null}
      {body ? (
        <>
          {title ? <br /> : null}
          {body}
        </>
      ) : null}
    </>
  );
}

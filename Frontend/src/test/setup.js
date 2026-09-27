import '@testing-library/jest-dom/vitest';
import React from 'react';

globalThis.React = React;

class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}

global.ResizeObserver = ResizeObserverStub;

beforeEach(() => {
  localStorage.clear();
  sessionStorage.clear();
});

import createCache from '@emotion/cache';
import { CacheProvider } from '@emotion/react';
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './src/App';

const rootElement = document.getElementById('root');
if (!rootElement) {
  throw new Error('Root element not found');
}

const nonceMeta = document.querySelector('meta[name="csp-nonce"]');
const nonce = nonceMeta?.getAttribute('content') ?? undefined;
const emotionCache = createCache({ key: 'mui', nonce });

ReactDOM.createRoot(rootElement).render(
  <CacheProvider value={emotionCache}>
    <App />
  </CacheProvider>,
);

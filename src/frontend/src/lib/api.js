const BASE_URL = import.meta.env?.VITE_API_URL || 'https://fabguard-backend.onrender.com';

async function fetchAPI(endpoint, options = {}) {
  const res = await fetch(`${BASE_URL}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });
  if (!res.ok) {
    throw new Error(`API Error: ${res.statusText}`);
  }
  return res.json();
}

export const api = {
  getLots: () => fetchAPI('/lots'),
  ingestLot: (data) => fetchAPI('/lots/ingest', { method: 'POST', body: JSON.stringify(data) }),
  getPredictRisk: () => fetchAPI('/predict-risk'),
  getValidationMetrics: () => fetchAPI('/validate'),
  getDefects: (lotId, limit = 1500) => fetchAPI(`/defects/${lotId}?limit=${limit}`),
  getRootCause: (lotId, tier = 'tier2') => fetchAPI(`/rootcause/${lotId}?tier=${tier}`),
  getRecommendations: (lotId) => fetchAPI(`/recommend?lot_id=${lotId}`),
  getChatHistory: (lotId) => fetchAPI(`/chat/history/${lotId}`),
  clearChatHistory: (lotId) => fetchAPI(`/chat/history/${lotId}`, { method: 'DELETE' }),
  getChatSessions: () => fetchAPI('/chat/sessions'),
  sendChat: (lotId, message, conversationHistory = []) =>
    fetchAPI('/chat', {
      method: 'POST',
      body: JSON.stringify({
        lot_id: lotId,
        message,
        question: message,
        conversation_history: conversationHistory,
      }),
    }),
};

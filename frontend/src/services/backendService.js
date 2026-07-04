import apiClient from './api';

export const checkBackendHealth = async () => {
  const response = await apiClient.get('/health');
  return response.data;
};

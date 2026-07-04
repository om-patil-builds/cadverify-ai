import apiClient from './api';

export const checkBackendHealth = async () => {
  const response = await apiClient.get('/health');
  return response.data;
};

export const fetchUploads = async () => {
  const response = await apiClient.get('/uploads');
  return response.data;
};

export const uploadDrawingFiles = async ({ pdfFile, dxfFile, onUploadProgress }) => {
  const formData = new FormData();
  formData.append('pdf_file', pdfFile);
  formData.append('dxf_file', dxfFile);

  const response = await apiClient.post('/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    onUploadProgress: (event) => {
      if (onUploadProgress) {
        const percent = Math.round((event.loaded * 100) / (event.total || 1));
        onUploadProgress(percent);
      }
    },
  });

  return response.data;
};

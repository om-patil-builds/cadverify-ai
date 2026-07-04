import apiClient from './api';

export const checkBackendHealth = async () => {
  const response = await apiClient.get('/health');
  return response.data;
};

export const fetchUploads = async () => {
  const response = await apiClient.get('/uploads');
  return response.data;
};
export const fetchUploadById = async (uploadId) => {
  const response = await apiClient.get(`/uploads/${uploadId}`);
  return response.data;
};

export const deleteUpload = async (uploadId) => {
  const response = await apiClient.delete(`/uploads/${uploadId}`);
  return response;
};

const downloadBlob = async (url, fileName) => {
  const response = await apiClient.get(url, { responseType: 'blob' });
  const blobUrl = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement('a');
  link.href = blobUrl;
  link.setAttribute('download', fileName);
  document.body.appendChild(link);
  link.click();
  link.parentNode.removeChild(link);
  window.URL.revokeObjectURL(blobUrl);
};

export const downloadUploadPdf = async (uploadId, fileName) => {
  return downloadBlob(`/uploads/${uploadId}/download/pdf`, fileName);
};

export const downloadUploadDxf = async (uploadId, fileName) => {
  return downloadBlob(`/uploads/${uploadId}/download/dxf`, fileName);
};

export const parseUploadDxf = async (uploadId) => {
  const response = await apiClient.get(`/uploads/${uploadId}/parse`);
  return response.data;
};

export const parseUploadPdf = async (uploadId) => {
  const response = await apiClient.get(`/uploads/${uploadId}/parse-pdf`);
  return response.data;
};

export const fetchParsedDxfEntities = async (uploadId) => {
  const response = await apiClient.get(`/uploads/${uploadId}/parsed-entities`);
  return response.data;
};

export const fetchParsedPdf = async (uploadId) => {
  const response = await apiClient.get(`/uploads/${uploadId}/parsed-pdf`);
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

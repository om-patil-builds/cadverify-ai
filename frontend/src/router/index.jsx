import { Navigate, Route, Routes } from 'react-router-dom';
import Layout from '../components/layout/Layout';
import DashboardPage from '../pages/Dashboard/DashboardPage';
import ComparePage from '../pages/Compare/ComparePage';
import UploadDetailsPage from '../pages/Compare/UploadDetailsPage';
import ReportsPage from '../pages/Reports/ReportsPage';

const AppRouter = () => {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/compare" element={<ComparePage />} />
        <Route path="/compare/:uploadId" element={<UploadDetailsPage />} />
        <Route path="/reports" element={<ReportsPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
};

export default AppRouter;

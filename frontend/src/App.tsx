import { lazy, Suspense } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { DashboardLayout } from './layouts/DashboardLayout';

const Dashboard = lazy(() => import('./pages/Dashboard').then((module) => ({ default: module.Dashboard })));
const Upload = lazy(() => import('./pages/Upload').then((module) => ({ default: module.Upload })));
const Search = lazy(() => import('./pages/Search').then((module) => ({ default: module.Search })));
const Jobs = lazy(() => import('./pages/Jobs').then((module) => ({ default: module.Jobs })));
const JobDetails = lazy(() => import('./pages/JobDetails').then((module) => ({ default: module.JobDetails })));
const CandidateDetails = lazy(() => import('./pages/CandidateDetails').then((module) => ({ default: module.CandidateDetails })));
const RelationshipExplorer = lazy(() => import('./pages/RelationshipExplorer').then((module) => ({ default: module.RelationshipExplorer })));
const AISummary = lazy(() => import('./pages/AISummary').then((module) => ({ default: module.AISummary })));
const Settings = lazy(() => import('./pages/Settings').then((module) => ({ default: module.Settings })));
const GmailImport = lazy(() => import('./pages/GmailImport').then((module) => ({ default: module.GmailImport })));

function App() {
  return (
    <Router>
      <DashboardLayout>
        <Suspense
          fallback={(
            <div className="min-h-[40vh] space-y-4 p-6" role="status" aria-label="Loading page">
              <div className="h-8 w-1/3 animate-shimmer rounded-lg" />
              <div className="h-32 animate-shimmer rounded-2xl" />
              <div className="h-48 animate-shimmer rounded-2xl" />
            </div>
          )}
        >
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/upload" element={<Upload />} />
            <Route path="/search" element={<Search />} />
            <Route path="/jobs" element={<Jobs />} />
            <Route path="/jobs/:jobId" element={<JobDetails />} />
            <Route path="/candidate/:id" element={<CandidateDetails />} />
            <Route path="/graph" element={<RelationshipExplorer />} />
            <Route path="/ai-summary" element={<AISummary />} />
            <Route path="/gmail-import" element={<GmailImport />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </Suspense>
      </DashboardLayout>
    </Router>
  );
}

export default App;

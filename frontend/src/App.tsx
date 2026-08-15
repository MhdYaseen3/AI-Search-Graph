import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { DashboardLayout } from './layouts/DashboardLayout';
import { Dashboard } from './pages/Dashboard';
import { Upload } from './pages/Upload';
import { Search } from './pages/Search';
import { Jobs } from './pages/Jobs';
import { CandidateDetails } from './pages/CandidateDetails';
import { RelationshipExplorer } from './pages/RelationshipExplorer';
import { AISummary } from './pages/AISummary';
import { Settings } from './pages/Settings';

function App() {
  return (
    <Router>
      <DashboardLayout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/upload" element={<Upload />} />
          <Route path="/search" element={<Search />} />
          <Route path="/jobs" element={<Jobs />} />
          <Route path="/candidate/:id" element={<CandidateDetails />} />
          <Route path="/graph" element={<RelationshipExplorer />} />
          <Route path="/ai-summary" element={<AISummary />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </DashboardLayout>
    </Router>
  );
}

export default App;

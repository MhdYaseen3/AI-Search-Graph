import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { 
  Users, 
  GitFork, 
  Search, 
  UploadCloud, 
  ChevronRight, 
  TrendingUp, 
  Zap, 
  Award,
  BookOpen
} from 'lucide-react';
import { resumeService } from '../services/api';
import type { Candidate } from '../types';

export const Dashboard: React.FC = () => {
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const data = await resumeService.searchCandidates('');
        setCandidates(data);
      } catch (err) {
        console.error('Failed to load dashboard statistics', err);
      } finally {
        setLoading(false);
      }
    };
    fetchStats();
  }, []);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      navigate(`/search?q=${encodeURIComponent(searchQuery)}`);
    } else {
      navigate('/search');
    }
  };

  // Compute stats
  const totalResumes = candidates.length;
  const averageMatchScore = totalResumes > 0 
    ? Math.round(candidates.reduce((sum, c) => sum + c.matchScore, 0) / totalResumes) 
    : 0;
  const totalRelationships = candidates.reduce((sum, c) => sum + c.relationshipCount, 0);

  // Hardcode some top aggregated skills for visualization
  const skillsCountMap: Record<string, number> = {};
  candidates.forEach(c => {
    c.skills.forEach(s => {
      skillsCountMap[s] = (skillsCountMap[s] || 0) + 1;
    });
  });
  
  const skillChartData = Object.entries(skillsCountMap)
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 5);

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      
      {/* HERO SECTION WITH SEARCH BAR */}
      <section className="relative overflow-hidden rounded-3xl border border-dark-border bg-gradient-to-r from-dark-card via-slate-900 to-brand-950/20 p-8 md:p-10 glow-purple">
        <div className="absolute top-0 right-0 w-80 h-80 bg-brand-500/10 rounded-full blur-[80px] pointer-events-none" />
        <div className="max-w-2xl space-y-4">
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-brand-500/10 text-xs font-semibold text-brand-500">
            <Zap size={12} className="fill-brand-500" />
            AI-Powered Talent Graph Mapping
          </span>
          <h2 className="text-2xl md:text-4xl font-extrabold text-white tracking-tight leading-tight">
            Map, search, and analyze candidates with semantic graphs.
          </h2>
          <p className="text-sm md:text-base text-slate-400">
            Search beyond keywords. Our system extracts skill associations, employment histories, and academic timelines directly from resumes to build an interactive knowledge graph.
          </p>

          <form onSubmit={handleSearchSubmit} className="pt-2 flex items-center gap-2 max-w-lg">
            <div className="relative flex-1">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500" size={18} />
              <input
                type="text"
                placeholder="Search skills, roles, or names (e.g. PyTorch, React, DevOps)..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-slate-950 border border-dark-border focus:border-brand-500 rounded-xl py-3 pl-12 pr-4 text-sm text-slate-100 placeholder-slate-500 outline-none transition-colors"
              />
            </div>
            <button
              type="submit"
              className="bg-brand-600 hover:bg-brand-700 text-white font-semibold text-sm px-6 py-3 rounded-xl shadow-lg transition-all duration-200"
            >
              Analyze
            </button>
          </form>
        </div>
      </section>

      {/* METRIC STATS PANEL */}
      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <div className="glass-panel rounded-2xl p-6 flex items-center justify-between">
          <div className="space-y-1">
            <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">Total Resumes</span>
            <h3 className="text-3xl font-extrabold text-white">{loading ? '...' : totalResumes}</h3>
            <span className="text-[10px] text-slate-400 block">Parsed successfully</span>
          </div>
          <div className="w-12 h-12 rounded-xl bg-indigo-500/10 flex items-center justify-center text-indigo-400">
            <Users size={22} />
          </div>
        </div>

        <div className="glass-panel rounded-2xl p-6 flex items-center justify-between">
          <div className="space-y-1">
            <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">Graph Relationships</span>
            <h3 className="text-3xl font-extrabold text-white">{loading ? '...' : totalRelationships}</h3>
            <span className="text-[10px] text-slate-400 block">Nodes & Edge links</span>
          </div>
          <div className="w-12 h-12 rounded-xl bg-brand-500/10 flex items-center justify-center text-brand-500">
            <GitFork size={22} />
          </div>
        </div>

        <div className="glass-panel rounded-2xl p-6 flex items-center justify-between">
          <div className="space-y-1">
            <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">Avg. Match Score</span>
            <h3 className="text-3xl font-extrabold text-white">{loading ? '...' : `${averageMatchScore}%`}</h3>
            <span className="text-[10px] text-emerald-400 flex items-center gap-1">
              <TrendingUp size={10} /> +1.2% this week
            </span>
          </div>
          <div className="w-12 h-12 rounded-xl bg-emerald-500/10 flex items-center justify-center text-emerald-400">
            <Award size={22} />
          </div>
        </div>

        <div className="glass-panel rounded-2xl p-6 flex items-center justify-between">
          <div className="space-y-1">
            <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">Processing Queue</span>
            <h3 className="text-3xl font-extrabold text-white">Idle</h3>
            <span className="text-[10px] text-slate-400 block">All systems active</span>
          </div>
          <div className="w-12 h-12 rounded-xl bg-amber-500/10 flex items-center justify-center text-amber-400">
            <BookOpen size={22} />
          </div>
        </div>
      </section>

      {/* DETAILED INSIGHTS & RECENT VISUALIZATIONS */}
      <section className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* SKILLS DISTRIBUTION CHART PANEL */}
        <div className="glass-panel rounded-2xl p-6 lg:col-span-1 flex flex-col justify-between">
          <div className="space-y-1.5 pb-4">
            <h3 className="text-sm font-bold text-white uppercase tracking-wider">Top Talent Skills</h3>
            <p className="text-xs text-slate-400">Aggregated database skill distribution</p>
          </div>

          <div className="space-y-4 flex-1 flex flex-col justify-center">
            {loading ? (
              <div className="space-y-3">
                <div className="h-6 rounded bg-slate-800 animate-pulse" />
                <div className="h-6 rounded bg-slate-800 animate-pulse" />
                <div className="h-6 rounded bg-slate-800 animate-pulse" />
              </div>
            ) : skillChartData.length > 0 ? (
              skillChartData.map((skill, index) => {
                const maxVal = Math.max(...skillChartData.map(s => s.count));
                const percent = maxVal > 0 ? (skill.count / maxVal) * 100 : 0;
                
                return (
                  <div key={skill.name} className="space-y-1">
                    <div className="flex justify-between text-xs font-semibold">
                      <span className="text-slate-300">{skill.name}</span>
                      <span className="text-brand-400">{skill.count} match{skill.count > 1 ? 'es' : ''}</span>
                    </div>
                    <div className="w-full bg-slate-900 h-2.5 rounded-full overflow-hidden border border-dark-border">
                      <div 
                        className={`h-full rounded-full bg-gradient-to-r ${
                          index === 0 ? 'from-brand-600 to-indigo-500' :
                          index === 1 ? 'from-indigo-500 to-blue-500' :
                          'from-blue-500 to-cyan-500'
                        }`}
                        style={{ width: `${percent}%` }}
                      />
                    </div>
                  </div>
                );
              })
            ) : (
              <p className="text-xs text-slate-500 italic">No skill distributions map compiled yet.</p>
            )}
          </div>

          <div className="border-t border-dark-border/40 pt-4 mt-4 text-center">
            <Link to="/search" className="text-xs text-brand-500 hover:text-brand-400 font-semibold inline-flex items-center gap-1">
              Analyze talent pool <ChevronRight size={14} />
            </Link>
          </div>
        </div>

        {/* RECENT UPLOADS & GRAPH ACTIVITY */}
        <div className="glass-panel rounded-2xl p-6 lg:col-span-2 flex flex-col justify-between">
          <div className="flex items-center justify-between pb-4">
            <div className="space-y-0.5">
              <h3 className="text-sm font-bold text-white uppercase tracking-wider">Recently Added Candidates</h3>
              <p className="text-xs text-slate-400">Latest parsed resumes and system integrations</p>
            </div>
            <Link 
              to="/upload" 
              className="text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 px-3 py-1.5 rounded-lg border border-dark-border flex items-center gap-1.5 transition-colors"
            >
              <UploadCloud size={14} />
              <span>Import</span>
            </Link>
          </div>

          <div className="flex-1 overflow-x-auto">
            {loading ? (
              <div className="space-y-4 py-4">
                <div className="h-10 rounded bg-slate-800/40 animate-pulse" />
                <div className="h-10 rounded bg-slate-800/40 animate-pulse" />
              </div>
            ) : candidates.length > 0 ? (
              <table className="w-full min-w-[500px]">
                <thead>
                  <tr className="border-b border-dark-border/60 text-[10px] text-slate-500 uppercase tracking-wider text-left">
                    <th className="pb-3">Candidate</th>
                    <th className="pb-3">Current Role</th>
                    <th className="pb-3 text-center">Match</th>
                    <th className="pb-3 text-center">Rel. Nodes</th>
                    <th className="pb-3 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-dark-border/40 text-xs">
                  {candidates.slice(0, 3).map((candidate) => (
                    <tr key={candidate.id} className="hover:bg-slate-800/20 transition-colors">
                      <td className="py-3.5 font-medium text-white flex items-center gap-2">
                        <div className="w-7 h-7 rounded-lg bg-brand-600/10 border border-brand-500/20 text-brand-500 font-bold flex items-center justify-center text-[10px]">
                          {candidate.name.split(' ').map(n=>n[0]).join('')}
                        </div>
                        <div>
                          <span className="block">{candidate.name}</span>
                          <span className="text-[10px] text-slate-500 font-normal">{candidate.location}</span>
                        </div>
                      </td>
                      <td className="py-3.5 text-slate-300">
                        <span className="block font-semibold">{candidate.currentRole}</span>
                        <span className="text-[10px] text-slate-500">{candidate.currentCompany}</span>
                      </td>
                      <td className="py-3.5 text-center">
                        <span className={`inline-block px-2 py-0.5 rounded-full font-semibold text-[10px] ${
                          candidate.matchScore >= 90 ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                          candidate.matchScore >= 80 ? 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/20' :
                          'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                        }`}>
                          {candidate.matchScore}%
                        </span>
                      </td>
                      <td className="py-3.5 text-center text-slate-400">
                        {candidate.relationshipCount} edges
                      </td>
                      <td className="py-3.5 text-right">
                        <Link 
                          to={`/candidate/${candidate.id}`}
                          className="p-1 text-slate-400 hover:text-white hover:bg-slate-800/50 rounded-lg inline-flex"
                        >
                          <ChevronRight size={16} />
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="text-center py-8 text-slate-500 italic">No candidates parsed in database yet.</div>
            )}
          </div>
        </div>
      </section>

      {/* SYSTEM QUICKLINKS HUB */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="glass-panel rounded-2xl p-6 relative overflow-hidden group hover:border-brand-500/30 transition-all duration-300">
          <div className="absolute top-0 right-0 w-24 h-24 bg-brand-500/5 rounded-full blur-2xl group-hover:bg-brand-500/10 transition-colors" />
          <h4 className="text-sm font-bold text-white mb-2 flex items-center gap-1.5">
            <UploadCloud size={16} className="text-brand-500" />
            Ingest Talent Data
          </h4>
          <p className="text-xs text-slate-400 mb-4 leading-relaxed">
            Drag and drop resume PDFs to extract structured entities, skill taxonomies, and academic milestones in real-time.
          </p>
          <Link to="/upload" className="text-xs text-brand-500 group-hover:text-brand-400 font-semibold inline-flex items-center gap-1">
            Open Uploader <ChevronRight size={12} className="transition-transform group-hover:translate-x-1" />
          </Link>
        </div>

        <div className="glass-panel rounded-2xl p-6 relative overflow-hidden group hover:border-indigo-500/30 transition-all duration-300">
          <div className="absolute top-0 right-0 w-24 h-24 bg-indigo-500/5 rounded-full blur-2xl group-hover:bg-indigo-500/10 transition-colors" />
          <h4 className="text-sm font-bold text-white mb-2 flex items-center gap-1.5">
            <GitFork size={16} className="text-indigo-400" />
            Explore Connections
          </h4>
          <p className="text-xs text-slate-400 mb-4 leading-relaxed">
            Interact with our full force-directed relationship graph to visualize overlap, core hubs, and career migration paths.
          </p>
          <Link to="/graph" className="text-xs text-indigo-400 group-hover:text-indigo-300 font-semibold inline-flex items-center gap-1">
            Launch Graph Explorer <ChevronRight size={12} className="transition-transform group-hover:translate-x-1" />
          </Link>
        </div>

        <div className="glass-panel rounded-2xl p-6 relative overflow-hidden group hover:border-emerald-500/30 transition-all duration-300">
          <div className="absolute top-0 right-0 w-24 h-24 bg-emerald-500/5 rounded-full blur-2xl group-hover:bg-emerald-500/10 transition-colors" />
          <h4 className="text-sm font-bold text-white mb-2 flex items-center gap-1.5">
            <Zap size={16} className="text-emerald-400" />
            AI Workspace Reports
          </h4>
          <p className="text-xs text-slate-400 mb-4 leading-relaxed">
            Compare candidate profiles side-by-side. Generate custom interview guides and fit analysis automatically.
          </p>
          <Link to="/ai-summary" className="text-xs text-emerald-400 group-hover:text-emerald-300 font-semibold inline-flex items-center gap-1">
            Open AI Workspace <ChevronRight size={12} className="transition-transform group-hover:translate-x-1" />
          </Link>
        </div>
      </section>
    </div>
  );
};

import React, { useEffect, useState } from 'react';
import {
  Check,
  Users,
  AlertCircle,
  Cpu,
  Bookmark,
  Loader2,
  TrendingUp,
  GitCompare
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { resumeService } from '../services/api';
import type { Candidate } from '../types';

interface ComparisonData {
  candidates: Array<{
    candidate_id: string;
    full_name: string;
    email: string | null;
    summary: string | null;
    skills: string[];
    technologies: string[];
    projects: string[];
    education: string[];
    experiences: Array<{
      company: string;
      role: string | null;
      start_date: string | null;
      end_date: string | null;
    }>;
    experience_years: number | null;
  }>;
  metrics: Record<string, {
    skill_overlap: number;
    skill_coverage: number;
    technology_overlap: number;
    total_experience_diff: number | null;
    project_count_diff: number;
  }>;
  ai_analysis: string | null;
  recommendation: string | null;
  error: string | null;
}

// Helper function to format experience display
const formatExperience = (years: number | null): string => {
  if (years === null) return 'Not available';
  if (years === 0) return 'Less than 1 year';
  if (years === 1) return '1 year';
  return `${years} years`;
};

// Helper function to parse metric key and get readable label
const getMetricLabel = (
  metricKey: string,
  metricValue: number,
  candidates: ComparisonData['candidates']
): { label: string; description: string } => {
  const parts = metricKey.split('_vs_');
  if (parts.length === 2) {
    // Find candidate names by ID
    const candA = candidates.find(c => c.candidate_id === parts[0]);
    const candB = candidates.find(c => c.candidate_id === parts[1]);
    const nameA = candA?.full_name || parts[0];
    const nameB = candB?.full_name || parts[1];

    return {
      label: 'Skill Overlap',
      description: `Shared skills between ${nameA} and ${nameB}: ${metricValue}%`
    };
  }
  return {
    label: 'Skill Overlap',
    description: `Shared skills: ${metricValue}%`
  };
};

export const AISummary: React.FC = () => {
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [loading, setLoading] = useState(true);

  // Selected candidates for side-by-side comparison
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [comparisonData, setComparisonData] = useState<ComparisonData | null>(null);
  const [loadingComparison, setLoadingComparison] = useState(false);
  const [comparisonError, setComparisonError] = useState<string | null>(null);

  useEffect(() => {
    const loadCandidates = async () => {
      try {
        const data = await resumeService.searchCandidates('');
        setCandidates(data);
        // Default select the first 2 candidates for comparison
        if (data.length >= 2) {
          setSelectedIds([data[0].id, data[1].id]);
        }
      } catch (err) {
        console.error('Failed to load candidates for AI Summary workspace', err);
      } finally {
        setLoading(false);
      }
    };
    loadCandidates();
  }, []);

  // Fetch comparison data for selected candidates
  useEffect(() => {
    const fetchComparisonData = async () => {
      if (selectedIds.length === 0) {
        setComparisonData(null);
        setComparisonError(null);
        return;
      }
      setLoadingComparison(true);
      setComparisonError(null);
      try {
        const comparison = await resumeService.compareCandidates(selectedIds);
        setComparisonData(comparison);
      } catch (err) {
        console.error('Failed to fetch comparison data', err);
        setComparisonError('Failed to load comparison data. Please try again.');
      } finally {
        setLoadingComparison(false);
      }
    };
    fetchComparisonData();
  }, [selectedIds]);

  const toggleSelectCandidate = (id: string) => {
    setSelectedIds(prev => {
      if (prev.includes(id)) {
        return prev.filter(item => item !== id);
      }
      if (prev.length >= 3) {
        // Limit to 3 candidates for visual comparison layout
        return [...prev.slice(1), id];
      }
      return [...prev, id];
    });
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      
      {/* HEADER SECTION */}
      <div className="space-y-2">
        <h1 className="text-2xl lg:text-3xl font-extrabold text-white tracking-tight">AI Assessment Workspace</h1>
        <p className="text-sm text-slate-400">
          Compare candidate metrics side-by-side. Generate AI comparative analysis of technical skill matching, culture-fit score sheets, and targeted questions.
        </p>
      </div>

      {/* SELECT CANDIDATES SUB-BAR */}
      <section className="glass-panel rounded-2xl p-5 space-y-3">
        <h3 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
          <Users size={14} className="text-brand-500" />
          Select Candidates to Compare (Max 3)
        </h3>

        {loading ? (
          <div className="h-10 bg-slate-900 animate-pulse rounded-xl" />
        ) : (
          <div className="flex flex-wrap gap-2.5">
            {candidates.map(candidate => {
              const isSelected = selectedIds.includes(candidate.id);
              return (
                <button
                  key={candidate.id}
                  onClick={() => toggleSelectCandidate(candidate.id)}
                  className={`px-3 py-2 rounded-xl text-xs font-semibold border transition-all duration-150 flex items-center gap-2 ${
                    isSelected
                      ? 'bg-brand-600/10 border-brand-500/40 text-brand-400'
                      : 'bg-slate-950 border-dark-border text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <div className={`w-3.5 h-3.5 rounded border flex items-center justify-center ${
                    isSelected ? 'bg-brand-600 border-brand-500 text-white' : 'border-dark-border'
                  }`}>
                    {isSelected && <Check size={10} />}
                  </div>
                  <span>{candidate.name}</span>
                  <span className="text-[10px] text-slate-500 font-normal">({candidate.currentRole})</span>
                </button>
              );
            })}
          </div>
        )}
      </section>

      {/* COMPARISON WORKSPACE PANELS */}
      {selectedIds.length > 0 ? (
        loadingComparison ? (
          // LOADING SKELETON
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="glass-panel rounded-2xl p-6 h-80 animate-shimmer" />
            <div className="glass-panel rounded-2xl p-6 h-80 animate-shimmer" />
            <div className="glass-panel rounded-2xl p-6 h-80 animate-shimmer" />
          </div>
        ) : comparisonError ? (
          <div className="glass-panel rounded-2xl p-12 text-center max-w-md mx-auto space-y-4 border border-dark-border">
            <AlertCircle size={32} className="text-red-500 mx-auto" />
            <div className="space-y-1.5">
              <h3 className="text-sm font-bold text-white uppercase tracking-wider">Comparison Error</h3>
              <p className="text-xs text-slate-400">{comparisonError}</p>
            </div>
          </div>
        ) : comparisonData ? (
          <div className="space-y-6">

            {/* COMPARATIVE CARDS GRID */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-stretch">
              {comparisonData.candidates.map(candidate => {
                const cand = candidates.find(c => c.id === candidate.candidate_id);
                const displayName = cand ? cand.currentRole : 'Candidate';

                // Ensure we never display UUIDs as names
                const displayNameClean = displayName.startsWith('cand-') || displayName.includes('uuid') ? 'Candidate' : displayName;
                const nameClean = candidate.full_name && candidate.full_name.length > 30 ? candidate.full_name : candidate.full_name;

                return (
                  <div
                    key={candidate.candidate_id}
                    className="glass-panel rounded-2xl p-6 flex flex-col justify-between border border-dark-border/80 relative overflow-hidden"
                  >
                    <div className="space-y-4">

                      {/* Title & Core match */}
                      <div className="flex items-start justify-between">
                        <div>
                          <h3 className="text-base font-extrabold text-white">{nameClean || 'Candidate'}</h3>
                          <span className="text-xs text-brand-400 font-semibold">{displayNameClean}</span>
                        </div>
                      </div>

                      {/* Score metrics */}
                      <div className="grid grid-cols-3 gap-2 py-3 border-t border-b border-dark-border/40 text-center">
                        <div>
                          <span className="text-[9px] text-slate-500 uppercase font-semibold">Skills</span>
                          <p className="text-sm font-extrabold text-white mt-0.5">{candidate.skills.length}</p>
                        </div>
                        <div>
                          <span className="text-[9px] text-slate-500 uppercase font-semibold">Projects</span>
                          <p className="text-sm font-extrabold text-indigo-400 mt-0.5">{candidate.projects.length}</p>
                        </div>
                        <div>
                          <span className="text-[9px] text-slate-500 uppercase font-semibold">Experience</span>
                          <p className="text-sm font-extrabold text-emerald-400 mt-0.5">{formatExperience(candidate.experience_years)}</p>
                        </div>
                      </div>

                      {/* Skills list */}
                      <div className="space-y-2.5">
                        <span className="text-[10px] text-slate-400 uppercase tracking-wider font-bold block">Skills</span>
                        <ul className="space-y-1.5 text-xs text-slate-300">
                          {candidate.skills.slice(0, 5).map((skill, idx) => (
                            <li key={idx} className="flex gap-1.5 items-start">
                              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 shrink-0 mt-1.5" />
                              <span className="leading-snug">{skill}</span>
                            </li>
                          ))}
                          {candidate.skills.length > 5 && (
                            <li className="text-xs text-slate-500 italic">
                              +{candidate.skills.length - 5} more skills
                            </li>
                          )}
                        </ul>
                      </div>

                      {/* Technologies list */}
                      <div className="space-y-2.5 pt-2">
                        <span className="text-[10px] text-slate-400 uppercase tracking-wider font-bold block">Technologies</span>
                        <ul className="space-y-1.5 text-xs text-slate-300">
                          {candidate.technologies.slice(0, 4).map((tech, idx) => (
                            <li key={idx} className="flex gap-1.5 items-start">
                              <span className="w-1.5 h-1.5 rounded-full bg-indigo-500 shrink-0 mt-1.5" />
                              <span className="leading-snug">{tech}</span>
                            </li>
                          ))}
                          {candidate.technologies.length > 4 && (
                            <li className="text-xs text-slate-500 italic">
                              +{candidate.technologies.length - 4} more technologies
                            </li>
                          )}
                        </ul>
                      </div>

                    </div>

                    {/* Summary snippet */}
                    {candidate.summary && (
                      <div className="mt-6 pt-4 border-t border-dark-border/40 text-xs text-slate-400 leading-relaxed italic">
                        &ldquo;{candidate.summary.slice(0, 120)}...&rdquo;
                      </div>
                    )}

                  </div>
                );
              })}
            </div>

            {/* INTEGRATIVE DYNAMIC SUMMARY */}
            <section className="glass-panel rounded-3xl p-6 border border-dark-border/80 bg-gradient-to-br from-dark-card to-brand-950/10">
              <div className="flex items-center gap-2 border-b border-dark-border/40 pb-4 mb-4">
                <Cpu className="text-brand-500" size={20} />
                <h3 className="text-sm font-extrabold text-white uppercase tracking-wider">Comparative Analysis</h3>
              </div>

              <div className="space-y-4 text-xs text-slate-300 leading-relaxed font-normal">
                {comparisonData.ai_analysis ? (
                  <div className="prose prose-invert prose-sm max-w-none">
                    <ReactMarkdown>{comparisonData.ai_analysis}</ReactMarkdown>
                  </div>
                ) : (
                  <p>AI comparative analysis unavailable. Objective metrics are shown below.</p>
                )}

                {/* Show objective metrics with better labels */}
                {Object.keys(comparisonData.metrics).length > 0 && (
                  <div className="p-4 rounded-2xl bg-slate-900 border border-dark-border text-slate-400">
                    <div className="flex items-center gap-2 mb-3">
                      <GitCompare size={16} className="text-brand-500" />
                      <span className="text-[10px] uppercase font-bold text-white">Objective Comparison Metrics</span>
                    </div>
                    <div className="space-y-3">
                      {Object.entries(comparisonData.metrics).map(([key, metric]) => {
                        const { label, description } = getMetricLabel(key, metric.skill_overlap, comparisonData.candidates);
                        return (
                          <div key={key} className="space-y-1">
                            <div className="flex justify-between items-center">
                              <span className="text-[10px] font-semibold text-slate-300">{label}</span>
                              <span className="text-white font-bold">{metric.skill_overlap}%</span>
                            </div>
                            <p className="text-[9px] text-slate-500 leading-snug">{description}</p>
                            {metric.skill_coverage !== metric.skill_overlap && (
                              <div className="flex justify-between items-center mt-1">
                                <span className="text-[10px] text-slate-400">Skill Coverage</span>
                                <span className="text-brand-400 font-semibold">{metric.skill_coverage}%</span>
                              </div>
                            )}
                            {metric.technology_overlap > 0 && (
                              <div className="flex justify-between items-center mt-1">
                                <span className="text-[10px] text-slate-400">Technology Overlap</span>
                                <span className="text-indigo-400 font-semibold">{metric.technology_overlap}%</span>
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* Recommendation */}
                {comparisonData.recommendation && (
                  <div className="p-4 rounded-2xl bg-slate-900 border border-dark-border text-slate-400 flex items-start gap-2.5">
                    <TrendingUp size={16} className="text-brand-500 shrink-0 mt-0.5" />
                    <div className="flex-1">
                      <span className="text-[10px] uppercase font-bold text-white block mb-1.5">Hiring Recommendation</span>
                      <p className="text-xs leading-relaxed">{comparisonData.recommendation}</p>
                    </div>
                  </div>
                )}
              </div>
            </section>

          </div>
        ) : (
          <div className="glass-panel rounded-2xl p-12 text-center max-w-md mx-auto space-y-4 border border-dark-border">
            <Loader2 size={32} className="text-slate-600 mx-auto animate-spin" />
            <div className="space-y-1.5">
              <h3 className="text-sm font-bold text-white uppercase tracking-wider">Loading Comparison</h3>
              <p className="text-xs text-slate-400">Fetching candidate comparison data...</p>
            </div>
          </div>
        )
      ) : (
        <div className="glass-panel rounded-2xl p-12 text-center max-w-md mx-auto space-y-4 border border-dark-border">
          <Bookmark size={32} className="text-slate-600 mx-auto" />
          <div className="space-y-1.5">
            <h3 className="text-sm font-bold text-white uppercase tracking-wider">No Candidates Selected</h3>
            <p className="text-xs text-slate-400">
              Select at least one candidate from the list above to render detailed AI assessment reports.
            </p>
          </div>
        </div>
      )}

    </div>
  );
};

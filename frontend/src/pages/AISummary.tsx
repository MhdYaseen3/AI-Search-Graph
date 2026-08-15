import React, { useEffect, useState } from 'react';
import { 
  Check, 
  Users, 
  AlertCircle,
  Cpu,
  Bookmark
} from 'lucide-react';
import { resumeService } from '../services/api';
import type { Candidate, AISummaryReport } from '../types';

export const AISummary: React.FC = () => {
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [loading, setLoading] = useState(true);
  
  // Selected candidates for side-by-side comparison
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [comparisonReports, setComparisonReports] = useState<AISummaryReport[]>([]);
  const [loadingComparison, setLoadingComparison] = useState(false);

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

  // Fetch AI reports for selected candidates
  useEffect(() => {
    const fetchComparisonReports = async () => {
      if (selectedIds.length === 0) {
        setComparisonReports([]);
        return;
      }
      setLoadingComparison(true);
      try {
        const reports = await Promise.all(
          selectedIds.map(id => resumeService.getAISummary(id))
        );
        setComparisonReports(reports);
      } catch (err) {
        console.error('Failed to fetch AI reports for comparison', err);
      } finally {
        setLoadingComparison(false);
      }
    };
    fetchComparisonReports();
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
        ) : (
          <div className="space-y-6">
            
            {/* COMPARATIVE CARDS GRID */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-stretch">
              {comparisonReports.map(report => {
                const cand = candidates.find(c => c.id === report.candidateId);
                if (!cand) return null;

                return (
                  <div 
                    key={report.candidateId} 
                    className="glass-panel rounded-2xl p-6 flex flex-col justify-between border border-dark-border/80 relative overflow-hidden"
                  >
                    {/* Glowing card border accents based on recommendation */}
                    {report.hiringRecommendation === 'Strong Hire' && (
                      <div className="absolute top-0 left-0 right-0 h-1 bg-emerald-500" />
                    )}
                    {report.hiringRecommendation === 'Hire' && (
                      <div className="absolute top-0 left-0 right-0 h-1 bg-indigo-500" />
                    )}

                    <div className="space-y-4">
                      
                      {/* Title & Core match */}
                      <div className="flex items-start justify-between">
                        <div>
                          <h3 className="text-base font-extrabold text-white">{report.candidateName}</h3>
                          <span className="text-xs text-brand-400 font-semibold">{cand.currentRole}</span>
                        </div>
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                          report.hiringRecommendation === 'Strong Hire' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                          'bg-indigo-500/10 text-indigo-400 border border-indigo-500/20'
                        }`}>
                          {report.hiringRecommendation}
                        </span>
                      </div>

                      {/* Score metrics */}
                      <div className="grid grid-cols-3 gap-2 py-3 border-t border-b border-dark-border/40 text-center">
                        <div>
                          <span className="text-[9px] text-slate-500 uppercase font-semibold">Match Rating</span>
                          <p className="text-sm font-extrabold text-white mt-0.5">{report.matchScore}%</p>
                        </div>
                        <div>
                          <span className="text-[9px] text-slate-500 uppercase font-semibold">Skills Align</span>
                          <p className="text-sm font-extrabold text-indigo-400 mt-0.5">{report.skillMatchPercent}%</p>
                        </div>
                        <div>
                          <span className="text-[9px] text-slate-500 uppercase font-semibold">Culture Fit</span>
                          <p className="text-sm font-extrabold text-emerald-400 mt-0.5">{report.cultureFitPercent}%</p>
                        </div>
                      </div>

                      {/* Strengths lists */}
                      <div className="space-y-2.5">
                        <span className="text-[10px] text-slate-400 uppercase tracking-wider font-bold block">Top Skill Strengths</span>
                        <ul className="space-y-1.5 text-xs text-slate-300">
                          {report.strengths.slice(0, 3).map((str, idx) => (
                            <li key={idx} className="flex gap-1.5 items-start">
                              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 shrink-0 mt-1.5" />
                              <span className="leading-snug">{str}</span>
                            </li>
                          ))}
                        </ul>
                      </div>

                      {/* Gaps lists */}
                      <div className="space-y-2.5 pt-2">
                        <span className="text-[10px] text-slate-400 uppercase tracking-wider font-bold block">Assessed Talent Gaps</span>
                        <ul className="space-y-1.5 text-xs text-slate-300">
                          {report.gaps.slice(0, 2).map((gap, idx) => (
                            <li key={idx} className="flex gap-1.5 items-start">
                              <span className="w-1.5 h-1.5 rounded-full bg-amber-500 shrink-0 mt-1.5" />
                              <span className="leading-snug">{gap}</span>
                            </li>
                          ))}
                        </ul>
                      </div>

                    </div>

                    {/* Reasoning snippet */}
                    <div className="mt-6 pt-4 border-t border-dark-border/40 text-xs text-slate-400 leading-relaxed italic">
                      &ldquo;{report.reasoning.slice(0, 150)}...&rdquo;
                    </div>

                  </div>
                );
              })}
            </div>

            {/* INTEGRATIVE DYNAMIC SUMMARY SUMMARY */}
            <section className="glass-panel rounded-3xl p-6 border border-dark-border/80 bg-gradient-to-br from-dark-card to-brand-950/10">
              <div className="flex items-center gap-2 border-b border-dark-border/40 pb-4 mb-4">
                <Cpu className="text-brand-500" size={20} />
                <h3 className="text-sm font-extrabold text-white uppercase tracking-wider">Comparative Pipeline Recommendation</h3>
              </div>

              <div className="space-y-4 text-xs text-slate-300 leading-relaxed font-normal">
                <p>
                  Analyzing the selected talent profiles shows strong matches against standard templates. 
                  {comparisonReports[0] && comparisonReports[1] && (
                    <span>
                      {' '}Comparing <strong>{comparisonReports[0].candidateName}</strong> against <strong>{comparisonReports[1].candidateName}</strong>, the former offers higher skill alignment for core computational libraries ({comparisonReports[0].skillMatchPercent}% vs {comparisonReports[1].skillMatchPercent}%), while the latter shows excellent adaptability under collaborative corporate structures.
                    </span>
                  )}
                </p>
                <div className="p-4 rounded-2xl bg-slate-900 border border-dark-border text-slate-400 flex items-start gap-2.5">
                  <AlertCircle size={16} className="text-brand-500 shrink-0 mt-0.5" />
                  <div>
                    <span className="text-[10px] uppercase font-bold text-white block mb-0.5">Integration Suggestion</span>
                    <span>For engineering vacancies, prioritize candidates displaying match indexes &gt; 90% and lower relationship gaps. Leverage the suggested interview guide tags to drill into custom fine-tuning questions.</span>
                  </div>
                </div>
              </div>
            </section>

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

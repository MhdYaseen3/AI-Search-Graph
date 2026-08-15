import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  ArrowLeft, 
  Mail, 
  Phone, 
  MapPin, 
  Sparkles, 
  GitFork, 
  GraduationCap, 
  Briefcase,
  CheckCircle,
  HelpCircle,
  FileText
} from 'lucide-react';
import { resumeService } from '../services/api';
import type { Candidate, AISummaryReport } from '../types';

export const CandidateDetails: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [candidate, setCandidate] = useState<Candidate | null>(null);
  const [aiSummary, setAISummary] = useState<AISummaryReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'overview' | 'ai-assessment'>('overview');

  useEffect(() => {
    const fetchCandidateDetails = async () => {
      if (!id) return;
      setLoading(true);
      try {
        const [candData, summaryData] = await Promise.all([
          resumeService.getCandidateById(id),
          resumeService.getAISummary(id)
        ]);
        setCandidate(candData);
        setAISummary(summaryData);
      } catch (err) {
        console.error('Failed to load candidate details', err);
      } finally {
        setLoading(false);
      }
    };
    fetchCandidateDetails();
  }, [id]);

  if (loading) {
    return (
      <div className="space-y-6 animate-in fade-in duration-200">
        <div className="h-24 rounded-2xl bg-slate-900/60 animate-pulse" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="h-64 rounded-2xl bg-slate-900/60 animate-pulse md:col-span-2" />
          <div className="h-64 rounded-2xl bg-slate-900/60 animate-pulse" />
        </div>
      </div>
    );
  }

  if (!candidate) {
    return (
      <div className="text-center py-12 space-y-4">
        <h3 className="text-lg font-bold text-white">Candidate profile not found</h3>
        <button
          onClick={() => navigate('/search')}
          className="bg-brand-600 hover:bg-brand-700 text-white px-4 py-2 rounded-xl text-xs font-semibold"
        >
          Back to Search
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      
      {/* BACK NAVIGATION */}
      <button 
        onClick={() => navigate(-1)}
        className="text-xs text-slate-400 hover:text-white flex items-center gap-1.5 transition-colors"
      >
        <ArrowLeft size={14} />
        <span>Back to talent search</span>
      </button>

      {/* CANDIDATE HEADER SUMMARY */}
      <section className="glass-panel rounded-2xl p-6 flex flex-col md:flex-row items-center justify-between gap-6">
        
        <div className="flex items-center gap-4 text-center md:text-left flex-col md:flex-row">
          <div className="w-16 h-16 rounded-2xl bg-brand-600/10 border border-brand-500/20 text-brand-500 font-extrabold flex items-center justify-center text-lg">
            {candidate.name.split(' ').map(n=>n[0]).join('')}
          </div>
          <div className="space-y-1">
            <h1 className="text-xl lg:text-2xl font-extrabold text-white leading-none">{candidate.name}</h1>
            <p className="text-sm font-semibold text-brand-400">{candidate.currentRole}</p>
            <p className="text-xs text-slate-500">{candidate.currentCompany} &bull; {candidate.location}</p>
          </div>
        </div>

        {/* METRICS & QUICK ACTION GAUGE */}
        <div className="flex items-center gap-6">
          <div className="text-center">
            <span className="text-[10px] text-slate-500 uppercase tracking-wider block font-semibold">Match Score</span>
            <div className="inline-flex items-center justify-center relative mt-1">
              <svg className="w-14 h-14 transform -rotate-90">
                <circle cx="28" cy="28" r="22" className="stroke-slate-800" strokeWidth="4" fill="transparent" />
                <circle 
                  cx="28" 
                  cy="28" 
                  r="22" 
                  className="stroke-emerald-500" 
                  strokeWidth="4" 
                  fill="transparent" 
                  strokeDasharray={138.2}
                  strokeDashoffset={138.2 - (138.2 * candidate.matchScore) / 100}
                />
              </svg>
              <span className="absolute text-xs font-bold text-white">{candidate.matchScore}%</span>
            </div>
          </div>

          <div className="flex flex-col gap-2">
            <button
              onClick={() => navigate(`/graph?id=${candidate.id}`)}
              className="bg-brand-600 hover:bg-brand-700 text-white text-xs font-semibold py-2 px-4 rounded-xl flex items-center gap-1.5 shadow-md transition-colors"
            >
              <GitFork size={14} />
              <span>Explore Relationships</span>
            </button>
            <button
              onClick={() => setActiveTab('ai-assessment')}
              className="bg-slate-900 border border-dark-border text-slate-300 hover:bg-slate-800 text-xs font-semibold py-2 px-4 rounded-xl flex items-center gap-1.5 transition-colors"
            >
              <Sparkles size={14} className="text-brand-400" />
              <span>AI Summary</span>
            </button>
          </div>
        </div>
      </section>

      {/* MAIN LAYOUT WITH LEFT DETAILS AND RIGHT SIDE CONTACTS CARD */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* LEFT COMPONENT DETAILS (Overview/Timeline/AI evaluation tabs) */}
        <div className="lg:col-span-2 space-y-6">
          
          {/* TABS SELECTOR */}
          <div className="flex border-b border-dark-border/40">
            <button
              onClick={() => setActiveTab('overview')}
              className={`pb-3 text-xs font-bold uppercase tracking-wider border-b-2 px-4 transition-all duration-200 ${
                activeTab === 'overview' 
                  ? 'border-brand-500 text-brand-500' 
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              Overview & Timeline
            </button>
            <button
              onClick={() => setActiveTab('ai-assessment')}
              className={`pb-3 text-xs font-bold uppercase tracking-wider border-b-2 px-4 transition-all duration-200 ${
                activeTab === 'ai-assessment' 
                  ? 'border-brand-500 text-brand-500' 
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              AI Assessment Report
            </button>
          </div>

          {/* TAB CONTENT OVERVIEW */}
          {activeTab === 'overview' && (
            <div className="space-y-6">
              
              {/* PROFESSIONAL SUMMARY */}
              <div className="glass-panel rounded-2xl p-6 space-y-3">
                <h3 className="text-xs font-bold text-white uppercase tracking-wider">Professional Profile</h3>
                <p className="text-xs text-slate-300 leading-relaxed font-normal">
                  {candidate.summary}
                </p>
              </div>

              {/* TIMELINE OF EXPERIENCE */}
              <div className="glass-panel rounded-2xl p-6 space-y-4">
                <h3 className="text-xs font-bold text-white uppercase tracking-wider">Employment History</h3>
                
                <div className="relative border-l border-dark-border/60 ml-3 pl-6 space-y-6 pt-2">
                  {candidate.experience.map((exp, index) => (
                    <div key={index} className="relative space-y-1">
                      {/* Timeline dot */}
                      <span className="absolute -left-[31px] top-1.5 w-3 h-3 rounded-full bg-brand-500 ring-4 ring-dark-bg" />
                      
                      <div className="flex items-center justify-between flex-wrap gap-2">
                        <h4 className="text-sm font-bold text-white">{exp.role}</h4>
                        <span className="text-[10px] text-slate-500 font-semibold bg-slate-900 border border-dark-border px-2 py-0.5 rounded-full">
                          {exp.duration}
                        </span>
                      </div>
                      
                      <p className="text-[11px] font-semibold text-brand-400 flex items-center gap-1">
                        <Briefcase size={12} className="text-slate-500" />
                        {exp.company}
                      </p>
                      
                      <p className="text-xs text-slate-400 leading-relaxed pt-1">
                        {exp.description}
                      </p>
                    </div>
                  ))}
                </div>
              </div>

              {/* ACADEMIC HISTORY */}
              <div className="glass-panel rounded-2xl p-6 space-y-4">
                <h3 className="text-xs font-bold text-white uppercase tracking-wider">Education</h3>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {candidate.education.map((edu, index) => (
                    <div key={index} className="p-4 rounded-xl bg-slate-900/40 border border-dark-border/60 flex gap-3 items-start">
                      <div className="w-8 h-8 rounded-lg bg-indigo-500/10 text-indigo-400 flex items-center justify-center shrink-0 mt-0.5">
                        <GraduationCap size={16} />
                      </div>
                      <div className="space-y-1">
                        <h4 className="text-xs font-bold text-white leading-tight">{edu.degree}</h4>
                        <p className="text-[10px] text-slate-400">{edu.school}</p>
                        <span className="text-[9px] text-slate-500 font-semibold block">{edu.year}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

            </div>
          )}

          {/* TAB CONTENT AI ASSESSMENT */}
          {activeTab === 'ai-assessment' && aiSummary && (
            <div className="space-y-6">
              
              {/* STRENGTHS AND GAPS BARS */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
                <div className="glass-panel rounded-xl p-4 space-y-1.5 text-center">
                  <span className="text-[9px] text-slate-500 uppercase font-semibold">Experience Match</span>
                  <div className="text-xl font-extrabold text-brand-400">{aiSummary.experienceMatchPercent}%</div>
                  <div className="w-full bg-slate-900 h-1.5 rounded-full overflow-hidden">
                    <div className="h-full bg-brand-500" style={{ width: `${aiSummary.experienceMatchPercent}%` }} />
                  </div>
                </div>

                <div className="glass-panel rounded-xl p-4 space-y-1.5 text-center">
                  <span className="text-[9px] text-slate-500 uppercase font-semibold">Skill Set Alignment</span>
                  <div className="text-xl font-extrabold text-indigo-400">{aiSummary.skillMatchPercent}%</div>
                  <div className="w-full bg-slate-900 h-1.5 rounded-full overflow-hidden">
                    <div className="h-full bg-indigo-500" style={{ width: `${aiSummary.skillMatchPercent}%` }} />
                  </div>
                </div>

                <div className="glass-panel rounded-xl p-4 space-y-1.5 text-center">
                  <span className="text-[9px] text-slate-500 uppercase font-semibold">Cultural Fit Score</span>
                  <div className="text-xl font-extrabold text-emerald-400">{aiSummary.cultureFitPercent}%</div>
                  <div className="w-full bg-slate-900 h-1.5 rounded-full overflow-hidden">
                    <div className="h-full bg-emerald-500" style={{ width: `${aiSummary.cultureFitPercent}%` }} />
                  </div>
                </div>
              </div>

              {/* CORE REASONING ASSESSMENTS */}
              <div className="glass-panel rounded-2xl p-6 space-y-4">
                <div className="flex items-center justify-between border-b border-dark-border/40 pb-3">
                  <h3 className="text-xs font-bold text-white uppercase tracking-wider">AI Evaluation Summary</h3>
                  <span className={`px-3 py-1 rounded-full text-[10px] font-bold ${
                    aiSummary.hiringRecommendation === 'Strong Hire' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                    aiSummary.hiringRecommendation === 'Hire' ? 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/20' :
                    'bg-slate-800 text-slate-400'
                  }`}>
                    Recommendation: {aiSummary.hiringRecommendation}
                  </span>
                </div>
                
                <p className="text-xs text-slate-300 leading-relaxed font-normal">
                  {aiSummary.reasoning}
                </p>
              </div>

              {/* STRENGTHS AND GAPS BULLETS */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                <div className="glass-panel rounded-2xl p-5 space-y-3">
                  <h4 className="text-xs font-bold text-emerald-400 uppercase tracking-wider flex items-center gap-1">
                    <CheckCircle size={14} /> Key Strengths
                  </h4>
                  <ul className="space-y-2 text-xs text-slate-300 list-disc list-inside">
                    {aiSummary.strengths.map((str, idx) => (
                      <li key={idx} className="leading-relaxed">{str}</li>
                    ))}
                  </ul>
                </div>

                <div className="glass-panel rounded-2xl p-5 space-y-3">
                  <h4 className="text-xs font-bold text-amber-400 uppercase tracking-wider flex items-center gap-1">
                    <HelpCircle size={14} /> Noted Experience Gaps
                  </h4>
                  <ul className="space-y-2 text-xs text-slate-300 list-disc list-inside">
                    {aiSummary.gaps.map((gap, idx) => (
                      <li key={idx} className="leading-relaxed">{gap}</li>
                    ))}
                  </ul>
                </div>
              </div>

              {/* CUSTOM INTERVIEW QUESTIONS */}
              <div className="glass-panel rounded-2xl p-6 space-y-4 bg-gradient-to-br from-dark-card to-brand-950/10">
                <h3 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
                  <Sparkles size={14} className="text-brand-500" />
                  Suggested AI Behavioral Questions
                </h3>
                
                <div className="space-y-3">
                  {aiSummary.suggestedInterviewQuestions.map((q, idx) => (
                    <div key={idx} className="p-3 rounded-xl bg-slate-900 border border-dark-border text-xs text-slate-200 flex gap-2">
                      <span className="font-bold text-brand-500 shrink-0">Q{idx+1}:</span>
                      <span className="leading-relaxed">{q}</span>
                    </div>
                  ))}
                </div>
              </div>

            </div>
          )}

        </div>

        {/* RIGHT SIDE CONTACT INFORMATION AND SKILL CLOUD */}
        <div className="space-y-6">
          
          {/* CONTACT INFO CARD */}
          <div className="glass-panel rounded-2xl p-6 space-y-4">
            <h3 className="text-xs font-bold text-white uppercase tracking-wider border-b border-dark-border/40 pb-3">
              Contact Channels
            </h3>
            
            <div className="space-y-3.5 text-xs text-slate-300">
              <div className="flex items-center gap-3">
                <Mail size={16} className="text-slate-500" />
                <a href={`mailto:${candidate.email}`} className="hover:text-brand-400 transition-colors font-medium break-all">{candidate.email}</a>
              </div>
              <div className="flex items-center gap-3">
                <Phone size={16} className="text-slate-500" />
                <a href={`tel:${candidate.phone}`} className="hover:text-brand-400 transition-colors font-medium">{candidate.phone}</a>
              </div>
              <div className="flex items-center gap-3">
                <MapPin size={16} className="text-slate-500" />
                <span>{candidate.location}</span>
              </div>
            </div>
            
            <div className="pt-2 border-t border-dark-border/40">
              <button className="w-full bg-slate-900 hover:bg-slate-800 text-slate-300 font-semibold text-xs py-2.5 rounded-xl border border-dark-border flex items-center justify-center gap-1.5 transition-colors">
                <FileText size={14} />
                <span>Download Extracted CV</span>
              </button>
            </div>
          </div>

          {/* EXTRACTED SKILL MATRIX */}
          <div className="glass-panel rounded-2xl p-6 space-y-4">
            <h3 className="text-xs font-bold text-white uppercase tracking-wider border-b border-dark-border/40 pb-3">
              Skill Entities Matrix
            </h3>
            
            <div className="flex flex-wrap gap-2">
              {candidate.skills.map((skill) => (
                <span 
                  key={skill}
                  className="px-2.5 py-1 rounded-lg bg-slate-900 border border-dark-border/80 text-[10px] text-slate-200 font-semibold shadow-sm hover:border-brand-500/40 transition-colors"
                >
                  {skill}
                </span>
              ))}
            </div>
          </div>

        </div>

      </div>

    </div>
  );
};

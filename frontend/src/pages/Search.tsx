import React, { useState, useEffect, useMemo, useRef } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { 
  Search as SearchIcon, 
  SlidersHorizontal, 
  MapPin, 
  GraduationCap, 
  Briefcase,
  ChevronRight,
  GitFork,
  User,
  FilterX,
  Check,
  X
} from 'lucide-react';
import { resumeService } from '../services/api';
import type { Candidate } from '../types';

export const Search: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const queryParam = searchParams.get('q') || '';

  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [showFilters, setShowFilters] = useState(false);
  const [searchAttempt, setSearchAttempt] = useState(0);
  const searchFormRef = useRef<HTMLFormElement>(null);

  // Filters State
  const [minScore, setMinScore] = useState<number>(0);
  const [selectedSkill, setSelectedSkill] = useState<string>('');
  const [selectedLocation, setSelectedLocation] = useState<string>('');

  useEffect(() => {
    const controller = new AbortController();
    let active = true;

    const fetchSearchResults = async () => {
      setLoading(true);
      setSearchError(null);
      try {
        const results = await resumeService.searchCandidates(queryParam, controller.signal);
        if (active) setCandidates(results);
      } catch (err) {
        if (!active || controller.signal.aborted) return;
        console.error('Search error', err);
        setCandidates([]);
        setSearchError('Unable to load candidates. Please try again.');
      } finally {
        if (active) setLoading(false);
      }
    };

    void fetchSearchResults();
    return () => {
      active = false;
      controller.abort();
    };
  }, [queryParam, searchAttempt]);

  const allSkills = useMemo(
    () => Array.from(new Set(candidates.flatMap((candidate) => candidate.skills))),
    [candidates],
  );
  const allLocations = useMemo(
    () => Array.from(new Set(candidates
      .map((candidate) => candidate.location)
      .filter(Boolean)
      .map((location) => location.split(',')[0].trim()))),
    [candidates],
  );
  const filteredCandidates = useMemo(() => candidates.filter((candidate) => (
    (minScore === 0 || candidate.matchScore >= minScore)
    && (!selectedSkill || candidate.skills.includes(selectedSkill))
    && (!selectedLocation || candidate.location.toLowerCase().includes(selectedLocation.toLowerCase()))
  )), [candidates, minScore, selectedSkill, selectedLocation]);

  const handleSearchSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const query = String(formData.get('query') ?? '').trim();
    setSearchParams(query ? { q: query } : {});
  };

  const handleResetFilters = () => {
    setMinScore(0);
    setSelectedSkill('');
    setSelectedLocation('');
    searchFormRef.current?.reset();
    setSearchParams({});
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      
      {/* SEARCH AND FILTER HEAD BAR */}
      <div className="flex flex-col md:flex-row gap-3 items-center justify-between">
        <form ref={searchFormRef} onSubmit={handleSearchSubmit} className="w-full md:max-w-xl flex items-center gap-2">
          <div className="relative flex-1">
            <SearchIcon className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500" size={18} />
            <input
              key={queryParam}
              name="query"
              type="text"
              placeholder="Search skills, companies, names..."
              defaultValue={queryParam}
              className="w-full bg-slate-900 border border-dark-border focus:border-brand-500 rounded-xl py-3 pl-12 pr-4 text-sm text-slate-100 placeholder-slate-500 outline-none transition-colors"
            />
          </div>
          <button
            type="submit"
            className="bg-brand-600 hover:bg-brand-700 text-white font-semibold text-sm px-6 py-3 rounded-xl shadow-lg transition-colors"
          >
            Search
          </button>
        </form>

        <button
          onClick={() => setShowFilters(!showFilters)}
          className={`flex items-center gap-2 px-4 py-3 rounded-xl border text-sm font-semibold transition-colors ${
            showFilters || selectedSkill || selectedLocation || minScore > 0
              ? 'bg-brand-600/10 border-brand-500/30 text-brand-500'
              : 'bg-slate-900 border-dark-border text-slate-300 hover:bg-slate-800'
          }`}
        >
          <SlidersHorizontal size={16} />
          <span>Advanced Filters</span>
        </button>
      </div>

      {/* FILTER DRAWER AREA */}
      {showFilters && (
        <div className="glass-panel rounded-2xl p-6 grid grid-cols-1 md:grid-cols-3 gap-6 border border-dark-border/80 animate-in slide-in-from-top duration-200">
          
          {/* Match Score Slider */}
          <div className="space-y-2.5">
            <div className="flex justify-between text-xs font-semibold">
              <span className="text-slate-400">Min Match Score</span>
              <span className="text-brand-400 font-bold">{minScore}%</span>
            </div>
            <input
              type="range"
              min="0"
              max="100"
              value={minScore}
              onChange={(e) => setMinScore(Number(e.target.value))}
              className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-brand-600"
            />
            <span className="text-[10px] text-slate-500 block">Filters candidates with matching indexes below threshold</span>
          </div>

          {/* Skill Selector */}
          <div className="space-y-2">
            <span className="text-xs font-semibold text-slate-400 block">Required Skill Hub</span>
            <select
              value={selectedSkill}
              onChange={(e) => setSelectedSkill(e.target.value)}
              className="w-full bg-slate-950 border border-dark-border focus:border-brand-500 rounded-xl py-2 px-3 text-xs text-slate-300 outline-none"
            >
              <option value="">All Skills</option>
              {allSkills.map(s => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>

          {/* Location Selector */}
          <div className="space-y-2">
            <span className="text-xs font-semibold text-slate-400 block">Geography / Location</span>
            <select
              value={selectedLocation}
              onChange={(e) => setSelectedLocation(e.target.value)}
              className="w-full bg-slate-950 border border-dark-border focus:border-brand-500 rounded-xl py-2 px-3 text-xs text-slate-300 outline-none"
            >
              <option value="">All Locations</option>
              {allLocations.map(l => (
                <option key={l} value={l}>{l}</option>
              ))}
            </select>
          </div>

          <div className="md:col-span-3 border-t border-dark-border/40 pt-4 flex justify-end">
            <button
              onClick={handleResetFilters}
              className="text-xs text-slate-400 hover:text-white font-semibold flex items-center gap-1"
            >
              <FilterX size={14} />
              Reset Filters
            </button>
          </div>
        </div>
      )}

      {/* SEARCH RESULTS FEED */}
      {loading ? (
        // LOADING SHIMMER GRID
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          <div className="glass-panel rounded-2xl p-6 h-48 animate-shimmer" />
          <div className="glass-panel rounded-2xl p-6 h-48 animate-shimmer" />
        </div>
      ) : searchError ? (
        <div className="glass-panel rounded-2xl p-12 text-center max-w-md mx-auto space-y-4 border border-red-500/20">
          <div className="w-16 h-16 rounded-full bg-red-500/10 border border-red-500/20 flex items-center justify-center text-red-400 mx-auto">
            <FilterX size={28} />
          </div>
          <div className="space-y-1.5">
            <h3 className="text-base font-bold text-white">Search unavailable</h3>
            <p className="text-xs text-slate-400">{searchError}</p>
          </div>
          <button
            onClick={() => setSearchAttempt((attempt) => attempt + 1)}
            className="bg-brand-600 hover:bg-brand-700 text-white font-semibold text-xs py-2 px-5 rounded-xl shadow-md transition-colors"
          >
            Try Again
          </button>
        </div>
      ) : filteredCandidates.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {filteredCandidates.map((candidate) => (
            <div 
              key={candidate.id}
              className="glass-panel rounded-2xl p-6 border border-dark-border hover:border-brand-500/20 hover:scale-[1.01] transition-all duration-200 flex flex-col justify-between space-y-4"
            >
              <div className="flex items-start justify-between">
                
                <div className="flex items-center gap-3">
                  <div className="w-11 h-11 rounded-xl bg-brand-600/10 border border-brand-500/20 text-brand-500 font-bold flex items-center justify-center text-xs">
                    {candidate.name.split(' ').map(n=>n[0]).join('')}
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-white leading-snug">{candidate.name}</h3>
                    <p className="text-xs text-slate-400 flex items-center gap-1">
                      <Briefcase size={12} className="text-slate-500" />
                      {candidate.currentRole}
                    </p>
                  </div>
                </div>

                <span className={`inline-block px-2.5 py-1 rounded-full font-bold text-xs ${
                  candidate.matchScore >= 90 ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                  candidate.matchScore >= 80 ? 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/20' :
                  'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                }`}>
                  {candidate.matchScore}% match
                </span>
              </div>

              {/* BIO SNIPPET */}
              <p className="text-xs text-slate-400 line-clamp-2 leading-relaxed">
                {candidate.summary}
              </p>

              {/* MATCH INTELLIGENCE */}
              <div className="space-y-2">
                {/* Experience Years */}
                {candidate.experienceYears && (
                  <div className="flex items-center gap-2 text-[10px] text-slate-400">
                    <Briefcase size={12} className="text-slate-500" />
                    <span>{candidate.experienceYears.toFixed(1)} years experience</span>
                  </div>
                )}

                {/* Matched Skills */}
                {candidate.matchedSkills && candidate.matchedSkills.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {candidate.matchedSkills.slice(0, 4).map(skill => (
                      <span
                        key={skill}
                        className="px-2 py-0.5 rounded-md bg-brand-600/10 border border-brand-500/20 text-[9px] text-brand-400 font-semibold"
                      >
                        {skill}
                      </span>
                    ))}
                    {candidate.matchedSkills.length > 4 && (
                      <span className="px-2 py-0.5 rounded-md bg-slate-900 border border-dark-border text-[9px] text-slate-500">
                        +{candidate.matchedSkills.length - 4} more
                      </span>
                    )}
                  </div>
                )}

                {/* Matched Technologies */}
                {candidate.matchedTechnologies && candidate.matchedTechnologies.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {candidate.matchedTechnologies.slice(0, 3).map(tech => (
                      <span
                        key={tech}
                        className="px-2 py-0.5 rounded-md bg-indigo-600/10 border border-indigo-500/20 text-[9px] text-indigo-400 font-semibold"
                      >
                        {tech}
                      </span>
                    ))}
                    {candidate.matchedTechnologies.length > 3 && (
                      <span className="px-2 py-0.5 rounded-md bg-slate-900 border border-dark-border text-[9px] text-slate-500">
                        +{candidate.matchedTechnologies.length - 3} more
                      </span>
                    )}
                  </div>
                )}

                {/* Matched Projects */}
                {candidate.matchedProjects && candidate.matchedProjects.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {candidate.matchedProjects.slice(0, 2).map(project => (
                      <span
                        key={project}
                        className="px-2 py-0.5 rounded-md bg-amber-600/10 border border-amber-500/20 text-[9px] text-amber-400 font-semibold"
                      >
                        {project}
                      </span>
                    ))}
                    {candidate.matchedProjects.length > 2 && (
                      <span className="px-2 py-0.5 rounded-md bg-slate-900 border border-dark-border text-[9px] text-slate-500">
                        +{candidate.matchedProjects.length - 2} more
                      </span>
                    )}
                  </div>
                )}
              </div>

              {/* HIGHLIGHTED PARAMETERS */}
              <div className="grid grid-cols-2 gap-2 border-t border-b border-dark-border/40 py-3 text-[10px] text-slate-400">
                <div className="flex items-center gap-1.5">
                  <MapPin size={12} className="text-slate-500" />
                  <span>{candidate.location}</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <GraduationCap size={12} className="text-slate-500" />
                  <span>{candidate.education[0]?.school?.split('University')[0].trim() || 'Education not specified'}</span>
                </div>
              </div>

              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Match intelligence</span>
                  <span className="text-[10px] text-slate-500">
                    {candidate.experienceYears != null ? `${candidate.experienceYears} years experience` : 'Experience not specified'}
                  </span>
                </div>

                <div className="flex flex-wrap gap-1.5">
                  {[
                    { label: 'Role', matched: candidate.matchBreakdown?.role_match },
                    { label: 'Experience', matched: candidate.matchBreakdown?.experience_match },
                    { label: 'Skills', matched: candidate.matchBreakdown?.skill_match },
                    { label: 'Technologies', matched: candidate.matchBreakdown?.technology_match },
                    { label: 'Projects', matched: candidate.matchBreakdown?.project_match },
                  ].map(({ label, matched }) => (
                    <span
                      key={label}
                      className={`inline-flex items-center gap-1 rounded-md border px-2 py-1 text-[9px] font-semibold ${
                        matched ? 'border-emerald-500/20 bg-emerald-500/10 text-emerald-400' : 'border-dark-border bg-slate-950 text-slate-500'
                      }`}
                    >
                      {matched ? <Check size={10} /> : <X size={10} />}
                      {label}
                    </span>
                  ))}
                </div>

                {[
                  { label: 'Skills', values: candidate.matchedSkills || candidate.skills, colorClass: 'bg-slate-900' },
                  { label: 'Technologies', values: candidate.matchedTechnologies || candidate.technologies || [], colorClass: 'bg-brand-600/10' },
                  { label: 'Projects', values: candidate.matchedProjects || candidate.projects || [], colorClass: 'bg-emerald-500/10' },
                ].map(({ label, values, colorClass }) => {
                  const items = values;
                  return items.length > 0 ? (
                    <div key={label} className="space-y-1">
                      <span className="text-[9px] font-semibold uppercase tracking-wider text-slate-500">Matched {label}</span>
                      <div className="flex flex-wrap gap-1.5">
                        {items.map((item) => (
                          <span key={item} className={`rounded-md border border-dark-border px-2 py-0.5 text-[9px] font-semibold text-slate-300 ${colorClass}`}>
                            {item}
                          </span>
                        ))}
                      </div>
                    </div>
                  ) : null;
                })}

                {candidate.matchExplanation && (
                  <p className="border-l-2 border-brand-500/40 pl-2 text-[10px] leading-relaxed text-slate-400">
                    {candidate.matchExplanation}
                  </p>
                )}
              </div>

              {/* ACTIONS FOOTER */}
              <div className="pt-2 flex items-center justify-between border-t border-dark-border/40">
                <span className="text-[10px] text-slate-500 flex items-center gap-1">
                  <GitFork size={12} className="text-brand-500" />
                  {candidate.relationshipCount} graph associations
                </span>
                
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => navigate(`/candidate/${candidate.id}?query=${encodeURIComponent(queryParam)}&matchScore=${candidate.matchScore}`)}
                    className="bg-brand-600/10 hover:bg-brand-600/20 text-brand-500 font-semibold text-[11px] py-1.5 px-3 rounded-lg border border-brand-500/20 flex items-center gap-1 transition-all duration-200"
                  >
                    <User size={12} />
                    <span>View Profile</span>
                  </button>
                  <button
                    onClick={() => navigate(`/graph?id=${candidate.id}`)}
                    className="p-1.5 text-slate-400 hover:text-white bg-slate-900 border border-dark-border hover:bg-slate-800 rounded-lg inline-flex"
                  >
                    <ChevronRight size={14} />
                  </button>
                </div>
              </div>

            </div>
          ))}
        </div>
      ) : (
        // EMPTY STATE VIEW
        <div className="glass-panel rounded-2xl p-12 text-center max-w-md mx-auto space-y-4 border border-dark-border">
          <div className="w-16 h-16 rounded-full bg-slate-900 border border-dark-border flex items-center justify-center text-slate-500 mx-auto">
            <FilterX size={28} />
          </div>
          <div className="space-y-1.5">
            <h3 className="text-base font-bold text-white">No matching candidates found</h3>
            <p className="text-xs text-slate-400">
              No candidates meet your current search query or active filter settings. Try relaxing your constraints.
            </p>
          </div>
          <button
            onClick={handleResetFilters}
            className="bg-brand-600 hover:bg-brand-700 text-white font-semibold text-xs py-2 px-5 rounded-xl shadow-md transition-colors"
          >
            Clear Filters & Search
          </button>
        </div>
      )}

    </div>
  );
};

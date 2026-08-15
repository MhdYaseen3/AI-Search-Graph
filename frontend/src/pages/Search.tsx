import React, { useState, useEffect } from 'react';
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
  FilterX
} from 'lucide-react';
import { resumeService } from '../services/api';
import type { Candidate } from '../types';

export const Search: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const queryParam = searchParams.get('q') || '';

  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [filteredCandidates, setFilteredCandidates] = useState<Candidate[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchVal, setSearchVal] = useState(queryParam);
  const [showFilters, setShowFilters] = useState(false);

  // Filters State
  const [minScore, setMinScore] = useState<number>(70);
  const [selectedSkill, setSelectedSkill] = useState<string>('');
  const [selectedLocation, setSelectedLocation] = useState<string>('');

  // Aggregated metadata for filter values
  const [allSkills, setAllSkills] = useState<string[]>([]);
  const [allLocations, setAllLocations] = useState<string[]>([]);

  useEffect(() => {
    setSearchVal(queryParam);
    fetchSearchResults();
  }, [queryParam]);

  const fetchSearchResults = async () => {
    setLoading(true);
    try {
      const results = await resumeService.searchCandidates(queryParam);
      setCandidates(results);
      
      // Extract unique skills & locations for filters from the returned dataset
      const skillsSet = new Set<string>();
      const locationsSet = new Set<string>();
      results.forEach(c => {
        c.skills.forEach(s => skillsSet.add(s));
        if (c.location) locationsSet.add(c.location.split(',')[0].trim());
      });
      setAllSkills(Array.from(skillsSet));
      setAllLocations(Array.from(locationsSet));
    } catch (err) {
      console.error('Search error', err);
    } finally {
      setLoading(false);
    }
  };

  // Run filtering logic client-side on fetched results
  useEffect(() => {
    let temp = [...candidates];

    // Filter by min score
    temp = temp.filter(c => c.matchScore >= minScore);

    // Filter by skill
    if (selectedSkill) {
      temp = temp.filter(c => c.skills.includes(selectedSkill));
    }

    // Filter by location
    if (selectedLocation) {
      temp = temp.filter(c => c.location.toLowerCase().includes(selectedLocation.toLowerCase()));
    }

    setFilteredCandidates(temp);
  }, [candidates, minScore, selectedSkill, selectedLocation]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setSearchParams(searchVal ? { q: searchVal } : {});
  };

  const handleResetFilters = () => {
    setMinScore(70);
    setSelectedSkill('');
    setSelectedLocation('');
    setSearchVal('');
    setSearchParams({});
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      
      {/* SEARCH AND FILTER HEAD BAR */}
      <div className="flex flex-col md:flex-row gap-3 items-center justify-between">
        <form onSubmit={handleSearchSubmit} className="w-full md:max-w-xl flex items-center gap-2">
          <div className="relative flex-1">
            <SearchIcon className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500" size={18} />
            <input
              type="text"
              placeholder="Search skills, companies, names..."
              value={searchVal}
              onChange={(e) => setSearchVal(e.target.value)}
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
            showFilters || selectedSkill || selectedLocation || minScore > 70
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
              min="50"
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

              {/* HIGHLIGHTED PARAMETERS */}
              <div className="grid grid-cols-2 gap-2 border-t border-b border-dark-border/40 py-3 text-[10px] text-slate-400">
                <div className="flex items-center gap-1.5">
                  <MapPin size={12} className="text-slate-500" />
                  <span>{candidate.location}</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <GraduationCap size={12} className="text-slate-500" />
                  <span>{candidate.education[0]?.school.split('University')[0].trim()}</span>
                </div>
              </div>

              {/* SKILLS CHIPS */}
              <div className="flex flex-wrap gap-1.5">
                {candidate.skills.slice(0, 4).map(s => (
                  <span 
                    key={s} 
                    className="px-2 py-0.5 rounded-md bg-slate-900 border border-dark-border text-[9px] text-slate-300 font-semibold"
                  >
                    {s}
                  </span>
                ))}
                {candidate.skills.length > 4 && (
                  <span className="px-2 py-0.5 rounded-md bg-slate-950 border border-dark-border/40 text-[9px] text-slate-500">
                    +{candidate.skills.length - 4} more
                  </span>
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
                    onClick={() => navigate(`/candidate/${candidate.id}`)}
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

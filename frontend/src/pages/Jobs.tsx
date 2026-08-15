import React, { useState, useEffect } from 'react';
import {
  Search as SearchIcon,
  Plus,
  Filter,
  X,
  Briefcase,
  MapPin,
  DollarSign,
  TrendingUp,
  ChevronRight,
  Award,
  Calendar,
  AlertCircle
} from 'lucide-react';
import { jobService } from '../services/api';
import type { Job, CreateJobInput, JobStatus, EmploymentType } from '../types';
import { CreateJobForm } from '../components/CreateJobForm';

export const Jobs: React.FC = () => {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [filteredJobs, setFilteredJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<JobStatus | 'All'>('All');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchJobs();
  }, []);

  const fetchJobs = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await jobService.getAllJobs();
      setJobs(data);
    } catch (err) {
      console.error('Failed to load jobs', err);
      setError('Failed to load jobs. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  // Apply filters client-side
  useEffect(() => {
    let filtered = [...jobs];

    // Filter by status
    if (statusFilter !== 'All') {
      filtered = filtered.filter(job => job.status === statusFilter);
    }

    // Filter by search query
    if (searchQuery.trim()) {
      const lowerQuery = searchQuery.toLowerCase();
      filtered = filtered.filter(job =>
        job.title.toLowerCase().includes(lowerQuery) ||
        job.description.toLowerCase().includes(lowerQuery) ||
        job.requiredSkills.some(s => s.toLowerCase().includes(lowerQuery)) ||
        job.location.toLowerCase().includes(lowerQuery)
      );
    }

    setFilteredJobs(filtered);
  }, [jobs, statusFilter, searchQuery]);

  const handleCreateJob = async (input: CreateJobInput) => {
    try {
      const newJob = await jobService.createJob(input);
      setJobs(prev => [newJob, ...prev]);
      setShowCreateModal(false);
      setError(null);
    } catch (err) {
      console.error('Failed to create job', err);
      setError('Failed to create job. Please try again.');
    }
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // Search is handled by useEffect with searchQuery state
  };

  const formatSalary = (salary?: Job['salary']) => {
    if (!salary) return 'Not specified';
    if (salary.min && salary.max) {
      return `${salary.currency} ${salary.min.toLocaleString()} - ${salary.max.toLocaleString()}`;
    }
    if (salary.min) return `${salary.currency} ${salary.min.toLocaleString()}+`;
    if (salary.max) return `Up to ${salary.currency} ${salary.max.toLocaleString()}`;
    return 'Not specified';
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays} days ago`;
    if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
    return `${Math.floor(diffDays / 30)} months ago`;
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* HERO SECTION WITH TITLE AND ACTIONS */}
      <section className="relative overflow-hidden rounded-3xl border border-dark-border bg-gradient-to-r from-dark-card via-slate-900 to-brand-950/20 p-8 md:p-10 glow-purple">
        <div className="absolute top-0 right-0 w-80 h-80 bg-brand-500/10 rounded-full blur-[80px] pointer-events-none" />
        <div className="max-w-2xl space-y-4">
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-brand-500/10 text-xs font-semibold text-brand-500">
            <Briefcase size={12} className="fill-brand-500" />
            Job Management Portal
          </span>
          <h2 className="text-2xl md:text-4xl font-extrabold text-white tracking-tight leading-tight">
            Manage open positions and track job postings.
          </h2>
          <p className="text-sm md:text-base text-slate-400">
            Create and manage job listings. Search through open positions and filter by status to stay organized.
          </p>

          <button
            onClick={() => setShowCreateModal(true)}
            className="mt-4 inline-flex items-center gap-2 bg-brand-600 hover:bg-brand-700 text-white font-semibold text-sm px-6 py-3 rounded-xl shadow-lg transition-all duration-200"
          >
            <Plus size={18} />
            Create New Job
          </button>
        </div>
      </section>

      {/* ERROR MESSAGE */}
      {error && (
        <div className="flex items-center gap-3 px-4 py-3 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
          <AlertCircle size={16} />
          <span>{error}</span>
          <button
            onClick={() => setError(null)}
            className="ml-auto p-1 hover:bg-red-500/20 rounded"
          >
            <X size={16} />
          </button>
        </div>
      )}

      {/* SEARCH AND FILTER BAR */}
      <div className="flex flex-col md:flex-row gap-3 items-center justify-between">
        <form onSubmit={handleSearchSubmit} className="w-full md:max-w-xl flex items-center gap-2">
          <div className="relative flex-1">
            <SearchIcon className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500" size={18} />
            <input
              type="text"
              placeholder="Search jobs by title, skills, location..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
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

        {/* STATUS FILTER BUTTONS */}
        <div className="flex items-center gap-2 w-full md:w-auto">
          <button
            onClick={() => setStatusFilter('All')}
            className={`flex items-center gap-2 px-4 py-3 rounded-xl border text-sm font-semibold transition-colors ${
              statusFilter === 'All'
                ? 'bg-brand-600/20 border-brand-500/30 text-brand-500'
                : 'bg-slate-900 border-dark-border text-slate-300 hover:bg-slate-800'
            }`}
          >
            <Filter size={16} />
            All
          </button>
          <button
            onClick={() => setStatusFilter('Active')}
            className={`px-4 py-3 rounded-xl border text-sm font-semibold transition-colors ${
              statusFilter === 'Active'
                ? 'bg-emerald-600/20 border-emerald-500/30 text-emerald-400'
                : 'bg-slate-900 border-dark-border text-slate-300 hover:bg-slate-800'
            }`}
          >
            <span className="inline-flex items-center gap-1.5">
              <span className="w-2 h-2 bg-emerald-500 rounded-full"></span>
              Active
            </span>
          </button>
          <button
            onClick={() => setStatusFilter('Closed')}
            className={`px-4 py-3 rounded-xl border text-sm font-semibold transition-colors ${
              statusFilter === 'Closed'
                ? 'bg-slate-600/20 border-slate-500/30 text-slate-300'
                : 'bg-slate-900 border-dark-border text-slate-300 hover:bg-slate-800'
            }`}
          >
            <span className="inline-flex items-center gap-1.5">
              <span className="w-2 h-2 bg-slate-500 rounded-full"></span>
              Closed
            </span>
          </button>
        </div>
      </div>

      {/* JOBS LIST */}
      <div className="space-y-3">
        {loading ? (
          <div className="flex items-center justify-center py-16">
            <div className="space-y-3 w-full max-w-2xl">
              {[...Array(3)].map((_, i) => (
                <div
                  key={i}
                  className="h-32 bg-slate-900 border border-dark-border rounded-2xl animate-pulse"
                />
              ))}
            </div>
          </div>
        ) : filteredJobs.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 px-4">
            <Briefcase size={48} className="text-slate-600 mb-4" />
            <h3 className="text-lg font-semibold text-slate-300 mb-2">No jobs found</h3>
            <p className="text-sm text-slate-500 text-center max-w-md">
              {searchQuery ? 'Try adjusting your search filters.' : 'Create a new job posting to get started.'}
            </p>
            {!searchQuery && (
              <button
                onClick={() => setShowCreateModal(true)}
                className="mt-4 inline-flex items-center gap-2 bg-brand-600 hover:bg-brand-700 text-white font-semibold text-sm px-4 py-2 rounded-lg transition-colors"
              >
                <Plus size={16} />
                Create Job
              </button>
            )}
          </div>
        ) : (
          filteredJobs.map((job) => (
            <JobCard key={job.id} job={job} formatSalary={formatSalary} formatDate={formatDate} />
          ))
        )}
      </div>

      {/* STATS FOOTER */}
      {!loading && filteredJobs.length > 0 && (
        <div className="flex items-center justify-between px-4 py-3 rounded-xl bg-slate-900 border border-dark-border text-sm text-slate-400">
          <span>
            Showing <span className="font-semibold text-slate-200">{filteredJobs.length}</span> of{' '}
            <span className="font-semibold text-slate-200">{jobs.length}</span> jobs
          </span>
          <div className="flex gap-6">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 bg-emerald-500 rounded-full"></span>
              <span>
                <span className="font-semibold text-emerald-400">
                  {jobs.filter(j => j.status === 'Active').length}
                </span>{' '}
                Active
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 bg-slate-500 rounded-full"></span>
              <span>
                <span className="font-semibold text-slate-300">
                  {jobs.filter(j => j.status === 'Closed').length}
                </span>{' '}
                Closed
              </span>
            </div>
          </div>
        </div>
      )}

      {/* CREATE JOB MODAL */}
      {showCreateModal && (
        <CreateJobFormModal
          onClose={() => setShowCreateModal(false)}
          onSubmit={handleCreateJob}
        />
      )}
    </div>
  );
};

// Job Card Component
interface JobCardProps {
  job: Job;
  formatSalary: (salary?: Job['salary']) => string;
  formatDate: (dateString: string) => string;
}

const JobCard: React.FC<JobCardProps> = ({ job, formatSalary, formatDate }) => {
  const statusConfig = {
    Active: {
      bg: 'bg-emerald-500/10',
      border: 'border-emerald-500/30',
      text: 'text-emerald-400',
      dot: 'bg-emerald-500'
    },
    Closed: {
      bg: 'bg-slate-600/10',
      border: 'border-slate-500/30',
      text: 'text-slate-400',
      dot: 'bg-slate-500'
    }
  };

  const config = statusConfig[job.status];

  return (
    <div className="group relative overflow-hidden rounded-2xl border border-dark-border bg-dark-card/60 hover:bg-dark-card transition-all duration-200 p-6 hover:border-brand-500/30">
      <div className="absolute inset-0 bg-gradient-to-r from-brand-600/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none" />

      <div className="relative space-y-4">
        {/* Header */}
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 space-y-2">
            <div className="flex items-center gap-2">
              <h3 className="text-lg font-bold text-white group-hover:text-brand-400 transition-colors">
                {job.title}
              </h3>
              <span className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-lg text-xs font-semibold ${config.bg} ${config.text}`}>
                <span className={`w-1.5 h-1.5 ${config.dot} rounded-full`}></span>
                {job.status}
              </span>
            </div>
            <p className="text-sm text-slate-400 line-clamp-2">{job.description}</p>
          </div>
          <ChevronRight className="w-5 h-5 text-slate-600 group-hover:text-brand-500 transition-colors mt-1 shrink-0" />
        </div>

        {/* Info Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <InfoItem icon={MapPin} label={job.location} />
          <InfoItem icon={Award} label={`${job.experience}+ years`} />
          <InfoItem icon={DollarSign} label={formatSalary(job.salary)} />
          <InfoItem icon={Briefcase} label={job.employmentType} />
        </div>

        {/* Skills Tags */}
        <div className="flex flex-wrap gap-2">
          {job.requiredSkills.slice(0, 5).map((skill) => (
            <span
              key={skill}
              className="inline-flex items-center px-2.5 py-1 rounded-lg bg-brand-600/15 text-brand-400 text-xs font-medium border border-brand-500/20"
            >
              {skill}
            </span>
          ))}
          {job.requiredSkills.length > 5 && (
            <span className="inline-flex items-center px-2.5 py-1 rounded-lg bg-slate-800 text-slate-400 text-xs font-medium">
              +{job.requiredSkills.length - 5} more
            </span>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between pt-2 border-t border-dark-border/50">
          <span className="text-xs text-slate-500 flex items-center gap-1">
            <Calendar size={12} />
            Posted {formatDate(job.createdAt)}
          </span>
          <button className="text-brand-500 hover:text-brand-400 text-xs font-semibold transition-colors">
            View Details →
          </button>
        </div>
      </div>
    </div>
  );
};

// Info Item Component
interface InfoItemProps {
  icon: React.ComponentType<{ size: number; className?: string }>;
  label: string;
}

const InfoItem: React.FC<InfoItemProps> = ({ icon: Icon, label }) => (
  <div className="flex items-center gap-2 text-sm">
    <Icon size={16} className="text-brand-500 shrink-0" />
    <span className="text-slate-300">{label}</span>
  </div>
);

// Create Job Form Modal
interface CreateJobFormModalProps {
  onClose: () => void;
  onSubmit: (input: CreateJobInput) => Promise<void>;
}

const CreateJobFormModal: React.FC<CreateJobFormModalProps> = ({ onClose, onSubmit }) => {
  const [isSubmitting, setIsSubmitting] = useState(false);

  return (
    <div className="fixed inset-0 z-50 flex items-end md:items-center justify-center p-4 md:p-0 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-t-3xl md:rounded-3xl bg-dark-bg border border-dark-border animate-in slide-in-from-bottom-5 md:scale-in duration-300">
        <div className="sticky top-0 flex items-center justify-between px-6 py-4 border-b border-dark-border/60 bg-dark-card/80 backdrop-blur-md">
          <h2 className="text-xl font-bold text-white">Create New Job</h2>
          <button
            onClick={onClose}
            className="p-2 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800/50 transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        <div className="p-6">
          <CreateJobForm
            onSubmit={async (input) => {
              setIsSubmitting(true);
              try {
                await onSubmit(input);
                onClose();
              } finally {
                setIsSubmitting(false);
              }
            }}
            isSubmitting={isSubmitting}
            onCancel={onClose}
          />
        </div>
      </div>
    </div>
  );
};

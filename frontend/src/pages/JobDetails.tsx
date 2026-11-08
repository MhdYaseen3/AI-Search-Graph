import React, { useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import {
  ArrowLeft,
  Briefcase,
  Check,
  Edit3,
  MapPin,
  Sparkles,
  UserPlus,
} from 'lucide-react';
import { CreateJobForm } from '../components/CreateJobForm';
import { jobService } from '../services/api';
import type {
  CandidateOption,
  CreateJobInput,
  Job,
  JobApplication,
  JobApplicationStatus,
  JobMatchCandidate,
} from '../types';

const APPLICATION_STATUSES: JobApplicationStatus[] = [
  'Applied',
  'Shortlisted',
  'Interview',
  'Selected',
  'Rejected',
];

const salaryLabel = (salary: Job['salary']) => {
  if (!salary) return 'Not specified';
  if (typeof salary === 'string') return salary;
  const { min, max, currency } = salary;
  if (min !== undefined && max !== undefined) {
    return `${currency} ${min.toLocaleString()} - ${max.toLocaleString()}`;
  }
  if (min !== undefined) return `${currency} ${min.toLocaleString()}+`;
  if (max !== undefined) return `Up to ${currency} ${max.toLocaleString()}`;
  return 'Not specified';
};

const editableJob = (job: Job): CreateJobInput => ({
  title: job.title,
  description: job.description,
  requiredSkills: job.requiredSkills,
  experience: job.experience,
  location: job.location,
  employmentType: job.employmentType,
  salary: typeof job.salary === 'string' ? undefined : job.salary,
  status: job.status,
});

export const JobDetails: React.FC = () => {
  const { jobId = '' } = useParams();
  const [job, setJob] = useState<Job | null>(null);
  const [applicants, setApplicants] = useState<JobApplication[]>([]);
  const [candidateOptions, setCandidateOptions] = useState<CandidateOption[]>([]);
  const [matches, setMatches] = useState<JobMatchCandidate[]>([]);
  const [hasRunMatching, setHasRunMatching] = useState(false);
  const [applicationFilter, setApplicationFilter] = useState<'All' | JobApplicationStatus>('All');
  const [selectedCandidate, setSelectedCandidate] = useState('');
  const [loading, setLoading] = useState(true);
  const [matching, setMatching] = useState(false);
  const [saving, setSaving] = useState(false);
  const [editing, setEditing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    Promise.all([
      jobService.getJobById(jobId),
      jobService.getApplicants(jobId),
      jobService.getCandidates(),
    ]).then(([jobRecord, applicationRecords, candidates]) => {
      if (!active) return;
      setJob(jobRecord);
      setApplicants(applicationRecords);
      setCandidateOptions(candidates);
    }).catch((loadError: unknown) => {
      if (active) {
        setError(loadError instanceof Error ? loadError.message : 'Unable to load job details.');
      }
    }).finally(() => {
      if (active) setLoading(false);
    });
    return () => {
      active = false;
    };
  }, [jobId]);

  const filteredApplicants = useMemo(
    () => applicationFilter === 'All'
      ? applicants
      : applicants.filter((application) => application.status === applicationFilter),
    [applicants, applicationFilter],
  );
  const applicantIds = useMemo(
    () => new Set(applicants.map((application) => application.candidate_id)),
    [applicants],
  );

  const saveJob = async (input: CreateJobInput) => {
    setSaving(true);
    try {
      const updated = await jobService.updateJob(jobId, input);
      setJob(updated);
      setEditing(false);
      setNotice('Job details saved.');
    } catch (saveError: unknown) {
      setError(saveError instanceof Error ? saveError.message : 'Unable to save job.');
      throw saveError;
    } finally {
      setSaving(false);
    }
  };

  const changeJobStatus = async (status: Job['status']) => {
    if (!job) return;
    setSaving(true);
    setError(null);
    try {
      setJob(await jobService.updateJob(job.id, { status }));
      setNotice(`Job ${status === 'Closed' ? 'closed' : 'reopened'}.`);
    } catch (statusError: unknown) {
      setError(statusError instanceof Error ? statusError.message : 'Unable to update job status.');
    } finally {
      setSaving(false);
    }
  };

  const runMatching = async () => {
    setMatching(true);
    setError(null);
    setNotice(null);
    try {
      setMatches(await jobService.matchCandidates(jobId));
      setHasRunMatching(true);
    } catch (matchError: unknown) {
      setError(matchError instanceof Error ? matchError.message : 'Candidate matching failed.');
    } finally {
      setMatching(false);
    }
  };

  const addApplicant = async (candidateId: string) => {
    setError(null);
    setNotice(null);
    try {
      const application = await jobService.addApplicant(jobId, candidateId);
      setApplicants((current) => current.some((item) => item.candidate_id === candidateId)
        ? current.map((item) => item.candidate_id === candidateId ? application : item)
        : [application, ...current]);
      setSelectedCandidate('');
      setNotice(`${application.full_name} is associated with this job.`);
    } catch (applicationError: unknown) {
      setError(applicationError instanceof Error ? applicationError.message : 'Unable to associate candidate.');
    }
  };

  const updateStage = async (candidateId: string, status: JobApplicationStatus) => {
    try {
      const updated = await jobService.updateApplicantStatus(jobId, candidateId, status);
      setApplicants((current) => current.map((item) => (
        item.candidate_id === candidateId ? updated : item
      )));
    } catch (stageError: unknown) {
      setError(stageError instanceof Error ? stageError.message : 'Unable to update applicant stage.');
    }
  };

  if (loading) {
    return <div className="p-8 text-slate-400">Loading job details…</div>;
  }
  if (!job) {
    return (
      <section className="space-y-4 rounded-2xl border border-dark-border bg-dark-card p-8">
        <p className="text-rose-400">{error || 'Job not found.'}</p>
        <Link to="/jobs" className="text-brand-400 hover:text-brand-300">Back to Jobs</Link>
      </section>
    );
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      <Link to="/jobs" className="inline-flex items-center gap-2 text-sm text-slate-400 hover:text-white">
        <ArrowLeft size={16} /> Back to Jobs
      </Link>

      {error && <div role="alert" className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-300">{error}</div>}
      {notice && <div role="status" className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-4 text-sm text-emerald-300">{notice}</div>}

      <section className="rounded-3xl border border-dark-border bg-gradient-to-br from-dark-card to-slate-900 p-6 md:p-8">
        <div className="flex flex-col gap-5 md:flex-row md:items-start md:justify-between">
          <div className="space-y-4">
            <div className="flex flex-wrap items-center gap-3">
              <h1 className="text-2xl font-bold text-white md:text-3xl">{job.title}</h1>
              <span className={`rounded-full px-3 py-1 text-xs font-semibold ${job.status === 'Active' ? 'bg-emerald-500/10 text-emerald-300' : 'bg-slate-700 text-slate-300'}`}>
                {job.status}
              </span>
            </div>
            <p className="max-w-4xl whitespace-pre-wrap text-sm leading-6 text-slate-300">{job.description}</p>
            <div className="flex flex-wrap gap-2">
              {job.requiredSkills.map((skill) => (
                <span key={skill} className="rounded-lg border border-brand-500/20 bg-brand-500/10 px-2.5 py-1 text-xs text-brand-300">{skill}</span>
              ))}
            </div>
          </div>
          <div className="flex shrink-0 flex-wrap gap-2">
            <button onClick={() => setEditing(true)} className="inline-flex items-center gap-2 rounded-xl border border-dark-border bg-slate-900 px-4 py-2.5 text-sm text-white hover:border-brand-500/50">
              <Edit3 size={16} /> Edit Job
            </button>
            <button disabled={saving} onClick={() => void changeJobStatus(job.status === 'Active' ? 'Closed' : 'Active')} className="rounded-xl bg-slate-800 px-4 py-2.5 text-sm font-semibold text-slate-200 hover:bg-slate-700 disabled:opacity-50">
              {job.status === 'Active' ? 'Close Job' : 'Reopen Job'}
            </button>
          </div>
        </div>

        <div className="mt-7 grid gap-3 border-t border-dark-border pt-6 sm:grid-cols-2 lg:grid-cols-4">
          <DetailItem label="Experience" value={`${job.experience}+ years`} icon={<Briefcase size={16} />} />
          <DetailItem label="Location" value={job.location} icon={<MapPin size={16} />} />
          <DetailItem label="Employment Type" value={job.employmentType} icon={<Briefcase size={16} />} />
          <DetailItem label="Salary" value={salaryLabel(job.salary)} icon={<span className="font-bold">$</span>} />
        </div>
      </section>

      <section className="rounded-2xl border border-dark-border bg-dark-card p-5 md:p-6">
        <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
          <div>
            <h2 className="text-lg font-bold text-white">AI Candidate Matching</h2>
            <p className="mt-1 text-sm text-slate-400">Rank saved candidates using required skills, experience, projects, and profile relevance.</p>
          </div>
          <button onClick={() => void runMatching()} disabled={matching} className="inline-flex items-center justify-center gap-2 rounded-xl bg-brand-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-brand-500 disabled:opacity-50">
            <Sparkles size={16} /> {matching ? 'Finding matches…' : 'AI Find Matching Candidates'}
          </button>
        </div>
        {hasRunMatching && matches.length === 0 && (
          <p className="mt-5 rounded-xl border border-dashed border-dark-border p-6 text-center text-sm text-slate-400">No candidates were found.</p>
        )}
        {matches.length > 0 && (
          <div className="mt-5 space-y-3">
            {matches.map((candidate) => (
              <article key={candidate.candidate_id} className="rounded-xl border border-dark-border bg-slate-950/40 p-4">
                <div className="flex flex-col justify-between gap-3 md:flex-row md:items-start">
                  <div>
                    <Link to={`/candidate/${candidate.candidate_id}`} className="font-semibold text-white hover:text-brand-300">{candidate.full_name}</Link>
                    <p className="mt-1 text-xs text-slate-400">{candidate.experience_years ?? candidate.experience} years experience</p>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="rounded-lg bg-brand-500/10 px-3 py-1.5 text-sm font-bold text-brand-300">{Math.round(candidate.match_score)}% match</span>
                    <button disabled={applicantIds.has(candidate.candidate_id)} onClick={() => void addApplicant(candidate.candidate_id)} className="inline-flex items-center gap-1.5 rounded-lg border border-dark-border px-3 py-1.5 text-xs text-slate-200 hover:border-brand-500/50 disabled:opacity-50">
                      {applicantIds.has(candidate.candidate_id) ? <Check size={14} /> : <UserPlus size={14} />}
                      {applicantIds.has(candidate.candidate_id) ? 'Associated' : 'Associate'}
                    </button>
                  </div>
                </div>
                <MatchEvidence label="Matched skills" values={candidate.matched_skills} empty="No required skills matched" />
                <MatchEvidence label="Missing skills" values={candidate.missing_skills} empty="None" />
                {candidate.matched_projects.length > 0 && <MatchEvidence label="Relevant projects" values={candidate.matched_projects} empty="" />}
                {candidate.missing_projects.length > 0 && <MatchEvidence label="Unmatched project criteria" values={candidate.missing_projects} empty="" />}
                <p className="mt-3 text-xs leading-5 text-slate-400">{candidate.explanation || candidate.ai_explanation || candidate.summary || 'Profile ranked against this job.'}</p>
              </article>
            ))}
          </div>
        )}
        {!hasRunMatching && <p className="mt-4 text-xs text-slate-500">Run matching to view candidate scores and evidence.</p>}
      </section>

      <section className="space-y-4 rounded-2xl border border-dark-border bg-dark-card p-5 md:p-6">
        <div className="flex flex-col justify-between gap-3 md:flex-row md:items-center">
          <div>
            <h2 className="text-lg font-bold text-white">Applicants</h2>
            <p className="mt-1 text-sm text-slate-400">{applicants.length} candidate{applicants.length === 1 ? '' : 's'} associated with this position</p>
          </div>
          <div className="flex gap-2">
            <select aria-label="Select candidate to associate" value={selectedCandidate} onChange={(event) => setSelectedCandidate(event.target.value)} className="max-w-xs rounded-xl border border-dark-border bg-slate-950 px-3 py-2 text-sm text-white">
              <option value="">Choose candidate…</option>
              {candidateOptions.filter((candidate) => !applicantIds.has(candidate.id)).map((candidate) => (
                <option key={candidate.id} value={candidate.id}>{candidate.full_name}{candidate.email ? ` · ${candidate.email}` : ''}</option>
              ))}
            </select>
            <button disabled={!selectedCandidate} onClick={() => void addApplicant(selectedCandidate)} className="inline-flex items-center gap-2 rounded-xl bg-brand-600 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50">
              <UserPlus size={15} /> Associate
            </button>
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          {(['All', ...APPLICATION_STATUSES] as const).map((status) => (
            <button key={status} onClick={() => setApplicationFilter(status)} className={`rounded-lg border px-3 py-1.5 text-xs font-medium ${applicationFilter === status ? 'border-brand-500/40 bg-brand-500/10 text-brand-300' : 'border-dark-border text-slate-400 hover:text-white'}`}>
              {status}
            </button>
          ))}
        </div>

        {filteredApplicants.length === 0 ? (
          <p className="rounded-xl border border-dashed border-dark-border p-8 text-center text-sm text-slate-500">No applicants in this stage yet.</p>
        ) : (
          <div className="space-y-2">
            {filteredApplicants.map((applicant) => (
              <article key={applicant.id} className="flex flex-col justify-between gap-3 rounded-xl border border-dark-border bg-slate-950/30 p-4 md:flex-row md:items-center">
                <div>
                  <Link to={`/candidate/${applicant.candidate_id}`} className="font-semibold text-white hover:text-brand-300">{applicant.full_name}</Link>
                  <p className="mt-1 text-xs text-slate-400">{applicant.email || 'Email not provided'}</p>
                </div>
                <select aria-label={`Recruitment stage for ${applicant.full_name}`} value={applicant.status} onChange={(event) => void updateStage(applicant.candidate_id, event.target.value as JobApplicationStatus)} className="rounded-lg border border-dark-border bg-slate-900 px-3 py-2 text-sm text-slate-200">
                  {APPLICATION_STATUSES.map((status) => <option key={status} value={status}>{status}</option>)}
                </select>
              </article>
            ))}
          </div>
        )}
      </section>

      {editing && (
        <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/70 p-4 md:items-center">
          <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-2xl border border-dark-border bg-dark-bg p-5">
            <h2 className="mb-5 text-xl font-bold text-white">Edit Job</h2>
            <CreateJobForm initialValue={editableJob(job)} onSubmit={saveJob} isSubmitting={saving} onCancel={() => setEditing(false)} />
          </div>
        </div>
      )}
    </div>
  );
};

const DetailItem: React.FC<{ label: string; value: string; icon: React.ReactNode }> = ({ label, value, icon }) => (
  <div className="rounded-xl border border-dark-border bg-slate-950/30 p-4">
    <div className="flex items-center gap-2 text-brand-400">{icon}<span className="text-xs text-slate-500">{label}</span></div>
    <p className="mt-2 text-sm font-medium text-slate-200">{value}</p>
  </div>
);

const MatchEvidence: React.FC<{ label: string; values: string[]; empty: string }> = ({ label, values, empty }) => (
  <div className="mt-3 flex flex-wrap items-center gap-1.5">
    <span className="mr-1 text-xs text-slate-500">{label}:</span>
    {values.length > 0
      ? values.map((value) => <span key={value} className="rounded-md bg-slate-800 px-2 py-1 text-xs text-slate-300">{value}</span>)
      : <span className="text-xs text-slate-500">{empty}</span>}
  </div>
);

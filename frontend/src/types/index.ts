// Frontend API types aligned with backend responses

export interface Experience {
  role: string;
  company: string;
  duration: string;
  description: string;
}

export interface Education {
  degree: string;
  school: string;
  year: string;
}

export interface Candidate {
  id: string;
  name: string;
  email: string;
  phone: string;
  location: string;
  currentRole: string;
  currentCompany: string;
  matchScore: number;
  experienceYears?: number;
  skills: string[];
  technologies?: string[];
  projects?: string[];
  summary: string;
  experience: Experience[];
  education: Education[];
  relationshipCount: number;
  matchedSkills?: string[];
  matchedTechnologies?: string[];
  matchedProjects?: string[];
  matchedRoles?: string[];
  matchBreakdown?: MatchBreakdown;
  matchExplanation?: string;
}

export interface MatchBreakdown {
  role_match: boolean;
  experience_match: boolean;
  skill_match: boolean;
  technology_match: boolean;
  project_match: boolean;
}

export interface GraphNode {
  id: string;
  label: string;
  type: 'candidate' | 'skill' | 'company' | 'institution' | 'project' | 'job' | 'application';
  val?: number;
  x?: number;
  y?: number;
  vx?: number;
  vy?: number;
  fx?: number | null;
  fy?: number | null;
}

export interface GraphLink {
  id?: string;
  source: string;
  target: string;
  type: string;
}

export interface CandidateGraph {
  nodes: GraphNode[];
  links: GraphLink[];
  total?: number;
  skip?: number;
  limit?: number;
}

export interface DashboardStats {
  total_resumes: number;
  graph_relationships: number;
  average_match_score: number | null;
  recent_candidates: Array<{
    id: string;
    full_name: string;
    location?: string | null;
    relationship_count: number;
  }>;
  top_skills: Array<{ name: string; count: number }>;
  processing_queue: {
    pending: number;
    processing: number;
    completed: number;
    failed: number;
    duplicates: number;
    idle: boolean;
  };
}

export interface CandidateComparisonResult {
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

export interface AISummaryReport {
  candidateId: string;
  candidateName: string;
  matchScore: number;
  strengths: string[];
  gaps: string[];
  experienceMatchPercent: number;
  skillMatchPercent: number;
  cultureFitPercent: number;
  hiringRecommendation: 'Strong Hire' | 'Hire' | 'Neutral' | 'Pass';
  reasoning: string;
  suggestedInterviewQuestions: string[];
  source?: string;
}

export interface CandidateSummaryResponse {
  candidate_id: string;
  summary: string;
  source: string;
}

export interface UploadProgressLog {
  timestamp: string;
  level: 'info' | 'success' | 'warn' | 'error';
  message: string;
}

export interface UploadResponse {
  success: boolean;
  message: string;
  candidateId: string;
  candidate: Candidate;
  logs: UploadProgressLog[];
}

export interface MatchBreakdown {
  role_match: boolean;
  experience_match: boolean;
  skill_match: boolean;
  technology_match: boolean;
  project_match: boolean;
}

export interface SearchResultItem {
  candidate_id: string;
  full_name: string;
  score: number;
  experience_years?: number;
  matched_roles: string[];
  matched_skills: string[];
  matched_technologies: string[];
  matched_projects: string[];
  match_breakdown: MatchBreakdown;
  explanation?: string;
  summary?: string;
}

export interface SearchApiResponse {
  query: string;
  total: number;
  parsed_skills: string[];
  parsed_technologies: string[];
  parsed_projects: string[];
  min_experience_years?: number;
  results: SearchResultItem[];
}

export interface CandidateDetailApiResponse {
  id: string;
  full_name: string;
  email?: string;
  phone?: string;
  location?: string;
  summary?: string;
  skills: string[];
  technologies: string[];
  projects: string[];
  education: Array<{ institution?: string; degree?: string }>;
  experiences: Array<{
    id?: string;
    company: string;
    role?: string;
    description?: string;
    start_date?: string;
    end_date?: string;
  }>;
  experience_years?: number;
}

export type JobStatus = 'Active' | 'Closed';
export type EmploymentType = 'Full-time' | 'Part-time' | 'Contract' | 'Temporary' | 'Freelance';

export interface Job {
  id: string;
  title: string;
  description: string;
  requiredSkills: string[];
  experience: number;
  location: string;
  employmentType: EmploymentType;
  salary?: {
    min?: number;
    max?: number;
    currency: string;
  } | string;
  status: JobStatus;
  createdAt: string;
  updatedAt: string;
  postedBy?: string;
}

export interface CreateJobInput {
  title: string;
  description: string;
  requiredSkills: string[];
  experience: number;
  location: string;
  employmentType: EmploymentType;
  salary?: {
    min?: number;
    max?: number;
    currency: string;
  };
  status: JobStatus;
}

export type JobApplicationStatus =
  | 'Applied'
  | 'Shortlisted'
  | 'Interview'
  | 'Selected'
  | 'Rejected';

export interface JobApplication {
  id: string;
  job_id: string;
  candidate_id: string;
  full_name: string;
  email?: string | null;
  summary?: string | null;
  status: JobApplicationStatus;
  created_at: string;
  updated_at: string;
}

export interface JobMatchCandidate {
  candidate_id: string;
  full_name: string;
  match_score: number;
  matched_skills: string[];
  missing_skills: string[];
  matched_projects: string[];
  missing_projects: string[];
  experience: number;
  experience_years?: number | null;
  summary?: string | null;
  ai_explanation?: string | null;
  explanation?: string | null;
}

export interface CandidateOption {
  id: string;
  full_name: string;
  email?: string | null;
}

export interface GmailAttachment {
  message_id: string;
  attachment_id: string;
  filename: string;
  size: number;
  mime_type: string;
  subject: string;
  sender: string;
  date: string;
  already_imported?: boolean;
  classification?: 'RESUME' | 'NON_RESUME' | 'UNCERTAIN';
  confidence?: number;
  classification_reason?: string;
  content_hash?: string | null;
}

export interface GmailImportHistoryItem {
  message_id: string;
  attachment_id: string;
  filename: string;
  sha256?: string | null;
  status: 'PENDING' | 'PROCESSING' | 'SUCCESS' | 'FAILED' | 'DUPLICATE';
  imported_at?: string | null;
  updated_at?: string | null;
  candidate_id?: string | null;
  candidate_name?: string | null;
  failure_reason?: string | null;
}

export interface GmailImportItemResult {
  message_id: string;
  attachment_id: string;
  filename: string;
  success: boolean;
  candidate_id?: string | null;
  status: GmailImportHistoryItem['status'];
  sha256?: string | null;
  error?: string | null;
  warning?: string | null;
}

export interface GmailImportResponse {
  success_count: number;
  failure_count: number;
  errors: string[];
  imported_candidates: string[];
  results: GmailImportItemResult[];
}

export interface GmailResumeEmail {
  id: string;
  subject: string;
  sender: string;
  date: string;
  attachments: GmailAttachment[];
}

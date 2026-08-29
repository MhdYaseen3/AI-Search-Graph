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
}

export interface GraphNode {
  id: string;
  label: string;
  type: 'candidate' | 'skill' | 'company' | 'institution' | 'project';
  val?: number;
  x?: number;
  y?: number;
  vx?: number;
  vy?: number;
  fx?: number | null;
  fy?: number | null;
}

export interface GraphLink {
  source: string;
  target: string;
  type: string;
}

export interface CandidateGraph {
  nodes: GraphNode[];
  links: GraphLink[];
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

export interface SearchResultItem {
  candidate_id: string;
  full_name: string;
  score: number;
  experience_years?: number;
  matched_skills: string[];
  matched_technologies: string[];
  matched_projects: string[];
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
  };
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

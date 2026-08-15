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
  skills: string[];
  summary: string;
  experience: Experience[];
  education: Education[];
  relationshipCount: number;
}

export interface GraphNode {
  id: string;
  label: string;
  type: 'candidate' | 'skill' | 'company' | 'institution' | 'project';
  val?: number; // visual weight/size
  x?: number;
  y?: number;
  vx?: number;
  vy?: number;
  fx?: number | null;
  fy?: number | null;
}

export interface GraphLink {
  source: string; // Node ID
  target: string; // Node ID
  type: string;   // 'HAS_SKILL' | 'WORKED_AT' | 'STUDIED_AT' | 'WORKED_ON' | 'COLLABORATED'
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

export type JobStatus = 'Active' | 'Closed';
export type EmploymentType = 'Full-time' | 'Part-time' | 'Contract' | 'Temporary' | 'Freelance';

export interface Job {
  id: string;
  title: string;
  description: string;
  requiredSkills: string[];
  experience: number; // years
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

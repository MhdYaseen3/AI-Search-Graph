import axios from 'axios';
import type {
  Candidate,
  CandidateGraph,
  AISummaryReport,
  UploadResponse,
  Job,
  CreateJobInput,
  SearchApiResponse,
  CandidateDetailApiResponse,
  CandidateSummaryResponse,
  GmailAttachment,
  GmailImportHistoryItem,
  GmailImportResponse,
  JobApplication,
  JobApplicationStatus,
  JobMatchCandidate,
  CandidateOption,
  DashboardStats,
  CandidateComparisonResult,
} from '../types';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';
const USE_REAL_API = import.meta.env.VITE_USE_REAL_API === 'true';

export const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

const mapDetailToCandidate = (detail: CandidateDetailApiResponse, matchScore = 0): Candidate => {
  const experiences = detail.experiences || [];
  const education = detail.education || [];
  const skills = detail.skills || [];
  const technologies = detail.technologies || [];
  const projects = detail.projects || [];
  const latestExperience = experiences[0];
  return {
    id: detail.id,
    name: detail.full_name,
    email: detail.email || 'Not available',
    phone: detail.phone || 'Not available',
    location: detail.location || 'Not specified',
    currentRole: latestExperience?.role || 'Not specified',
    currentCompany: latestExperience?.company || 'Not specified',
    matchScore,
    experienceYears: detail.experience_years,
    skills,
    technologies,
    projects,
    summary: detail.summary || 'No summary available.',
    experience: experiences.map((exp) => ({
      role: exp.role || 'Role not specified',
      company: exp.company,
      duration: `${exp.start_date || 'Unknown'} - ${exp.end_date || 'Present'}`,
      description: exp.description || '',
    })),
    education: education.map((edu) => ({
      degree: edu.degree || 'Degree not specified',
      school: edu.institution || 'Institution not specified',
      year: '',
    })),
    relationshipCount:
      skills.length + technologies.length + projects.length + education.length + experiences.length,
  };
};

const mapSearchResultToCandidate = (
  result: SearchApiResponse['results'][number],
): Candidate => ({
  id: result.candidate_id,
  name: result.full_name,
  email: '',
  phone: '',
  location: 'Not specified',
  currentRole: result.matched_skills[0] || 'Candidate',
  currentCompany: '',
  matchScore: Math.round(result.score * 100),
  experienceYears: result.experience_years,
  skills: result.matched_skills,
  technologies: result.matched_technologies,
  projects: result.matched_projects,
  matchedSkills: result.matched_skills,
  matchedTechnologies: result.matched_technologies,
  matchedProjects: result.matched_projects,
  matchedRoles: result.matched_roles,
  matchBreakdown: result.match_breakdown,
  matchExplanation: result.explanation,
  summary: result.summary || 'No summary available.',
  experience: [],
  education: [],
  relationshipCount:
    result.matched_skills.length +
    result.matched_technologies.length +
    result.matched_projects.length,
});

// ==========================================
// HIGH-FIDELITY MOCK DATABASE FOR FRONTEND DEMO
// ==========================================

const mockCandidates: Candidate[] = [
  {
    id: 'cand-1',
    name: 'Sarah Jenkins',
    email: 'sarah.j@techfuture.io',
    phone: '+1 (555) 234-5678',
    location: 'San Francisco, CA',
    currentRole: 'Senior AI Research Engineer',
    currentCompany: 'NeuralLabs AI',
    matchScore: 96,
    skills: ['PyTorch', 'Python', 'Transformer Models', 'LLMs', 'RAG', 'TypeScript', 'Docker', 'AWS'],
    summary: 'Senior AI Engineer with 6+ years of experience specialized in fine-tuning large language models and developing production-grade Retrieval-Augmented Generation (RAG) systems. Previously led natural language processing pipelines that improved response accuracy by 40%.',
    experience: [
      {
        role: 'Senior AI Research Engineer',
        company: 'NeuralLabs AI',
        duration: '2023 - Present',
        description: 'Led a team of 3 engineers in building a customizable RAG framework for corporate knowledge bases, lowering latency by 150ms. Conducted fine-tuning experiments on open-source LLMs (Llama-3, Mistral) for target industry verticals.'
      },
      {
        role: 'Machine Learning Engineer',
        company: 'CloudScale Solutions',
        duration: '2020 - 2023',
        description: 'Designed and deployed machine learning microservices using FastAPI and PyTorch. Built scalable data parsing pipelines that processed over 5M documents daily.'
      }
    ],
    education: [
      {
        degree: 'Master of Science in Computer Science (AI Specialization)',
        school: 'Stanford University',
        year: '2020'
      },
      {
        degree: 'Bachelor of Science in Software Engineering',
        school: 'UC Berkeley',
        year: '2018'
      }
    ],
    relationshipCount: 14
  },
  {
    id: 'cand-2',
    name: 'Marcus Chen',
    email: 'm.chen@devops-flow.net',
    phone: '+1 (555) 876-5432',
    location: 'Seattle, WA',
    currentRole: 'Lead Cloud Infrastructure Architect',
    currentCompany: 'Synthetix Solutions',
    matchScore: 89,
    skills: ['Kubernetes', 'Terraform', 'Docker', 'AWS', 'Go', 'Python', 'CI/CD', 'Prometheus', 'Linux'],
    summary: 'DevOps & Infrastructure Lead with a decade of experience designing fault-tolerant multi-region cloud deployments. Specialist in Infrastructure as Code (IaC) and Kubernetes orchestrations.',
    experience: [
      {
        role: 'Lead Cloud Infrastructure Architect',
        company: 'Synthetix Solutions',
        duration: '2022 - Present',
        description: 'Migrated legacy container platform to AWS EKS with zero downtime, reducing monthly cloud expenditure by 28%. Automated tenant provisioning using Custom Kubernetes Operators in Go.'
      },
      {
        role: 'Senior DevOps Engineer',
        company: 'AlphaStream Technologies',
        duration: '2018 - 2022',
        description: 'Created unified CI/CD runner environments in GitLab, cutting deployment execution times in half. Engineered multi-cluster Prometheus/Grafana monitoring dashboard systems.'
      }
    ],
    education: [
      {
        degree: 'Bachelor of Science in Computer Engineering',
        school: 'University of Washington',
        year: '2017'
      }
    ],
    relationshipCount: 12
  },
  {
    id: 'cand-3',
    name: 'Elena Rostova',
    email: 'elena.rostova@designcore.co',
    phone: '+1 (555) 345-6789',
    location: 'New York, NY (Remote)',
    currentRole: 'Senior Frontend UI Engineer',
    currentCompany: 'PixelForge Labs',
    matchScore: 92,
    skills: ['React', 'TypeScript', 'Tailwind CSS', 'Next.js', 'Vite', 'Figma', 'Redux Toolkit', 'Jest', 'Websockets'],
    summary: 'Frontend UI specialist dedicated to crafting pixel-perfect, accessible, and high-performance user interfaces. Proven track record of spearheading design systems that unify styling architectures across company divisions.',
    experience: [
      {
        role: 'Senior Frontend UI Engineer',
        company: 'PixelForge Labs',
        duration: '2021 - Present',
        description: 'Designed and implemented the core open-source web application interface, resulting in 500k+ active weekly users. Architected an internal component library utilizing Radix UI primitives and Tailwind CSS.'
      },
      {
        role: 'Web Application Developer',
        company: 'MediSync Systems',
        duration: '2019 - 2021',
        description: 'Developed real-time healthcare telemetry charts using React, D3.js, and WebSockets. Achieved 100% adherence to WCAG 2.1 AA accessibility compliance.'
      }
    ],
    education: [
      {
        degree: 'Bachelor of Fine Arts in Interaction Design',
        school: 'Carnegie Mellon University',
        year: '2019'
      }
    ],
    relationshipCount: 11
  },
  {
    id: 'cand-4',
    name: 'David Kojo',
    email: 'david.kojo@fintech-edge.com',
    phone: '+1 (555) 456-7890',
    location: 'Austin, TX',
    currentRole: 'Backend Engineer (FinTech)',
    currentCompany: 'PayArc Global',
    matchScore: 84,
    skills: ['Go', 'PostgreSQL', 'Redis', 'Kafka', 'Python', 'gRPC', 'Docker', 'Kubernetes'],
    summary: 'Distributed systems backend developer focusing on ledger technologies, transactional integrity, and message brokers. Expert in query optimization and real-time ledger settlement models.',
    experience: [
      {
        role: 'Backend Engineer',
        company: 'PayArc Global',
        duration: '2022 - Present',
        description: 'Refactored transaction reconciliation service using Go and Apache Kafka, increasing throughput capacity by 200%. Optimized SQL querying layouts for PostgreSQL databases with 10M+ transaction rows.'
      },
      {
        role: 'Software Developer',
        company: 'NeoBank Systems',
        duration: '2020 - 2022',
        description: 'Maintained API integrations with payment gateways (Stripe, Plaid). Implemented strict cryptographical protocols for secure user-auth storage.'
      }
    ],
    education: [
      {
        degree: 'Bachelor of Science in Computer Science',
        school: 'University of Texas at Austin',
        year: '2020'
      }
    ],
    relationshipCount: 10
  }
];

// Generate AI summary assessment reports
const generateMockAISummary = (candId: string): AISummaryReport => {
  const cand = mockCandidates.find(c => c.id === candId) || mockCandidates[0];
  
  // Custom strengths, gaps and suggestions per candidate
  let strengths: string[] = ['Solid software architecture standards', 'Proven technical leadership'];
  let gaps: string[] = ['No client-facing experience listed in CV'];
  let recommendation: AISummaryReport['hiringRecommendation'] = 'Hire';
  let questions: string[] = ['How do you resolve architectural disputes within your developers team?'];
  let expScore = 85;
  let skillScore = 90;
  let fitScore = 88;

  if (cand.id === 'cand-1') {
    strengths = ['Advanced PyTorch fine-tuning and model deployment expertise', 'Hands-on RAG vector database integrations', 'High-caliber educational background at Stanford'];
    gaps = ['Less emphasis on native mobile framework integration', 'No C++ machine learning backend engineering shown'];
    recommendation = 'Strong Hire';
    expScore = 98;
    skillScore = 95;
    fitScore = 94;
    questions = [
      'Can you describe your specific fine-tuning recipe for optimizing a Llama-3 model for domain compliance?',
      'How do you address the chunk-overlap latency issue in high-throughput database vectors?'
    ];
  } else if (cand.id === 'cand-2') {
    strengths = ['Deep expertise with Terraform modular configurations', 'Robust security implementations under AWS EKS setups', 'Strong Kubernetes operator programmatic design in Go'];
    gaps = ['No cloud-native deployment experience with Azure/GCP mentioned', 'Minimal React/frontend exposure'];
    recommendation = 'Strong Hire';
    expScore = 92;
    skillScore = 94;
    fitScore = 87;
    questions = [
      'Describe how you designed a Custom Kubernetes Operator. What was the reconcile loop structure?',
      'How do you manage cross-region secrets securely within a multi-cluster Terraform setup?'
    ];
  } else if (cand.id === 'cand-3') {
    strengths = ['State-of-the-art UI/UX aesthetic designs with custom styling layouts', 'Flawless TypeScript component modularization', 'Experienced in web accessibility standard WCAG guidelines'];
    gaps = ['Mainly cloud client side development; minimal Node/Go server-side engineering'];
    recommendation = 'Strong Hire';
    expScore = 94;
    skillScore = 96;
    fitScore = 90;
    questions = [
      'What accessibility tests do you integrate into your CI/CD compilation pipeline?',
      'How do you manage rendering optimization for high-density WebSocket data feeds in React?'
    ];
  }

  return {
    candidateId: cand.id,
    candidateName: cand.name,
    matchScore: cand.matchScore,
    strengths,
    gaps,
    experienceMatchPercent: expScore,
    skillMatchPercent: skillScore,
    cultureFitPercent: fitScore,
    hiringRecommendation: recommendation,
    reasoning: `Candidate ${cand.name} displays excellent synergy with roles requiring high levels of technical adaptability. Their work at ${cand.currentCompany} highlights their ability to deploy production-quality systems. Skill and experience matrices match 90%+ of our senior template standards. Highly recommended to advance to live interview panels.`,
    suggestedInterviewQuestions: questions
  };
};

// ==========================================
// AXIOS INTERCEPTORS FOR MOCK FALLBACK MODE
// ==========================================

// If the API request fails (e.g. backend isn't running), or VITE_USE_MOCK is set, we fallback to our mock data.
// We intercept requests and return mock responses.
api.interceptors.request.use((config) => {
  console.log(`[API Request] ${config.method?.toUpperCase()} ${config.url}`);
  return config;
});

// Helper to simulate network latency
const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

// Mock services layer functions to invoke
export const resumeService = {
  uploadResume: async (file: File): Promise<UploadResponse> => {
    try {
      if (USE_REAL_API) {
        const formData = new FormData();
        formData.append('file', file);
        const response = await api.post('/resumes/ingest', formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        });
        const data = response.data;
        const candidate = mapDetailToCandidate(
          {
            id: data.candidate_id,
            full_name: data.full_name,
            email: data.email,
            phone: data.phone,
            skills: data.skills,
            technologies: data.technologies,
            projects: data.projects,
            education: data.education.map((institution: string) => ({
              institution,
            })),
            experiences: [],
            experience_years: undefined,
          },
          0,
        );

        return {
          success: true,
          message: data.message,
          candidateId: data.candidate_id,
          candidate,
          logs: [
            { timestamp: new Date().toISOString(), level: 'success', message: data.message },
            { timestamp: new Date().toISOString(), level: 'info', message: `Linked ${data.relationship_count} graph nodes.` },
          ],
        };
      }
    } catch (err) {
      console.warn('Real backend error, falling back to mock upload...', err);
    }

    // Mock upload workflow simulation
    await sleep(2500); // realistic analysis time
    const newId = `cand-${Date.now()}`;
    const nameFromFilename = file.name.replace(/\.[^/.]+$/, "").split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
    
    const newCandidate: Candidate = {
      id: newId,
      name: nameFromFilename || 'Alexander Vance',
      email: 'alex.vance@innovate-net.org',
      phone: '+1 (555) 765-4321',
      location: 'Denver, CO',
      currentRole: 'Senior Full Stack Engineer',
      currentCompany: 'Innovate Labs',
      matchScore: 88,
      skills: ['React', 'Node.js', 'PostgreSQL', 'TypeScript', 'Docker', 'Python', 'Tailwind CSS'],
      summary: 'Self-motivated developer with strong analytical skills and a passion for engineering beautiful frontends backed by highly scalable database APIs. Extracted from uploaded PDF metadata.',
      experience: [
        {
          role: 'Senior Full Stack Engineer',
          company: 'Innovate Labs',
          duration: '2022 - Present',
          description: 'Constructed responsive layout designs for admin dashboards. Handled migrations of DB clusters to secure managed instances.'
        }
      ],
      education: [
        {
          degree: 'Bachelor of Science in Information Technology',
          school: 'Colorado State University',
          year: '2021'
        }
      ],
      relationshipCount: 8
    };

    // Add candidate to local session db so it persists in the active session
    mockCandidates.push(newCandidate);

    return {
      success: true,
      message: 'Resume parsed and knowledge graph constructed successfully.',
      candidateId: newId,
      candidate: newCandidate,
      logs: [
        { timestamp: '10:00:01', level: 'info', message: 'Initialized PDF file stream parser.' },
        { timestamp: '10:00:01', level: 'info', message: `Analyzing document: ${file.name} (${(file.size / 1024).toFixed(1)} KB)` },
        { timestamp: '10:00:02', level: 'info', message: 'Extracting contact details and location matrices.' },
        { timestamp: '10:00:02', level: 'info', message: 'Scanning skills vector spaces against job taxonomy libraries.' },
        { timestamp: '10:00:03', level: 'info', message: 'Synthesized 7 matching skills: React, TypeScript, Node.js, PostgreSQL, Docker, Python, Tailwind CSS.' },
        { timestamp: '10:00:03', level: 'info', message: 'Resolving organization nodes (Innovate Labs).' },
        { timestamp: '10:00:04', level: 'success', message: 'Knowledge Graph parsed successfully. Linked candidate with 8 relational nodes.' },
        { timestamp: '10:00:04', level: 'success', message: 'AI Assessment pipeline evaluation completed.' }
      ]
    };
  },

  searchCandidates: async (query: string, signal?: AbortSignal): Promise<Candidate[]> => {
    try {
      const response = await api.post<SearchApiResponse>('/search', null, {
        params: { query },
        signal,
      });
      return response.data.results.map(mapSearchResultToCandidate);
    } catch (err) {
      if (!signal?.aborted) console.error('Real backend search failed', err);
      throw err;
    }
  },

  getCandidateById: async (id: string): Promise<Candidate> => {
    try {
      const response = await api.get<CandidateDetailApiResponse>(`/candidates/${id}/detail`);
      return mapDetailToCandidate(response.data);
    } catch (err) {
      console.error(`Failed to fetch candidate profile ${id}`, err);
      throw err;
    }
  },

  getCandidateGraph: async (
    id: string,
    skip = 0,
    limit = 100,
  ): Promise<CandidateGraph> => {
    if (id === 'global' || !id) {
      const response = await api.get<CandidateGraph>('/candidates/graph', {
        params: { skip, limit },
      });
      return response.data;
    }
    try {
      const response = await api.get<CandidateGraph>(`/candidates/${id}/graph`);
      return response.data;
    } catch (err) {
      console.error(`Failed to fetch graph for candidate ${id}`, err);
      throw err;
    }
  },

  getDashboardStats: async (): Promise<DashboardStats> => {
    const response = await api.get<DashboardStats>('/dashboard/stats');
    return response.data;
  },

  deleteCandidate: async (id: string): Promise<void> => {
    await api.delete(`/candidates/${encodeURIComponent(id)}`);
  },

  getCandidateSummary: async (id: string): Promise<CandidateSummaryResponse> => {
    const response = await api.post<CandidateSummaryResponse>(`/resumes/${id}/summary`);
    return response.data;
  },

  getAISummary: async (id: string): Promise<AISummaryReport> => {
    try {
      if (import.meta.env.VITE_USE_REAL_API === 'true') {
        const response = await api.get<AISummaryReport>(`/api/summary/${id}`);
        return response.data;
      }
    } catch (err) {
      console.warn(`Real backend error fetching AI summary ${id}, falling back...`, err);
    }

    await sleep(600);
    return generateMockAISummary(id);
  },

  compareCandidates: async (candidateIds: string[]): Promise<CandidateComparisonResult> => {
    try {
      const response = await api.post('/candidates/compare', { candidate_ids: candidateIds });
      return response.data;
    } catch (err) {
      console.error('Real backend error comparing candidates', err);
      throw err;
    }
  }
};

// ==========================================
// JOB SERVICE
// ==========================================

interface JobApiRecord {
  id: string;
  title: string;
  description: string;
  required_skills: string[];
  experience: number;
  location: string;
  employment_type: Job['employmentType'];
  salary?: string | null;
  status: Job['status'];
  created_by?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

const salaryFromApi = (salary?: string | null): Job['salary'] => {
  if (!salary) return undefined;
  const amounts = [...salary.matchAll(/\d[\d,]*/g)]
    .map(([value]) => Number(value.replaceAll(',', '')))
    .filter(Number.isFinite);
  const currency = salary.match(/\b[A-Z]{3}\b/)?.[0] || salary;
  return {
    currency,
    min: amounts[0],
    max: amounts[1],
  };
};

const salaryToApi = (salary: CreateJobInput['salary']): string | null => {
  if (!salary) return null;
  if (salary.min !== undefined && salary.max !== undefined) {
    return `${salary.currency} ${salary.min} - ${salary.max}`;
  }
  if (salary.min !== undefined) return `${salary.currency} ${salary.min}+`;
  if (salary.max !== undefined) return `Up to ${salary.currency} ${salary.max}`;
  return null;
};

const mapJobFromApi = (job: JobApiRecord): Job => ({
  id: job.id,
  title: job.title,
  description: job.description,
  requiredSkills: job.required_skills || [],
  experience: job.experience,
  location: job.location,
  employmentType: job.employment_type,
  salary: salaryFromApi(job.salary),
  status: job.status,
  createdAt: job.created_at || new Date().toISOString(),
  updatedAt: job.updated_at || new Date().toISOString(),
  postedBy: job.created_by || undefined,
});

const mapJobToApi = (job: Partial<CreateJobInput>) => ({
  ...(job.title !== undefined && { title: job.title }),
  ...(job.description !== undefined && { description: job.description }),
  ...(job.requiredSkills !== undefined && { required_skills: job.requiredSkills }),
  ...(job.experience !== undefined && { experience: job.experience }),
  ...(job.location !== undefined && { location: job.location }),
  ...(job.employmentType !== undefined && { employment_type: job.employmentType }),
  ...(job.salary !== undefined && { salary: salaryToApi(job.salary) }),
  ...(job.status !== undefined && { status: job.status }),
});

export const jobService = {
  getAllJobs: async (): Promise<Job[]> => {
    const response = await api.get<{ items: JobApiRecord[] }>('/jobs', {
      params: { limit: 100 },
    });
    return response.data.items.map(mapJobFromApi);
  },

  searchJobs: async (query: string): Promise<Job[]> => {
    const response = await api.get<{ items: JobApiRecord[] }>('/jobs/search', {
      params: { q: query, limit: 100 },
    });
    return response.data.items.map(mapJobFromApi);
  },

  getJobsByStatus: async (status: 'Active' | 'Closed'): Promise<Job[]> => {
    const response = await api.get<{ items: JobApiRecord[] }>('/jobs', {
      params: { status, limit: 100 },
    });
    return response.data.items.map(mapJobFromApi);
  },

  getJobById: async (id: string): Promise<Job> => {
    const response = await api.get<JobApiRecord>(`/jobs/${id}`);
    return mapJobFromApi(response.data);
  },

  createJob: async (input: CreateJobInput): Promise<Job> => {
    const response = await api.post<JobApiRecord>('/jobs', mapJobToApi(input));
    return mapJobFromApi(response.data);
  },

  updateJob: async (id: string, input: Partial<CreateJobInput>): Promise<Job> => {
    const response = await api.put<JobApiRecord>(`/jobs/${id}`, mapJobToApi(input));
    return mapJobFromApi(response.data);
  },

  deleteJob: async (id: string): Promise<void> => {
    await api.delete(`/jobs/${id}`);
  },

  matchCandidates: async (jobId: string): Promise<JobMatchCandidate[]> => {
    const response = await api.post<{
      matched_candidates: JobMatchCandidate[];
    }>(`/jobs/${jobId}/match`);
    return response.data.matched_candidates;
  },

  getApplicants: async (jobId: string): Promise<JobApplication[]> => {
    const response = await api.get<JobApplication[]>(`/jobs/${jobId}/applicants`);
    return response.data;
  },

  addApplicant: async (
    jobId: string,
    candidateId: string,
  ): Promise<JobApplication> => {
    const response = await api.post<JobApplication>(
      `/jobs/${jobId}/applicants`,
      { candidate_id: candidateId },
    );
    return response.data;
  },

  updateApplicantStatus: async (
    jobId: string,
    candidateId: string,
    status: JobApplicationStatus,
  ): Promise<JobApplication> => {
    const response = await api.patch<JobApplication>(
      `/jobs/${jobId}/applicants/${candidateId}`,
      { status },
    );
    return response.data;
  },

  getCandidates: async (): Promise<CandidateOption[]> => {
    const response = await api.get<{
      items: CandidateOption[];
    }>('/candidates', { params: { limit: 100 } });
    return response.data.items;
  }
};

const gmailApiError = (err: unknown, fallback: string): string => {
  if (axios.isAxiosError(err)) {
    const data = err.response?.data as { detail?: string; errors?: { service?: string } } | undefined;
    if (typeof data?.detail === 'string' && data.detail.trim()) {
      return data.detail;
    }
    if (err.response?.status === 401) {
      return 'Gmail is not connected. Connect Gmail with read-only access first.';
    }
    return err.message || fallback;
  }
  return fallback;
};

export const gmailService = {
  getAuthUrl: async (): Promise<{ auth_url: string; state: string }> => {
    const response = await api.get('/gmail/auth-url');
    return response.data;
  },

  connect: async (): Promise<string> => {
    const authResponse = await api.get<{ auth_url: string; state: string }>('/gmail/auth-url');
    const { auth_url: authUrl, state } = authResponse.data;
    const redirectUri = new URL(authUrl).searchParams.get('redirect_uri');
    if (!redirectUri) {
      throw new Error('Gmail authorization URL is missing its callback URI.');
    }
    const callbackOrigin = new URL(redirectUri).origin;

    return new Promise((resolve, reject) => {
      let popup: Window | null = null;
      let settled = false;
      let callbackReceived = false;
      let closeGraceTimer: ReturnType<typeof setTimeout> | undefined;

      const cleanup = () => {
        window.removeEventListener('message', handleMessage);
        clearInterval(closeCheck);
        if (closeGraceTimer) clearTimeout(closeGraceTimer);
        clearTimeout(flowTimeout);
      };

      const finish = (error?: Error) => {
        if (settled) return;
        settled = true;
        cleanup();
        if (error) reject(error);
        else resolve(state);
      };

      const handleMessage = (event: MessageEvent<unknown>) => {
        if (event.origin !== callbackOrigin || event.source !== popup) return;
        if (!event.data || typeof event.data !== 'object') return;

        const message = event.data as {
          type?: unknown;
          success?: unknown;
          state?: unknown;
          error?: unknown;
        };
        if (message.type !== 'gmail_oauth_callback') return;
        if (message.state !== state) {
          finish(new Error('OAuth state validation failed. Please try again.'));
          return;
        }
        callbackReceived = true;
        if (closeCheck) clearInterval(closeCheck);
        if (closeGraceTimer) clearTimeout(closeGraceTimer);
        if (message.success === true) {
          void api.get<{ configured: boolean; connected: boolean }>('/gmail/status', {
            params: { state },
          }).then(({ data: status }) => {
            if (!status.connected) {
              finish(new Error('Gmail credentials were not stored. Please try again.'));
              return;
            }
            finish();
          }).catch(() => {
            finish(new Error('Unable to verify the Gmail connection. Please try again.'));
          });
        } else if (message.success === false) {
          finish(new Error(
            typeof message.error === 'string'
              ? message.error
              : 'Failed to connect to Gmail.',
          ));
        }
      };

      window.addEventListener('message', handleMessage);
      const closeCheck = setInterval(() => {
        if (popup?.closed && !callbackReceived && !closeGraceTimer) {
          closeGraceTimer = setTimeout(() => {
            finish(new Error('OAuth popup was closed before authentication completed.'));
          }, 2000);
        }
      }, 250);
      const flowTimeout = setTimeout(() => {
        finish(new Error('OAuth flow timed out. Please try again.'));
      }, 120000);
      try {
        popup = window.open(authUrl, 'gmail-oauth', 'width=500,height=600');
      } catch {
        finish(new Error('Unable to open the Gmail authorization popup.'));
        return;
      }

      if (!popup) {
        finish(new Error('Popup was blocked. Please allow popups for this site and try again.'));
      }
    });
  },

  getStatus: async (state?: string): Promise<{ configured: boolean; connected: boolean; email?: string | null }> => {
    const response = await api.get('/gmail/status', {
      params: state ? { state } : undefined,
    });
    return response.data;
  },

  disconnect: async (state: string): Promise<{ message: string }> => {
    try {
      const response = await api.post('/gmail/disconnect', null, {
        params: { state },
      });
      return response.data;
    } catch (err) {
      throw new Error(
        gmailApiError(err, 'Failed to disconnect Gmail account.'),
        { cause: err },
      );
    }
  },

  switchAccount: async (oldState: string): Promise<string> => {
    try {
      const authResponse = await api.get<{ auth_url: string; state: string }>('/gmail/switch-account', {
        params: { state: oldState },
      });
      const { auth_url: authUrl, state: newState } = authResponse.data;
      const redirectUri = new URL(authUrl).searchParams.get('redirect_uri');
      if (!redirectUri) {
        throw new Error('Gmail authorization URL is missing its callback URI.');
      }
      const callbackOrigin = new URL(redirectUri).origin;

      return new Promise((resolve, reject) => {
        let popup: Window | null = null;
        let settled = false;
        let callbackReceived = false;
        let closeGraceTimer: ReturnType<typeof setTimeout> | undefined;

        const cleanup = () => {
          window.removeEventListener('message', handleMessage);
          clearInterval(closeCheck);
          if (closeGraceTimer) clearTimeout(closeGraceTimer);
          clearTimeout(flowTimeout);
        };

        const finish = (error?: Error) => {
          if (settled) return;
          settled = true;
          cleanup();
          if (error) reject(error);
          else resolve(newState);
        };

        const handleMessage = (event: MessageEvent<unknown>) => {
          if (event.origin !== callbackOrigin || event.source !== popup) return;
          if (!event.data || typeof event.data !== 'object') return;

          const message = event.data as {
            type?: unknown;
            success?: unknown;
            state?: unknown;
            error?: unknown;
          };
          if (message.type !== 'gmail_oauth_callback') return;
          if (message.state !== newState) {
            finish(new Error('OAuth state validation failed. Please try again.'));
            return;
          }
          callbackReceived = true;
          if (closeCheck) clearInterval(closeCheck);
          if (closeGraceTimer) clearTimeout(closeGraceTimer);
          if (message.success === true) {
            // On successful switch, disconnect the old account
            void api.post('/gmail/disconnect', null, {
              params: { state: oldState },
            }).catch((err) => {
              console.warn('Failed to disconnect old Gmail account:', err);
            });

            void api.get<{ configured: boolean; connected: boolean; email?: string | null }>('/gmail/status', {
              params: { state: newState },
            }).then(({ data: status }) => {
              if (!status.connected) {
                finish(new Error('Gmail credentials were not stored. Please try again.'));
                return;
              }
              finish();
            }).catch(() => {
              finish(new Error('Unable to verify the Gmail connection. Please try again.'));
            });
          } else if (message.success === false) {
            finish(new Error(
              typeof message.error === 'string'
                ? message.error
                : 'Failed to connect to Gmail.',
            ));
          }
        };

        window.addEventListener('message', handleMessage);
        const closeCheck = setInterval(() => {
          if (popup?.closed && !callbackReceived && !closeGraceTimer) {
            closeGraceTimer = setTimeout(() => {
              finish(new Error('OAuth popup was closed before authentication completed.'));
            }, 2000);
          }
        }, 250);
        const flowTimeout = setTimeout(() => {
          finish(new Error('OAuth flow timed out. Please try again.'));
        }, 120000);
        try {
          popup = window.open(authUrl, 'gmail-oauth', 'width=500,height=600');
        } catch {
          finish(new Error('Unable to open the Gmail authorization popup.'));
          return;
        }

        if (!popup) {
          finish(new Error('Popup was blocked. Please allow popups for this site and try again.'));
        }
      });
    } catch (err) {
      throw new Error(
        gmailApiError(err, 'Failed to switch Gmail account.'),
        { cause: err },
      );
    }
  },

  searchResumeEmails: async (
    state: string,
    query?: string,
    maxResults?: number,
  ): Promise<GmailAttachment[]> => {
    try {
      const response = await api.post('/gmail/search', {
        query: query || 'resume OR cv OR "job application"',
        max_results: maxResults || 50,
      }, {
        params: { state },
      });
      return response.data;
    } catch (err) {
      throw new Error(
        gmailApiError(err, 'Failed to search Gmail resume emails.'),
        { cause: err },
      );
    }
  },

  importAttachments: async (
    state: string,
    attachments: GmailAttachment[],
  ): Promise<GmailImportResponse> => {
    try {
      const response = await api.post('/gmail/import', { attachments }, {
        params: { state },
      });
      return response.data;
    } catch (err) {
      throw new Error(
        gmailApiError(err, 'Failed to import Gmail resume attachments.'),
        { cause: err },
      );
    }
  },

  getImportHistory: async (limit = 100): Promise<GmailImportHistoryItem[]> => {
    try {
      const response = await api.get('/gmail/import-history', {
        params: { limit },
      });
      return response.data;
    } catch (err) {
      throw new Error(
        gmailApiError(err, 'Failed to load Gmail import history.'),
        { cause: err },
      );
    }
  },

  retryFailedImport: async (
    state: string,
    messageId: string,
    attachmentId: string,
  ): Promise<GmailImportResponse> => {
    try {
      const response = await api.post(
        '/gmail/import/retry',
        { message_id: messageId, attachment_id: attachmentId },
        { params: { state } },
      );
      return response.data;
    } catch (err) {
      throw new Error(
        gmailApiError(err, 'Failed to retry Gmail attachment import.'),
        { cause: err },
      );
    }
  },
};

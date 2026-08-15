import axios from 'axios';
import type { Candidate, CandidateGraph, AISummaryReport, UploadResponse, Job, CreateJobInput } from '../types';
// API client configuration
export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '',
  headers: {
    'Content-Type': 'application/json',
  },
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

// Generate visual graph data for a candidate
const generateMockGraph = (candId: string): CandidateGraph => {
  const cand = mockCandidates.find(c => c.id === candId) || mockCandidates[0];
  
  // Standard nodes: Candidate, current company, past companies, schools
  const nodes: CandidateGraph['nodes'] = [
    { id: cand.id, label: cand.name, type: 'candidate', val: 30 },
  ];
  const links: CandidateGraph['links'] = [];

  // Add school nodes and links
  cand.education.forEach((edu, index) => {
    const schoolId = `school-${index}-${cand.id}`;
    nodes.push({ id: schoolId, label: edu.school, type: 'institution', val: 18 });
    links.push({ source: cand.id, target: schoolId, type: 'STUDIED_AT' });
  });

  // Add company nodes and links
  cand.experience.forEach((exp, index) => {
    const compId = `company-${index}-${cand.id}`;
    nodes.push({ id: compId, label: exp.company, type: 'company', val: 22 });
    links.push({ source: cand.id, target: compId, type: index === 0 ? 'WORKED_AT' : 'PREVIOUSLY_WORKED_AT' });
  });

  // Add top skill nodes and links
  cand.skills.forEach((skill) => {
    const skillId = `skill-${skill.toLowerCase().replace(/\s+/g, '-')}`;
    // check if skill node already exists in case we combine
    if (!nodes.some(n => n.id === skillId)) {
      nodes.push({ id: skillId, label: skill, type: 'skill', val: 15 });
    }
    links.push({ source: cand.id, target: skillId, type: 'HAS_SKILL' });
  });

  // Add mock dynamic items (projects or shared nodes)
  const projId = `project-1-${cand.id}`;
  nodes.push({ id: projId, label: 'Enterprise Graph System', type: 'project', val: 16 });
  links.push({ source: cand.id, target: projId, type: 'WORKED_ON' });
  
  // Link skills to the project too
  if (cand.skills[0]) {
    const skillId = `skill-${cand.skills[0].toLowerCase().replace(/\s+/g, '-')}`;
    links.push({ source: projId, target: skillId, type: 'REQUIRES' });
  }
  if (cand.skills[1]) {
    const skillId = `skill-${cand.skills[1].toLowerCase().replace(/\s+/g, '-')}`;
    links.push({ source: projId, target: skillId, type: 'REQUIRES' });
  }

  return { nodes, links };
};

// Generate Global/Combined Graph for all candidates
export const generateGlobalGraph = (): CandidateGraph => {
  const nodes: CandidateGraph['nodes'] = [];
  const links: CandidateGraph['links'] = [];
  
  // Shared hubs (Common skills/companies)
  const sharedSkills = ['Python', 'Docker', 'Kubernetes', 'TypeScript', 'React', 'AWS'];
  sharedSkills.forEach(s => {
    nodes.push({ id: `skill-${s.toLowerCase()}`, label: s, type: 'skill', val: 24 }); // major hubs
  });
  
  mockCandidates.forEach(cand => {
    // Add candidate node
    nodes.push({ id: cand.id, label: cand.name, type: 'candidate', val: 32 });
    
    // Add current company
    const compId = `comp-${cand.currentCompany.toLowerCase().replace(/\s+/g, '-')}`;
    if (!nodes.some(n => n.id === compId)) {
      nodes.push({ id: compId, label: cand.currentCompany, type: 'company', val: 22 });
    }
    links.push({ source: cand.id, target: compId, type: 'WORKED_AT' });
    
    // Add skills. If skill is a shared hub, link to it. Otherwise create it.
    cand.skills.forEach(s => {
      const skillId = `skill-${s.toLowerCase().replace(/\s+/g, '-')}`;
      if (!nodes.some(n => n.id === skillId)) {
        nodes.push({ id: skillId, label: s, type: 'skill', val: 14 });
      }
      links.push({ source: cand.id, target: skillId, type: 'HAS_SKILL' });
    });
    
    // Add university
    const edu = cand.education[0];
    if (edu) {
      const schoolId = `school-${edu.school.toLowerCase().replace(/\s+/g, '-')}`;
      if (!nodes.some(n => n.id === schoolId)) {
        nodes.push({ id: schoolId, label: edu.school, type: 'institution', val: 20 });
      }
      links.push({ source: cand.id, target: schoolId, type: 'STUDIED_AT' });
    }
  });

  return { nodes, links };
};

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
      // If configured to use actual backend:
      if (import.meta.env.VITE_USE_REAL_API === 'true') {
        const formData = new FormData();
        formData.append('file', file);
        const response = await api.post<UploadResponse>('/api/resumes/upload', formData, {
          headers: { 'Content-Type': 'multipart/form-data' }
        });
        return response.data;
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

  searchCandidates: async (query: string): Promise<Candidate[]> => {
    try {
      if (import.meta.env.VITE_USE_REAL_API === 'true') {
        const response = await api.get<Candidate[]>(`/api/search?q=${encodeURIComponent(query)}`);
        return response.data;
      }
    } catch (err) {
      console.warn('Real backend error, falling back to mock search...', err);
    }

    await sleep(600); // simulated network delay
    if (!query.trim()) return mockCandidates;

    const lowerQuery = query.toLowerCase();
    return mockCandidates.filter((c) => 
      c.name.toLowerCase().includes(lowerQuery) ||
      c.currentRole.toLowerCase().includes(lowerQuery) ||
      c.currentCompany.toLowerCase().includes(lowerQuery) ||
      c.skills.some(s => s.toLowerCase().includes(lowerQuery)) ||
      c.location.toLowerCase().includes(lowerQuery)
    );
  },

  getCandidateById: async (id: string): Promise<Candidate> => {
    try {
      if (import.meta.env.VITE_USE_REAL_API === 'true') {
        const response = await api.get<Candidate>(`/api/candidates/${id}`);
        return response.data;
      }
    } catch (err) {
      console.warn(`Real backend error fetching candidate ${id}, falling back...`, err);
    }

    await sleep(500);
    const cand = mockCandidates.find(c => c.id === id);
    if (!cand) throw new Error(`Candidate with id ${id} not found.`);
    return cand;
  },

  getCandidateGraph: async (id: string): Promise<CandidateGraph> => {
    try {
      if (import.meta.env.VITE_USE_REAL_API === 'true') {
        const response = await api.get<CandidateGraph>(`/api/graph/${id}`);
        return response.data;
      }
    } catch (err) {
      console.warn(`Real backend error fetching graph ${id}, falling back...`, err);
    }

    await sleep(700);
    if (id === 'global' || !id) {
      return generateGlobalGraph();
    }
    return generateMockGraph(id);
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
  }
};

// ==========================================
// MOCK JOBS DATABASE
// ==========================================

const mockJobs: Job[] = [
  {
    id: 'job-1',
    title: 'Senior ML Engineer - LLM Fine-tuning',
    description: 'Join our AI team to lead the development of production-grade Language Models. Work with state-of-the-art transformer architectures and RAG frameworks to build next-generation AI solutions.',
    requiredSkills: ['PyTorch', 'Python', 'LLMs', 'RAG', 'Distributed Systems'],
    experience: 5,
    location: 'San Francisco, CA',
    employmentType: 'Full-time',
    salary: { min: 180000, max: 240000, currency: 'USD' },
    status: 'Active',
    createdAt: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
    updatedAt: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000).toISOString(),
    postedBy: 'tech-recruiter@graphcv.io'
  },
  {
    id: 'job-2',
    title: 'DevOps & Infrastructure Architect',
    description: 'Build and scale cloud infrastructure on AWS and Kubernetes. Lead infrastructure-as-code initiatives and optimize multi-region deployments. Work on CI/CD automation and monitoring solutions.',
    requiredSkills: ['Kubernetes', 'Terraform', 'AWS', 'Docker', 'Go', 'CI/CD'],
    experience: 6,
    location: 'Seattle, WA',
    employmentType: 'Full-time',
    salary: { min: 170000, max: 230000, currency: 'USD' },
    status: 'Active',
    createdAt: new Date(Date.now() - 14 * 24 * 60 * 60 * 1000).toISOString(),
    updatedAt: new Date(),
    postedBy: 'tech-recruiter@graphcv.io'
  },
  {
    id: 'job-3',
    title: 'Frontend UI/UX Engineer',
    description: 'Design and build beautiful, accessible user interfaces for our flagship product. Work with React, TypeScript, and Tailwind CSS. Collaborate with designers to implement pixel-perfect interfaces.',
    requiredSkills: ['React', 'TypeScript', 'Tailwind CSS', 'Next.js', 'JavaScript'],
    experience: 3,
    location: 'New York, NY (Remote)',
    employmentType: 'Full-time',
    salary: { min: 140000, max: 190000, currency: 'USD' },
    status: 'Active',
    createdAt: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000).toISOString(),
    updatedAt: new Date(),
    postedBy: 'tech-recruiter@graphcv.io'
  },
  {
    id: 'job-4',
    title: 'Backend Engineer - Fintech',
    description: 'Build highly scalable backend services for payment processing and ledger management. Work with Go, PostgreSQL, and Kafka. Expertise in transaction integrity and distributed systems required.',
    requiredSkills: ['Go', 'PostgreSQL', 'Kafka', 'Redis', 'gRPC'],
    experience: 4,
    location: 'Austin, TX',
    employmentType: 'Full-time',
    salary: { min: 160000, max: 220000, currency: 'USD' },
    status: 'Active',
    createdAt: new Date(Date.now() - 21 * 24 * 60 * 60 * 1000).toISOString(),
    updatedAt: new Date(Date.now() - 10 * 24 * 60 * 60 * 1000).toISOString(),
    postedBy: 'tech-recruiter@graphcv.io'
  },
  {
    id: 'job-5',
    title: 'Data Scientist - Analytics',
    description: 'Develop data pipelines and machine learning models to unlock insights from large datasets. Work with Python, SQL, and cloud data warehouses. Help drive product decisions with data-driven recommendations.',
    requiredSkills: ['Python', 'SQL', 'Machine Learning', 'Data Analysis', 'Apache Spark'],
    experience: 3,
    location: 'Boston, MA (Remote)',
    employmentType: 'Full-time',
    salary: { min: 130000, max: 180000, currency: 'USD' },
    status: 'Closed',
    createdAt: new Date(Date.now() - 60 * 24 * 60 * 60 * 1000).toISOString(),
    updatedAt: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString(),
    postedBy: 'tech-recruiter@graphcv.io'
  },
  {
    id: 'job-6',
    title: 'Full Stack Engineer',
    description: 'Build full-stack features from database to user interface. Work across our tech stack: React, Node.js, TypeScript, and PostgreSQL. Contribute to architectural decisions and code quality.',
    requiredSkills: ['React', 'Node.js', 'TypeScript', 'PostgreSQL', 'Docker'],
    experience: 2,
    location: 'Denver, CO (Remote)',
    employmentType: 'Full-time',
    salary: { min: 120000, max: 170000, currency: 'USD' },
    status: 'Active',
    createdAt: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(),
    updatedAt: new Date(),
    postedBy: 'tech-recruiter@graphcv.io'
  }
];

// ==========================================
// JOB SERVICE
// ==========================================

export const jobService = {
  getAllJobs: async (): Promise<Job[]> => {
    try {
      if (import.meta.env.VITE_USE_REAL_API === 'true') {
        const response = await api.get<Job[]>('/api/jobs');
        return response.data;
      }
    } catch (err) {
      console.warn('Real backend error, falling back to mock jobs...', err);
    }

    await sleep(400);
    return mockJobs;
  },

  searchJobs: async (query: string): Promise<Job[]> => {
    try {
      if (import.meta.env.VITE_USE_REAL_API === 'true') {
        const response = await api.get<Job[]>(`/api/jobs/search?q=${encodeURIComponent(query)}`);
        return response.data;
      }
    } catch (err) {
      console.warn('Real backend error, falling back to mock job search...', err);
    }

    await sleep(500);
    if (!query.trim()) return mockJobs;

    const lowerQuery = query.toLowerCase();
    return mockJobs.filter((job) =>
      job.title.toLowerCase().includes(lowerQuery) ||
      job.description.toLowerCase().includes(lowerQuery) ||
      job.requiredSkills.some(s => s.toLowerCase().includes(lowerQuery)) ||
      job.location.toLowerCase().includes(lowerQuery)
    );
  },

  getJobsByStatus: async (status: 'Active' | 'Closed'): Promise<Job[]> => {
    try {
      if (import.meta.env.VITE_USE_REAL_API === 'true') {
        const response = await api.get<Job[]>(`/api/jobs?status=${status}`);
        return response.data;
      }
    } catch (err) {
      console.warn('Real backend error, falling back to mock job status filter...', err);
    }

    await sleep(300);
    return mockJobs.filter(job => job.status === status);
  },

  getJobById: async (id: string): Promise<Job> => {
    try {
      if (import.meta.env.VITE_USE_REAL_API === 'true') {
        const response = await api.get<Job>(`/api/jobs/${id}`);
        return response.data;
      }
    } catch (err) {
      console.warn(`Real backend error fetching job ${id}, falling back...`, err);
    }

    await sleep(300);
    const job = mockJobs.find(j => j.id === id);
    if (!job) throw new Error(`Job with id ${id} not found.`);
    return job;
  },

  createJob: async (input: CreateJobInput): Promise<Job> => {
    try {
      if (import.meta.env.VITE_USE_REAL_API === 'true') {
        const response = await api.post<Job>('/api/jobs', input);
        return response.data;
      }
    } catch (err) {
      console.warn('Real backend error, falling back to mock job creation...', err);
    }

    await sleep(600);
    const newJob: Job = {
      id: `job-${Date.now()}`,
      ...input,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      postedBy: 'tech-recruiter@graphcv.io'
    };

    // Add to mock database
    mockJobs.unshift(newJob);
    return newJob;
  },

  updateJob: async (id: string, input: Partial<CreateJobInput>): Promise<Job> => {
    try {
      if (import.meta.env.VITE_USE_REAL_API === 'true') {
        const response = await api.patch<Job>(`/api/jobs/${id}`, input);
        return response.data;
      }
    } catch (err) {
      console.warn(`Real backend error updating job ${id}, falling back...`, err);
    }

    await sleep(500);
    const jobIndex = mockJobs.findIndex(j => j.id === id);
    if (jobIndex === -1) throw new Error(`Job with id ${id} not found.`);

    const updatedJob: Job = {
      ...mockJobs[jobIndex],
      ...input,
      updatedAt: new Date().toISOString()
    };

    mockJobs[jobIndex] = updatedJob;
    return updatedJob;
  },

  deleteJob: async (id: string): Promise<void> => {
    try {
      if (import.meta.env.VITE_USE_REAL_API === 'true') {
        await api.delete(`/api/jobs/${id}`);
        return;
      }
    } catch (err) {
      console.warn(`Real backend error deleting job ${id}, falling back...`, err);
    }

    await sleep(400);
    const jobIndex = mockJobs.findIndex(j => j.id === id);
    if (jobIndex === -1) throw new Error(`Job with id ${id} not found.`);
    mockJobs.splice(jobIndex, 1);
  }
};

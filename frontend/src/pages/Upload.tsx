import React, { useEffect, useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  UploadCloud, 
  FileText, 
  CheckCircle, 
  AlertCircle, 
  Terminal,
  GitFork,
  User,
  Mail
} from 'lucide-react';
import { gmailService, resumeService } from '../services/api';
import type { Candidate, GmailResumeEmail, UploadProgressLog } from '../types';

export const Upload: React.FC = () => {
  const [dragActive, setDragActive] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [logs, setLogs] = useState<UploadProgressLog[]>([]);
  const [newCandidate, setNewCandidate] = useState<Candidate | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const logEndRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();
  const [gmailConnected, setGmailConnected] = useState(false);
  const [gmailQuery, setGmailQuery] = useState('');
  const [gmailEmails, setGmailEmails] = useState<GmailResumeEmail[]>([]);
  const [gmailSearching, setGmailSearching] = useState(false);
  const [gmailImporting, setGmailImporting] = useState(false);
  const [gmailError, setGmailError] = useState<string | null>(null);
  const [selectedAttachments, setSelectedAttachments] = useState<Record<string, boolean>>({});
  const [gmailState, setGmailState] = useState<string | null>(null);

  const attachmentKey = (messageId: string, attachmentId: string) =>
    `${messageId}:${attachmentId}`;

  useEffect(() => {
    const savedState = sessionStorage.getItem('gmailOAuthState');
    gmailService
      .getStatus(savedState || undefined)
      .then((status) => {
        if (status.connected && savedState) {
          setGmailConnected(true);
          setGmailState(savedState);
        } else {
          sessionStorage.removeItem('gmailOAuthState');
          setGmailConnected(false);
          setGmailState(null);
        }
      })
      .catch(() => setGmailConnected(false));
  }, []);

  const connectGmail = async () => {
    setGmailError(null);
    try {
      const state = await gmailService.connect();
      sessionStorage.setItem('gmailOAuthState', state);
      setGmailState(state);
      setGmailConnected(true);
    } catch (err: unknown) {
      setGmailError(err instanceof Error ? err.message : 'Failed to connect to Gmail');
    }
  };

  const searchGmail = async () => {
    if (!gmailState) {
      setGmailError('Not authenticated. Please connect Gmail first.');
      return;
    }

    setGmailSearching(true);
    setGmailError(null);
    setSelectedAttachments({});
    try {
      const attachments = await gmailService.searchResumeEmails(gmailState, gmailQuery);

      // Convert attachments to email groups
      const emailMap = new Map<string, GmailResumeEmail>();
      attachments.forEach((att) => {
        const key = att.message_id;
        if (!emailMap.has(key)) {
          emailMap.set(key, {
            id: att.message_id,
            subject: att.subject,
            sender: att.sender,
            date: att.date,
            attachments: [],
          });
        }
        emailMap.get(key)!.attachments.push({
          ...att,
          already_imported: false,
        });
      });

      setGmailEmails(Array.from(emailMap.values()));
      if (attachments.length === 0) {
        setGmailError('No resume-related emails with attachments matched this search.');
      }
    } catch (err: unknown) {
      setGmailEmails([]);
      setGmailError(err instanceof Error ? err.message : 'Failed to search Gmail.');
    } finally {
      setGmailSearching(false);
    }
  };

  const toggleAttachment = (messageId: string, attachmentId: string, disabled: boolean) => {
    if (disabled) return;
    const key = attachmentKey(messageId, attachmentId);
    setSelectedAttachments((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const importSelectedGmailResumes = async () => {
    if (!gmailState) {
      setGmailError('Not authenticated. Please connect Gmail first.');
      return;
    }

    const attachments = gmailEmails.flatMap((email) =>
      email.attachments
        .filter((attachment) => selectedAttachments[attachmentKey(attachment.message_id, attachment.attachment_id)])
        .map((attachment) => ({
          message_id: attachment.message_id,
          attachment_id: attachment.attachment_id,
          filename: attachment.filename,
          size: attachment.size,
          mime_type: attachment.mime_type,
          subject: email.subject,
          sender: email.sender,
          date: email.date,
          classification: attachment.classification,
        })),
    );

    if (attachments.length === 0) {
      setGmailError('Select at least one PDF attachment to import.');
      return;
    }

    setGmailImporting(true);
    setGmailError(null);
    try {
      const result = await gmailService.importAttachments(gmailState, attachments);

      if (result.success_count > 0) {
        const firstCandidateId = result.imported_candidates[0];
        setLogs((prev) => [
          ...prev,
          {
            timestamp: new Date().toISOString(),
            level: 'success',
            message: `Imported ${result.success_count} Gmail resume${result.success_count === 1 ? '' : 's'} into the candidate graph.`,
          },
        ]);
        if (firstCandidateId) {
          const firstAttachment = attachments[0];
          setNewCandidate({
            id: firstCandidateId,
            name: firstAttachment.filename.replace(/\.pdf$/i, ''),
            email: 'Imported from Gmail',
            phone: '',
            location: '',
            currentRole: 'Imported candidate',
            currentCompany: '',
            matchScore: 0,
            skills: [],
            summary: 'Resume imported from Gmail through the existing ingest pipeline.',
            experience: [],
            education: [],
            relationshipCount: 0,
          });
        }
      }

      if (result.errors.length > 0) {
        setGmailError(result.errors.join(' '));
      }

      // Mark imported attachments
      setGmailEmails((prev) =>
        prev.map((email) => ({
          ...email,
          attachments: email.attachments.map((attachment) => {
            const wasImported = result.imported_candidates.length > 0;
            return wasImported ? { ...attachment, already_imported: true } : attachment;
          }),
        })),
      );
      setSelectedAttachments({});
    } catch (err: unknown) {
      setGmailError(err instanceof Error ? err.message : 'Failed to import Gmail attachments.');
    } finally {
      setGmailImporting(false);
    }
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      validateAndSetFile(e.dataTransfer.files[0]);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      validateAndSetFile(e.target.files[0]);
    }
  };

  const validateAndSetFile = (selectedFile: File) => {
    setError(null);
    setNewCandidate(null);
    setLogs([]);
    
    if (selectedFile.type !== 'application/pdf') {
      setError('Invalid file type. Only PDF resumes are supported.');
      return;
    }

    if (selectedFile.size > 10 * 1024 * 1024) { // 10MB
      setError('File size too large. Maximum size allowed is 10MB.');
      return;
    }

    setFile(selectedFile);
  };

  const triggerFileInput = () => {
    fileInputRef.current?.click();
  };

  const startParsing = async () => {
    if (!file) return;
    
    setUploading(true);
    setLogs([
      { timestamp: '10:00:00', level: 'info', message: 'Sending file to secure ingestion endpoint...' }
    ]);

    try {
      // Execute upload service (mocked with timeout)
      const res = await resumeService.uploadResume(file);
      
      if (res.success) {
        // Stream logs over short intervals to simulate live parsing
        for (let i = 0; i < res.logs.length; i++) {
          await new Promise((resolve) => setTimeout(resolve, 300));
          setLogs(prev => [...prev, res.logs[i]]);
          // scroll logs logEndRef
          setTimeout(() => logEndRef.current?.scrollIntoView({ behavior: 'smooth' }), 50);
        }
        setNewCandidate(res.candidate);
      } else {
        setError(res.message || 'Parsing failed.');
      }
    } catch (err: any) {
      setError(err?.message || 'Error occurred during parsing processing.');
      setLogs(prev => [...prev, { timestamp: '10:00:05', level: 'error', message: 'Pipeline integration terminated with errors.' }]);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8 animate-in fade-in duration-300">
      
      {/* EXPLANATORY HERO TITLE */}
      <div className="space-y-2">
        <h1 className="text-2xl lg:text-3xl font-extrabold text-white tracking-tight">Ingest Resume & Build Graph</h1>
        <p className="text-sm text-slate-400">
          Upload candidate CVs in PDF format. The system automatically reads semantic sections, identifies corporate and educational entities, and embeds them into your active Talent Knowledge Graph.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        
        {/* DRAG AND DROP ZONE PANEL */}
        <div className="lg:col-span-3 space-y-6">
          <div 
            className={`glass-panel border-2 border-dashed rounded-2xl p-8 flex flex-col items-center justify-center text-center cursor-pointer transition-all duration-300 ${
              dragActive ? 'border-brand-500 bg-brand-600/5 glow-purple' : 'border-dark-border hover:border-slate-700'
            }`}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            onClick={triggerFileInput}
          >
            <input 
              ref={fileInputRef}
              type="file" 
              className="hidden" 
              accept=".pdf"
              onChange={handleChange}
            />

            <div className="w-14 h-14 rounded-xl bg-brand-500/10 border border-brand-500/20 text-brand-500 flex items-center justify-center mb-4">
              <UploadCloud size={28} />
            </div>

            {file ? (
              <div className="space-y-2">
                <h3 className="text-sm font-bold text-white flex items-center justify-center gap-1.5">
                  <FileText size={16} className="text-brand-400" />
                  {file.name}
                </h3>
                <p className="text-xs text-slate-400">{(file.size / 1024).toFixed(1)} KB</p>
                <span className="text-[10px] text-brand-400 font-semibold block">Click to change file</span>
              </div>
            ) : (
              <div className="space-y-1">
                <h3 className="text-sm font-bold text-white">Drag and drop resume here</h3>
                <p className="text-xs text-slate-400">Supports PDF format up to 10MB</p>
                <button className="text-xs text-brand-500 font-semibold underline pt-2 hover:text-brand-400">
                  Or select file from device
                </button>
              </div>
            )}
          </div>

          {error && (
            <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex items-start gap-2">
              <AlertCircle size={16} className="shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {file && !uploading && !newCandidate && (
            <button
              onClick={startParsing}
              className="w-full bg-brand-600 hover:bg-brand-700 text-white font-semibold py-3.5 rounded-xl shadow-lg shadow-brand-700/20 flex items-center justify-center gap-2 transition-all duration-200"
            >
              <UploadCloud size={16} />
              <span>Process Ingestion Pipeline</span>
            </button>
          )}

          {uploading && (
            <div className="glass-panel rounded-2xl p-6 space-y-4">
              <div className="flex items-center justify-between text-xs">
                <span className="text-brand-400 font-semibold flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-brand-500 animate-ping" />
                  Analyzing Resume Data Structure...
                </span>
                <span className="text-slate-500">Estimating ~5s</span>
              </div>
              <div className="w-full bg-slate-900 h-2.5 rounded-full overflow-hidden border border-dark-border">
                <div className="h-full bg-brand-600 animate-shimmer rounded-full" style={{ width: '100%' }} />
              </div>
            </div>
          )}
        </div>

        {/* INGESTION PIPELINE LOGGING DISPLAY */}
        <div className="lg:col-span-2 space-y-6 flex flex-col">
          <div className="glass-panel rounded-2xl p-5 flex-1 flex flex-col justify-between min-h-[300px] border border-dark-border/80">
            <div className="flex items-center gap-2 border-b border-dark-border/40 pb-3 mb-3">
              <Terminal size={14} className="text-brand-400" />
              <h3 className="text-[10px] font-bold text-white uppercase tracking-wider">Parsing Console Log</h3>
            </div>

            <div className="flex-1 font-mono text-[11px] text-slate-400 space-y-2.5 max-h-[280px] overflow-y-auto pr-1">
              {logs.length > 0 ? (
                logs.map((log, index) => (
                  <div key={index} className="flex gap-2 items-start leading-relaxed animate-in slide-in-from-bottom-2 duration-100">
                    <span className="text-[9px] text-slate-600 shrink-0 mt-0.5">[{log.timestamp}]</span>
                    <span className={`
                      ${log.level === 'success' ? 'text-emerald-400' : ''}
                      ${log.level === 'warn' ? 'text-amber-400' : ''}
                      ${log.level === 'error' ? 'text-rose-400' : ''}
                      ${log.level === 'info' ? 'text-slate-400' : ''}
                    `}>
                      {log.message}
                    </span>
                  </div>
                ))
              ) : (
                <div className="h-full flex items-center justify-center text-slate-500 text-center italic py-10">
                  Awaiting resume ingestion upload process initiation...
                </div>
              )}
              <div ref={logEndRef} />
            </div>
          </div>
        </div>
      </div>

      {/* PIPELINE SUCCESS CANDIDATE PREVIEW */}
      {newCandidate && (
        <section className="glass-panel rounded-2xl p-6 border-l-4 border-emerald-500 glow-green animate-in fade-in slide-in-from-top-6 duration-300">
          <div className="flex items-center gap-3 mb-4">
            <CheckCircle className="text-emerald-400" size={24} />
            <div>
              <h3 className="text-base font-bold text-white">Ingestion Completed Successfully</h3>
              <p className="text-xs text-slate-400">Extracted and mapped all candidate parameters</p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-6 items-center pt-2">
            
            <div className="md:col-span-2 flex items-center gap-3">
              <div className="w-12 h-12 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 font-bold flex items-center justify-center text-sm">
                {newCandidate.name.split(' ').map(n=>n[0]).join('')}
              </div>
              <div>
                <h4 className="text-sm font-bold text-white">{newCandidate.name}</h4>
                <p className="text-xs text-slate-400">{newCandidate.currentRole} at {newCandidate.currentCompany}</p>
                <span className="text-[10px] text-slate-500 block mt-0.5">{newCandidate.location}</span>
              </div>
            </div>

            <div className="flex gap-4 items-center">
              <div>
                <span className="text-[10px] uppercase text-slate-500 font-semibold block">Match Rating</span>
                <span className="text-xl font-extrabold text-emerald-400">{newCandidate.matchScore}%</span>
              </div>
              <div>
                <span className="text-[10px] uppercase text-slate-500 font-semibold block">Extracted Nodes</span>
                <span className="text-xl font-extrabold text-white">{newCandidate.relationshipCount}</span>
              </div>
            </div>

            <div className="flex flex-col sm:flex-row gap-2.5 justify-end">
              <button
                onClick={() => navigate(`/candidate/${newCandidate.id}`)}
                className="bg-brand-600 hover:bg-brand-700 text-white font-semibold text-xs py-2 px-4 rounded-xl flex items-center justify-center gap-1 transition-colors"
              >
                <User size={14} />
                <span>View Profile</span>
              </button>
              <button
                onClick={() => navigate('/graph')}
                className="bg-slate-800 hover:bg-slate-700 text-slate-300 font-semibold text-xs py-2 px-4 rounded-xl border border-dark-border flex items-center justify-center gap-1 transition-colors"
              >
                <GitFork size={14} />
                <span>Open Graph</span>
              </button>
            </div>

          </div>
        </section>
      )}

      <section className="glass-panel rounded-2xl p-6 space-y-4 border border-dark-border/80">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div className="flex items-center gap-2">
            <Mail size={18} className="text-brand-400" />
            <div>
              <h2 className="text-base font-bold text-white">Import resumes from Gmail</h2>
              <p className="text-xs text-slate-400">
                Search resume-related mail, review PDF attachments, then import selected files through the existing parser.
              </p>
            </div>
          </div>
          {gmailConnected ? (
            <span className="text-[11px] font-semibold text-emerald-400">Gmail connected (read-only)</span>
          ) : (
            <button
              onClick={connectGmail}
              className="bg-brand-600 hover:bg-brand-700 text-white font-semibold text-xs py-2 px-4 rounded-xl text-center"
            >
              Connect Gmail
            </button>
          )}
        </div>

        <div className="flex flex-col sm:flex-row gap-2">
          <input
            type="search"
            value={gmailQuery}
            onChange={(e) => setGmailQuery(e.target.value)}
            placeholder='Search Gmail, e.g. filename:pdf subject:resume'
            className="flex-1 bg-slate-900 border border-dark-border rounded-xl px-3 py-2.5 text-sm text-white placeholder:text-slate-500"
            disabled={!gmailConnected || gmailSearching}
          />
          <button
            type="button"
            onClick={searchGmail}
            disabled={!gmailConnected || gmailSearching}
            className="bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-white font-semibold text-xs py-2.5 px-4 rounded-xl border border-dark-border"
          >
            {gmailSearching ? 'Searching...' : 'Search resume emails'}
          </button>
        </div>

        {gmailError && (
          <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex items-start gap-2">
            <AlertCircle size={16} className="shrink-0 mt-0.5" />
            <span>{gmailError}</span>
          </div>
        )}

        <div className="space-y-3">
          {gmailEmails.map((email) => (
            <div key={email.id} className="rounded-xl border border-dark-border bg-slate-950/40 p-4 space-y-3">
              <div>
                <h3 className="text-sm font-bold text-white">{email.subject || '(no subject)'}</h3>
                <p className="text-xs text-slate-400">{email.sender}</p>
                <p className="text-[11px] text-slate-500">{email.date}</p>
              </div>
              {email.attachments.length === 0 ? (
                <p className="text-xs text-slate-500">No attachments on this message.</p>
              ) : (
                <ul className="space-y-2">
                  {email.attachments.map((attachment) => {
                    const disabled = attachment.already_imported
                      || attachment.classification !== 'RESUME';
                    const key = attachmentKey(attachment.message_id, attachment.attachment_id);
                    return (
                      <li key={key} className="flex items-start gap-2 text-xs text-slate-300">
                        <input
                          type="checkbox"
                          className="mt-0.5"
                          checked={Boolean(selectedAttachments[key])}
                          disabled={disabled || gmailImporting}
                          onChange={() => toggleAttachment(attachment.message_id, attachment.attachment_id, disabled)}
                        />
                        <div>
                          <span className="font-semibold text-white">{attachment.filename}</span>
                          <span className="text-slate-500"> · {attachment.mime_type || 'unknown type'}</span>
                          {attachment.already_imported && (
                            <span className="block text-amber-400">Already imported</span>
                          )}
                          {attachment.classification !== 'RESUME' && (
                            <span className="block text-rose-400">Only attachments classified as resumes can be imported</span>
                          )}
                        </div>
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>
          ))}
        </div>

        {gmailEmails.length > 0 && (
          <button
            type="button"
            onClick={importSelectedGmailResumes}
            disabled={gmailImporting}
            className="w-full sm:w-auto bg-brand-600 hover:bg-brand-700 disabled:opacity-50 text-white font-semibold text-xs py-2.5 px-4 rounded-xl"
          >
            {gmailImporting ? 'Importing...' : 'Import selected PDFs'}
          </button>
        )}
      </section>

    </div>
  );
};

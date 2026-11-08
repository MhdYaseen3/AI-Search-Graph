import React, { useState, useEffect } from 'react';
import {
  Mail,
  CheckCircle,
  AlertCircle,
  Loader2,
  FileText,
  Download,
  RefreshCw,
  History,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { gmailService } from '../services/api';
import type {
  GmailAttachment as GmailAttachmentData,
  GmailImportHistoryItem,
} from '../types';

type AttachmentClassification = NonNullable<GmailAttachmentData['classification']>;
type GmailAttachment = GmailAttachmentData & {
  classification: AttachmentClassification;
  confidence: number;
  classification_reason: string;
};

export const GmailImport: React.FC = () => {
  const [status, setStatus] = useState<'idle' | 'connecting' | 'connected' | 'searching' | 'importing'>('idle');
  const [configured, setConfigured] = useState<boolean>(false);
  const [state, setState] = useState<string | null>(null);
  const [attachments, setAttachments] = useState<GmailAttachment[]>([]);
  const [selectedAttachments, setSelectedAttachments] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [importResults, setImportResults] = useState<{
    success: number;
    failed: number;
    duplicates: number;
    errors: string[];
  } | null>(null);
  const [importHistory, setImportHistory] = useState<GmailImportHistoryItem[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [retryingImport, setRetryingImport] = useState<string | null>(null);
  const [classificationOverrides, setClassificationOverrides] = useState<
    Record<string, AttachmentClassification>
  >({});
  const [showExcluded, setShowExcluded] = useState(true);
  const [reviewedUncertain, setReviewedUncertain] = useState<Set<string>>(new Set());
  const [hasSearched, setHasSearched] = useState(false);

  const attachmentKey = (attachment: GmailAttachment) =>
    `${attachment.message_id}_${attachment.attachment_id}`;
  const effectiveClassification = (attachment: GmailAttachment) =>
    classificationOverrides[attachmentKey(attachment)] || attachment.classification;

  const refreshImportHistory = async () => {
    setHistoryLoading(true);
    setHistoryError(null);
    try {
      setImportHistory(await gmailService.getImportHistory());
    } catch (err: unknown) {
      setHistoryError(err instanceof Error ? err.message : 'Failed to load import history.');
    } finally {
      setHistoryLoading(false);
    }
  };

  const retryImport = async (item: GmailImportHistoryItem) => {
    if (!state) {
      setError('Reconnect Gmail before retrying this attachment.');
      return;
    }
    const key = `${item.message_id}:${item.attachment_id}`;
    setRetryingImport(key);
    setError(null);
    try {
      const response = await gmailService.retryFailedImport(
        state,
        item.message_id,
        item.attachment_id,
      );
      if (response.success_count > 0) {
        setSuccess(`Retried ${item.filename} successfully.`);
      } else {
        setError(response.errors[0] || 'The attachment retry did not complete.');
      }
      await refreshImportHistory();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to retry attachment.');
      await refreshImportHistory();
    } finally {
      setRetryingImport(null);
    }
  };

  useEffect(() => {
    let active = true;
    gmailService.getImportHistory().then((history) => {
      if (active) setImportHistory(history);
    }).catch((err: unknown) => {
      if (active) {
        setHistoryError(err instanceof Error ? err.message : 'Failed to load import history.');
      }
    });
    const savedState = sessionStorage.getItem('gmailOAuthState');
    gmailService.getStatus(savedState || undefined).then((data) => {
      if (!active) return;
      setConfigured(data.configured);
      if (data.connected && savedState) {
        setState(savedState);
        setStatus('connected');
      } else {
        sessionStorage.removeItem('gmailOAuthState');
        setState(null);
        setStatus('idle');
      }
    }).catch((err: unknown) => {
      if (!active) return;
      console.error('Failed to check Gmail status', err);
      setConfigured(false);
    });
    return () => {
      active = false;
    };
  }, []);

  const connectGmail = async () => {
    setStatus('connecting');
    setError(null);
    try {
      const nextState = await gmailService.connect();
      sessionStorage.setItem('gmailOAuthState', nextState);
      setState(nextState);
      setStatus('connected');
      setSuccess('Gmail connected successfully');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to connect to Gmail');
      setStatus('idle');
    }
  };

  const searchEmails = async () => {
    if (!state) {
      setError('Not authenticated. Please connect Gmail first.');
      return;
    }

    setStatus('searching');
    setError(null);
    setSuccess(null);
    try {
      const results = await gmailService.searchResumeEmails(state);
      const data: GmailAttachment[] = results.map((attachment) => ({
        ...attachment,
        classification: attachment.classification || 'UNCERTAIN',
        confidence: attachment.confidence ?? 0,
        classification_reason:
          attachment.classification_reason || 'Classification details unavailable.',
      }));
      setAttachments(data);
      setSelectedAttachments(new Set());
      setClassificationOverrides({});
      setReviewedUncertain(new Set());
      setHasSearched(true);
      setStatus('connected');
      setSuccess(`Reviewed ${data.length} supported attachments. Nothing is imported until you choose Import Selected.`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to search emails');
      setStatus('connected');
    }
  };

  const toggleSelection = (attachmentId: string) => {
    const newSelection = new Set(selectedAttachments);
    if (newSelection.has(attachmentId)) {
      newSelection.delete(attachmentId);
    } else {
      newSelection.add(attachmentId);
    }
    setSelectedAttachments(newSelection);
  };

  const eligibleResumes = attachments.filter(
    (attachment) => effectiveClassification(attachment) === 'RESUME',
  );
  const selectedForImport = attachments.filter((attachment) => {
    const key = attachmentKey(attachment);
    const classification = effectiveClassification(attachment);
    return selectedAttachments.has(key)
      && classification !== 'NON_RESUME'
      && (classification !== 'UNCERTAIN' || reviewedUncertain.has(key));
  });

  const selectAllEligible = () => {
    setSelectedAttachments(new Set(eligibleResumes.map(attachmentKey)));
  };

  const deselectAll = () => setSelectedAttachments(new Set());

  const toggleReview = (attachment: GmailAttachment) => {
    const key = attachmentKey(attachment);
    const isReviewed = reviewedUncertain.has(key);
    const next = new Set(reviewedUncertain);
    if (isReviewed) next.delete(key);
    else next.add(key);
    setReviewedUncertain(next);
    if (isReviewed) {
      setSelectedAttachments((current) => {
        const next = new Set(current);
        next.delete(key);
        return next;
      });
    }
  };

  const importSelected = async () => {
    if (selectedForImport.length === 0) {
      setError('No attachments selected');
      return;
    }

    if (!state) {
      setError('Not authenticated');
      return;
    }

    setStatus('importing');
    setError(null);
    setSuccess(null);

    try {
      const data = await gmailService.importAttachments(
        state,
        selectedForImport.map((attachment) => ({
          ...attachment,
          classification: effectiveClassification(attachment),
        })),
      );
      setImportResults({
        success: data.success_count,
        failed: data.failure_count,
        duplicates: data.results.filter((item) => item.status === 'DUPLICATE').length,
        errors: data.errors,
      });
      await refreshImportHistory();
      if (data.failure_count > 0) {
        setError(`${data.failure_count} attachment${data.failure_count === 1 ? '' : 's'} could not be imported. See details below.`);
      }
      if (data.success_count > 0) {
        setSuccess(`Imported ${data.success_count} resume${data.success_count === 1 ? '' : 's'} successfully.`);
      } else if (data.failure_count === 0) {
        setSuccess('Import completed. No resumes were imported.');
      }
      setStatus('connected');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to import attachments');
      setStatus('connected');
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const formatReceivedDate = (date: string) => {
    const parsedDate = new Date(date);
    return Number.isNaN(parsedDate.getTime())
      ? date || 'Date unavailable'
      : parsedDate.toLocaleString();
  };

  const renderAttachment = (attachment: GmailAttachment) => {
    const key = attachmentKey(attachment);
    const isSelected = selectedAttachments.has(key);
    const classification = effectiveClassification(attachment);
    const isUncertain = classification === 'UNCERTAIN';
    const isReviewed = reviewedUncertain.has(key);
    const canSelect = classification !== 'NON_RESUME'
      && (!isUncertain || isReviewed);
    const color = classification === 'RESUME'
      ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300'
      : classification === 'NON_RESUME'
        ? 'border-red-500/30 bg-red-500/10 text-red-300'
        : 'border-amber-500/30 bg-amber-500/10 text-amber-300';

    return (
      <article key={key} className="rounded-xl border border-dark-border bg-slate-900 p-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start">
          <div className="flex min-w-0 flex-1 items-start gap-3">
            {canSelect && (
              <input
                type="checkbox"
                aria-label={`Select ${attachment.filename} for import`}
                checked={isSelected}
                onChange={() => toggleSelection(key)}
                disabled={status === 'importing'}
                className="mt-1 h-4 w-4 shrink-0 accent-emerald-500"
              />
            )}
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <FileText size={16} className="shrink-0 text-slate-400" />
                <span className="truncate text-sm font-semibold text-white">{attachment.filename}</span>
                <span className={`rounded-full border px-2 py-0.5 text-[10px] font-bold ${color}`}>
                  {classification.replace('_', ' ')}
                </span>
                <span className="text-xs font-semibold text-slate-300">
                  {Math.round(attachment.confidence * 100)}% confidence
                </span>
              </div>
              <dl className="mt-2 grid gap-x-4 gap-y-1 text-xs text-slate-400 sm:grid-cols-2">
                <div>
                  <dt className="inline font-semibold text-slate-300">From: </dt>
                  <dd className="inline break-all">{attachment.sender}</dd>
                </div>
                <div>
                  <dt className="inline font-semibold text-slate-300">Received: </dt>
                  <dd className="inline">{formatReceivedDate(attachment.date)}</dd>
                </div>
                <div className="sm:col-span-2">
                  <dt className="inline font-semibold text-slate-300">Subject: </dt>
                  <dd className="inline">{attachment.subject || 'No subject'}</dd>
                </div>
                <div>
                  <dt className="inline font-semibold text-slate-300">File size: </dt>
                  <dd className="inline">{formatFileSize(attachment.size)}</dd>
                </div>
              </dl>
              <p className="mt-2 text-xs text-slate-400">
                <span className="font-semibold text-slate-300">Reason: </span>
                {classificationOverrides[key]
                  ? 'Manually classified by recruiter.'
                  : attachment.classification_reason}
              </p>
              {isUncertain && (
                <button
                  type="button"
                  onClick={() => toggleReview(attachment)}
                  disabled={status === 'importing'}
                  className="mt-3 rounded-lg border border-amber-500/30 px-3 py-1.5 text-xs font-semibold text-amber-300 hover:bg-amber-500/10"
                >
                  {isReviewed ? 'Undo review' : 'Review attachment'}
                </button>
              )}
            </div>
          </div>
          <div className="sm:pl-2">
            <label className="sr-only" htmlFor={`classification-${key}`}>
              Override classification for {attachment.filename}
            </label>
            <select
              id={`classification-${key}`}
              value={classification}
              disabled={status === 'importing'}
              onChange={(event) => {
                const nextClassification = event.target.value as AttachmentClassification;
                setClassificationOverrides((current) => {
                  const next = { ...current };
                  if (nextClassification === attachment.classification) {
                    delete next[key];
                  } else {
                    next[key] = nextClassification;
                  }
                  return next;
                });
                if (
                  nextClassification === 'NON_RESUME'
                  || (nextClassification === 'UNCERTAIN' && !reviewedUncertain.has(key))
                ) {
                  setSelectedAttachments((selected) => {
                    const updated = new Set(selected);
                    updated.delete(key);
                    return updated;
                  });
                }
              }}
              className="w-full rounded-lg border border-dark-border bg-slate-800 px-2 py-1.5 text-xs text-white sm:w-auto"
            >
              <option value="RESUME">Override: Resume</option>
              <option value="UNCERTAIN">Override: Review</option>
              <option value="NON_RESUME">Override: Not a resume</option>
            </select>
          </div>
        </div>
      </article>
    );
  };

  const resumes = attachments
    .filter((attachment) => effectiveClassification(attachment) === 'RESUME')
    .sort((left, right) => right.confidence - left.confidence);
  const uncertain = attachments.filter(
    (attachment) => effectiveClassification(attachment) === 'UNCERTAIN',
  );
  const excluded = attachments.filter(
    (attachment) => effectiveClassification(attachment) === 'NON_RESUME',
  );

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Header */}
      <div className="space-y-2">
        <h1 className="text-2xl lg:text-3xl font-extrabold text-white tracking-tight">
          Gmail Resume Import
        </h1>
        <p className="text-sm text-slate-400">
          Connect Gmail to find and import resume attachments from your inbox.
        </p>
      </div>

      {/* Configuration Warning */}
      {!configured && (
        <div className="glass-panel rounded-2xl p-6 border border-yellow-500/30 bg-yellow-500/5">
          <div className="flex items-start gap-3">
            <AlertCircle className="text-yellow-500 shrink-0 mt-0.5" size={20} />
            <div className="space-y-2">
              <h3 className="text-sm font-bold text-yellow-500 uppercase tracking-wider">
                Gmail OAuth Not Configured
              </h3>
              <p className="text-xs text-slate-300 leading-relaxed">
                To use Gmail import, you must configure Google OAuth credentials:
              </p>
              <ul className="text-xs text-slate-400 space-y-1 list-disc list-inside">
                <li>Create a Google Cloud project at console.cloud.google.com</li>
                <li>Enable Gmail API</li>
                <li>Create OAuth 2.0 credentials (Web application)</li>
                <li>Add redirect URI: http://localhost:8000/api/v1/gmail/callback</li>
                <li>Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in backend .env</li>
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Actions */}
      {configured && (
        <div className="flex flex-wrap gap-3">
          {(status === 'idle' || status === 'connecting') && (
            <button
              onClick={connectGmail}
              disabled={status === 'connecting'}
              className="px-4 py-2.5 rounded-xl text-sm font-semibold bg-brand-600 hover:bg-brand-500 text-white transition-all duration-150 flex items-center gap-2"
            >
              {status === 'connecting'
                ? <Loader2 size={16} className="animate-spin" />
                : <Mail size={16} />}
              {status === 'connecting' ? 'Connecting...' : 'Connect Gmail'}
            </button>
          )}

          {(status === 'connected' || status === 'searching' || status === 'importing') && (
            <>
              <button
                onClick={searchEmails}
                disabled={status === 'importing' || status === 'searching'}
                className="px-4 py-2.5 rounded-xl text-sm font-semibold bg-slate-800 hover:bg-slate-700 text-white transition-all duration-150 flex items-center gap-2 disabled:opacity-50"
              >
                {status === 'searching' ? (
                  <Loader2 size={16} className="animate-spin" />
                ) : (
                  <RefreshCw size={16} />
                )}
                Search Emails
              </button>

            </>
          )}
        </div>
      )}

      {(status === 'connected' || status === 'importing') && attachments.length > 0 && (
        <section className="glass-panel flex flex-col gap-3 rounded-2xl border border-dark-border p-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm font-semibold text-white">
              {selectedForImport.length} resume{selectedForImport.length === 1 ? '' : 's'} selected
            </p>
            <p className="text-xs text-slate-400">
              Attachments are never imported automatically.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={selectAllEligible}
              disabled={eligibleResumes.length === 0 || status === 'importing'}
              className="rounded-lg border border-dark-border px-3 py-2 text-xs font-semibold text-slate-200 hover:bg-slate-800 disabled:opacity-50"
            >
              Select all eligible resumes
            </button>
            <button
              type="button"
              onClick={deselectAll}
              disabled={selectedAttachments.size === 0 || status === 'importing'}
              className="rounded-lg border border-dark-border px-3 py-2 text-xs font-semibold text-slate-200 hover:bg-slate-800 disabled:opacity-50"
            >
              Deselect all
            </button>
            <button
              type="button"
              onClick={importSelected}
              disabled={selectedForImport.length === 0 || status === 'importing'}
              className="rounded-xl bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-500 disabled:opacity-50"
            >
              {status === 'importing' ? (
                <span className="flex items-center gap-2">
                  <Loader2 size={16} className="animate-spin" />Importing...
                </span>
              ) : (
                <span className="flex items-center gap-2">
                  <Download size={16} />Import Selected
                </span>
              )}
            </button>
          </div>
        </section>
      )}

      {/* Status Messages */}
      {error && (
        <div className="glass-panel rounded-2xl p-4 border border-red-500/30 bg-red-500/5 text-red-400 text-sm flex items-center gap-2">
          <AlertCircle size={16} />
          {error}
        </div>
      )}

      {success && (
        <div className="glass-panel rounded-2xl p-4 border border-emerald-500/30 bg-emerald-500/5 text-emerald-400 text-sm flex items-center gap-2">
          <CheckCircle size={16} />
          {success}
        </div>
      )}

      {/* Import Results */}
      {importResults && (
        <div className="glass-panel rounded-2xl p-4 border border-dark-border space-y-2">
          <h3 className="text-sm font-bold text-white uppercase tracking-wider">Import Results</h3>
          <div className="flex gap-4 text-xs">
            <span className="text-emerald-400">Success: {importResults.success}</span>
            <span className="text-red-400">Failed: {importResults.failed}</span>
            <span className="text-amber-300">Duplicates: {importResults.duplicates}</span>
          </div>
          {importResults.errors.length > 0 && (
            <div className="text-xs text-slate-400 space-y-1">
              {importResults.errors.map((err, i) => (
                <div key={i} className="text-red-400">• {err}</div>
              ))}
            </div>
          )}
        </div>
      )}

      <section className="glass-panel rounded-2xl border border-dark-border p-5 sm:p-6">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <History size={17} className="text-brand-300" />
            <h3 className="text-sm font-bold uppercase tracking-wider text-white">
              Gmail Import History
            </h3>
          </div>
          <button
            type="button"
            onClick={refreshImportHistory}
            disabled={historyLoading}
            className="flex items-center gap-2 rounded-lg border border-dark-border px-3 py-2 text-xs font-semibold text-slate-200 hover:bg-slate-800 disabled:opacity-50"
          >
            <RefreshCw size={14} className={historyLoading ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>
        {historyError && (
          <p role="alert" className="mb-3 text-xs text-red-400">{historyError}</p>
        )}
        {historyLoading && importHistory.length === 0 ? (
          <p role="status" className="text-xs text-slate-400">Loading import history...</p>
        ) : importHistory.length === 0 ? (
          <p className="text-xs text-slate-400">No Gmail import attempts recorded.</p>
        ) : (
          <div className="space-y-2">
            {importHistory.map((item) => {
              const statusColor = item.status === 'SUCCESS'
                ? 'text-emerald-300 bg-emerald-500/10 border-emerald-500/30'
                : item.status === 'FAILED'
                  ? 'text-red-300 bg-red-500/10 border-red-500/30'
                  : item.status === 'DUPLICATE'
                    ? 'text-amber-300 bg-amber-500/10 border-amber-500/30'
                    : 'text-sky-300 bg-sky-500/10 border-sky-500/30';
              return (
                <article
                  key={`${item.message_id}:${item.attachment_id}`}
                  className="flex flex-col gap-2 rounded-xl border border-dark-border bg-slate-900 p-3 sm:flex-row sm:items-center sm:justify-between"
                >
                  <div className="min-w-0">
                    <p className="truncate text-sm font-semibold text-white">{item.filename}</p>
                    <p className="mt-1 text-xs text-slate-400">
                      {item.candidate_id && item.candidate_name ? (
                        <Link className="text-brand-300 hover:underline" to={`/candidate/${item.candidate_id}`}>
                          {item.candidate_name}
                        </Link>
                      ) : item.candidate_id ? (
                        <Link className="text-brand-300 hover:underline" to={`/candidate/${item.candidate_id}`}>
                          View candidate
                        </Link>
                      ) : 'Candidate not created'}
                      {item.imported_at && ` · ${new Date(item.imported_at).toLocaleString()}`}
                    </p>
                    {item.failure_reason && (
                      <p className="mt-1 text-xs text-red-300">{item.failure_reason}</p>
                    )}
                  </div>
                    <div className="flex shrink-0 items-center gap-2">
                      <span className={`w-fit rounded-full border px-2.5 py-1 text-[10px] font-bold ${statusColor}`}>
                        {item.status}
                      </span>
                      {(item.status === 'FAILED' || item.status === 'PENDING') && (
                        <button
                          type="button"
                          onClick={() => retryImport(item)}
                          disabled={!state || retryingImport !== null}
                          className="rounded-lg border border-dark-border px-3 py-1.5 text-xs font-semibold text-slate-200 hover:bg-slate-800 disabled:opacity-50"
                        >
                          {retryingImport === `${item.message_id}:${item.attachment_id}`
                            ? 'Retrying...'
                            : 'Retry'}
                        </button>
                      )}
                    </div>
                </article>
              );
            })}
          </div>
        )}
      </section>

      {/* Classified attachments */}
      {attachments.length > 0 && (
        <div className="glass-panel rounded-2xl p-6 border border-dark-border space-y-4">
          <div>
            <h3 className="text-sm font-bold text-white uppercase tracking-wider">
              Likely Resumes ({resumes.length})
            </h3>
            <p className="text-xs text-slate-400 mt-1">Highest-confidence matches are shown first.</p>
            {resumes.length > 0
              ? <div className="mt-3 space-y-3">{resumes.map(renderAttachment)}</div>
              : <p className="mt-3 text-xs text-slate-400">No likely resumes in this search.</p>}
          </div>

          {uncertain.length > 0 && (
            <div>
              <h3 className="text-sm font-bold text-amber-400 uppercase tracking-wider">
                Needs Review ({uncertain.length})
              </h3>
              <p className="mt-1 text-xs text-slate-400">Review each uncertain attachment before selecting it.</p>
              <div className="mt-3 space-y-3">{uncertain.map(renderAttachment)}</div>
            </div>
          )}

          {excluded.length > 0 && (
            <div>
              <button
                type="button"
                onClick={() => setShowExcluded(!showExcluded)}
                className="text-sm font-bold text-slate-400 uppercase tracking-wider"
              >
                {showExcluded ? 'Hide' : 'Show'} NON-RESUME attachments ({excluded.length})
              </button>
              {showExcluded && (
                <div className="mt-3 space-y-3">{excluded.map(renderAttachment)}</div>
              )}
            </div>
          )}
        </div>
      )}

      {configured && status === 'searching' && (
        <div role="status" className="glass-panel flex items-center justify-center gap-3 rounded-2xl border border-dark-border p-10 text-sm text-slate-300">
          <Loader2 size={18} className="animate-spin" />
          Searching Gmail and preparing attachments for review...
        </div>
      )}

      {configured && status === 'importing' && (
        <div role="status" className="glass-panel flex items-center justify-center gap-3 rounded-2xl border border-dark-border p-6 text-sm text-slate-300">
          <Loader2 size={18} className="animate-spin" />
          Importing only the attachments you selected...
        </div>
      )}

      {/* Empty and initial states */}
      {configured && status === 'connected' && hasSearched && attachments.length === 0 && !error && (
        <div className="glass-panel rounded-2xl border border-dark-border p-12 text-center">
          <Mail size={48} className="text-slate-600 mx-auto mb-4" />
          <h3 className="text-sm font-bold text-white uppercase tracking-wider mb-2">
            No Attachments Found
          </h3>
          <p className="text-xs text-slate-400">
            No supported PDF or Word attachments were found. Try searching again later.
          </p>
        </div>
      )}
      {configured && status === 'connected' && !hasSearched && !error && (
        <div className="glass-panel rounded-2xl border border-dark-border p-10 text-center">
          <Mail size={36} className="mx-auto mb-3 text-slate-600" />
          <p className="text-sm font-semibold text-white">Ready to review Gmail attachments</p>
          <p className="mt-1 text-xs text-slate-400">
            Search your inbox to classify attachments. Nothing will be imported until you select files and confirm.
          </p>
        </div>
      )}
    </div>
  );
};

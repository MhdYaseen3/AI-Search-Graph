import React, { useState } from 'react';
import { X, Plus, AlertCircle, Loader2 } from 'lucide-react';
import type { CreateJobInput, EmploymentType, JobStatus } from '../types';

interface CreateJobFormProps {
  onSubmit: (input: CreateJobInput) => Promise<void>;
  isSubmitting?: boolean;
  onCancel?: () => void;
}

export const CreateJobForm: React.FC<CreateJobFormProps> = ({
  onSubmit,
  isSubmitting = false,
  onCancel
}) => {
  const [formData, setFormData] = useState<CreateJobInput>({
    title: '',
    description: '',
    requiredSkills: [],
    experience: 0,
    location: '',
    employmentType: 'Full-time' as EmploymentType,
    salary: {
      min: undefined,
      max: undefined,
      currency: 'USD'
    },
    status: 'Active' as JobStatus
  });

  const [skillInput, setSkillInput] = useState('');
  const [error, setError] = useState<string | null>(null);

  const handleInputChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>
  ) => {
    const { name, value } = e.target;

    if (name.startsWith('salary.')) {
      const salaryKey = name.split('.')[1] as keyof NonNullable<CreateJobInput['salary']>;
      setFormData
      (prev => ({
        ...prev,
        salary: {
          ...prev.salary,
          [salaryKey]: salaryKey === 'currency' ? value : (value ? parseFloat(value) : undefined)
        }
      }));
    } else if (name === 'experience') {
      setFormData(prev => ({
        ...prev,
        [name]: parseInt(value) || 0
      }));
    } else {
      setFormData(prev => ({
        ...prev,
        [name]: value
      }));
    }

    // Clear error when user starts typing
    if (error) setError(null);
  };

  const handleAddSkill = () => {
    const skill = skillInput.trim();
    if (!skill) return;

    if (formData.requiredSkills.includes(skill)) {
      setError('Skill already added');
      return;
    }

    if (formData.requiredSkills.length >= 10) {
      setError('Maximum 10 skills allowed');
      return;
    }

    setFormData(prev => ({
      ...prev,
      requiredSkills: [...prev.requiredSkills, skill]
    }));
    setSkillInput('');
  };

  const handleRemoveSkill = (skillToRemove: string) => {
    setFormData(prev => ({
      ...prev,
      requiredSkills: prev.requiredSkills.filter(s => s !== skillToRemove)
    }));
  };

  const validateForm = (): boolean => {
    if (!formData.title.trim()) {
      setError('Job title is required');
      return false;
    }
    if (!formData.description.trim()) {
      setError('Job description is required');
      return false;
    }
    if (formData.requiredSkills.length === 0) {
      setError('Add at least one required skill');
      return false;
    }
    if (formData.experience < 0) {
      setError('Experience cannot be negative');
      return false;
    }
    if (!formData.location.trim()) {
      setError('Location is required');
      return false;
    }
    return true;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!validateForm()) {
      return;
    }

    try {
      await onSubmit(formData);
    } catch (err: any) {
      setError(err?.message || 'Failed to create job. Please try again.');
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* ERROR MESSAGE */}
      {error && (
        <div className="flex items-center gap-3 px-4 py-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}

      {/* FORM FIELDS */}
      <div className="space-y-4">
        {/* Job Title */}
        <div>
          <label htmlFor="title" className="block text-sm font-semibold text-slate-200 mb-2">
            Job Title <span className="text-red-400">*</span>
          </label>
          <input
            id="title"
            name="title"
            type="text"
            placeholder="e.g. Senior ML Engineer"
            value={formData.title}
            onChange={handleInputChange}
            className="w-full px-4 py-3 rounded-lg bg-slate-900 border border-dark-border focus:border-brand-500 text-slate-100 placeholder-slate-500 outline-none transition-colors"
          />
        </div>

        {/* Job Description */}
        <div>
          <label htmlFor="description" className="block text-sm font-semibold text-slate-200 mb-2">
            Job Description <span className="text-red-400">*</span>
          </label>
          <textarea
            id="description"
            name="description"
            placeholder="Describe the role, responsibilities, and key challenges..."
            rows={5}
            value={formData.description}
            onChange={handleInputChange}
            className="w-full px-4 py-3 rounded-lg bg-slate-900 border border-dark-border focus:border-brand-500 text-slate-100 placeholder-slate-500 outline-none transition-colors resize-none"
          />
        </div>

        {/* Required Skills */}
        <div>
          <label htmlFor="skills" className="block text-sm font-semibold text-slate-200 mb-2">
            Required Skills <span className="text-red-400">*</span>
          </label>
          <div className="space-y-3">
            {/* Skill Input */}
            <div className="flex gap-2">
              <input
                id="skills"
                type="text"
                placeholder="Add a skill (e.g. Python, React, Docker)"
                value={skillInput}
                onChange={(e) => {
                  setSkillInput(e.target.value);
                  if (error?.includes('Skill')) setError(null);
                }}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    handleAddSkill();
                  }
                }}
                className="flex-1 px-4 py-3 rounded-lg bg-slate-900 border border-dark-border focus:border-brand-500 text-slate-100 placeholder-slate-500 outline-none transition-colors"
              />
              <button
                type="button"
                onClick={handleAddSkill}
                className="px-4 py-3 rounded-lg bg-brand-600 hover:bg-brand-700 text-white font-semibold text-sm transition-colors flex items-center gap-2"
              >
                <Plus size={16} />
                Add
              </button>
            </div>

            {/* Skills List */}
            {formData.requiredSkills.length > 0 && (
              <div className="flex flex-wrap gap-2 p-3 rounded-lg bg-slate-900/50 border border-brand-500/20">
                {formData.requiredSkills.map((skill) => (
                  <div
                    key={skill}
                    className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-brand-600/20 border border-brand-500/30 text-brand-400 text-sm"
                  >
                    <span>{skill}</span>
                    <button
                      type="button"
                      onClick={() => handleRemoveSkill(skill)}
                      className="p-0.5 hover:bg-brand-600/30 rounded transition-colors"
                    >
                      <X size={14} />
                    </button>
                  </div>
                ))}
              </div>
            )}

            <p className="text-xs text-slate-500">
              {formData.requiredSkills.length}/10 skills added
            </p>
          </div>
        </div>

        {/* Experience and Location Row */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="experience" className="block text-sm font-semibold text-slate-200 mb-2">
              Years of Experience Required <span className="text-red-400">*</span>
            </label>
            <input
              id="experience"
              name="experience"
              type="number"
              min="0"
              max="50"
              placeholder="e.g. 5"
              value={formData.experience}
              onChange={handleInputChange}
              className="w-full px-4 py-3 rounded-lg bg-slate-900 border border-dark-border focus:border-brand-500 text-slate-100 placeholder-slate-500 outline-none transition-colors"
            />
          </div>

          <div>
            <label htmlFor="location" className="block text-sm font-semibold text-slate-200 mb-2">
              Location <span className="text-red-400">*</span>
            </label>
            <input
              id="location"
              name="location"
              type="text"
              placeholder="e.g. San Francisco, CA"
              value={formData.location}
              onChange={handleInputChange}
              className="w-full px-4 py-3 rounded-lg bg-slate-900 border border-dark-border focus:border-brand-500 text-slate-100 placeholder-slate-500 outline-none transition-colors"
            />
          </div>
        </div>

        {/* Employment Type and Status Row */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="employmentType" className="block text-sm font-semibold text-slate-200 mb-2">
              Employment Type <span className="text-red-400">*</span>
            </label>
            <select
              id="employmentType"
              name="employmentType"
              value={formData.employmentType}
              onChange={handleInputChange}
              className="w-full px-4 py-3 rounded-lg bg-slate-900 border border-dark-border focus:border-brand-500 text-slate-100 outline-none transition-colors cursor-pointer"
            >
              <option value="Full-time">Full-time</option>
              <option value="Part-time">Part-time</option>
              <option value="Contract">Contract</option>
              <option value="Temporary">Temporary</option>
              <option value="Freelance">Freelance</option>
            </select>
          </div>

          <div>
            <label htmlFor="status" className="block text-sm font-semibold text-slate-200 mb-2">
              Status <span className="text-red-400">*</span>
            </label>
            <select
              id="status"
              name="status"
              value={formData.status}
              onChange={handleInputChange}
              className="w-full px-4 py-3 rounded-lg bg-slate-900 border border-dark-border focus:border-brand-500 text-slate-100 outline-none transition-colors cursor-pointer"
            >
              <option value="Active">Active</option>
              <option value="Closed">Closed</option>
            </select>
          </div>
        </div>

        {/* Salary Section */}
        <div className="space-y-3 p-4 rounded-lg bg-slate-900/50 border border-dark-border/50">
          <h3 className="text-sm font-semibold text-slate-200">Salary Range (Optional)</h3>

          <div className="grid grid-cols-3 gap-3">
            <div>
              <label htmlFor="salary.min" className="block text-xs font-medium text-slate-400 mb-2">
                Min Salary
              </label>
              <input
                id="salary.min"
                name="salary.min"
                type="number"
                placeholder="100000"
                value={formData.salary?.min || ''}
                onChange={handleInputChange}
                className="w-full px-3 py-2 rounded-lg bg-slate-800 border border-dark-border focus:border-brand-500 text-slate-100 placeholder-slate-600 outline-none transition-colors text-sm"
              />
            </div>

            <div>
              <label htmlFor="salary.max" className="block text-xs font-medium text-slate-400 mb-2">
                Max Salary
              </label>
              <input
                id="salary.max"
                name="salary.max"
                type="number"
                placeholder="150000"
                value={formData.salary?.max || ''}
                onChange={handleInputChange}
                className="w-full px-3 py-2 rounded-lg bg-slate-800 border border-dark-border focus:border-brand-500 text-slate-100 placeholder-slate-600 outline-none transition-colors text-sm"
              />
            </div>

            <div>
              <label htmlFor="salary.currency" className="block text-xs font-medium text-slate-400 mb-2">
                Currency
              </label>
              <select
                id="salary.currency"
                name="salary.currency"
                value={formData.salary?.currency || 'USD'}
                onChange={handleInputChange}
                className="w-full px-3 py-2 rounded-lg bg-slate-800 border border-dark-border focus:border-brand-500 text-slate-100 outline-none transition-colors cursor-pointer text-sm"
              >
                <option value="USD">USD</option>
                <option value="EUR">EUR</option>
                <option value="GBP">GBP</option>
                <option value="CAD">CAD</option>
                <option value="AUD">AUD</option>
              </select>
            </div>
          </div>

          <p className="text-xs text-slate-500">
            Leave empty if salary is not disclosed or varies by candidate
          </p>
        </div>
      </div>

      {/* FORM ACTIONS */}
      <div className="flex gap-3 pt-4 border-t border-dark-border/50">
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            disabled={isSubmitting}
            className="flex-1 px-4 py-3 rounded-lg bg-slate-900 border border-dark-border hover:bg-slate-800 text-slate-200 font-semibold text-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Cancel
          </button>
        )}
        <button
          type="submit"
          disabled={isSubmitting}
          className="flex-1 px-4 py-3 rounded-lg bg-brand-600 hover:bg-brand-700 text-white font-semibold text-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
        >
          {isSubmitting ? (
            <>
              <Loader2 size={16} className="animate-spin" />
              Creating...
            </>
          ) : (
            'Create Job'
          )}
        </button>
      </div>
    </form>
  );
};

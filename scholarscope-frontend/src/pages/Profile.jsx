import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';
import Navbar from '../components/Navbar';
import ProfileCompletion from '../components/ProfileCompletion';

import {
  Camera, X, Plus, Check, Loader2, Save,
  User, GraduationCap, BookOpen, Zap, Star, Trash2,
} from 'lucide-react';

// Language proficiency levels — UI only, not stored in DB
const LANGUAGE_LEVELS = ['Native', 'Fluent', 'Advanced', 'Intermediate', 'Basic'];

const inp = "w-full px-3 py-2.5 text-sm border border-slate-200 dark:border-slate-700 rounded-lg bg-white dark:bg-slate-950 text-slate-900 dark:text-white outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary/50 transition placeholder-slate-300 dark:placeholder-slate-600";
const lbl = "text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide";

function SectionCard({ icon: Icon, title, subtitle, iconColor = 'text-primary', iconBg = 'bg-primary/10', children }) {
  return (
    <div className="bg-white dark:bg-slate-900 rounded-xl shadow-sm border border-slate-200 dark:border-slate-800">
      <div className="flex items-center gap-3 px-6 py-4 border-b border-slate-100 dark:border-slate-800">
        <div className={`w-8 h-8 rounded-lg ${iconBg} flex items-center justify-center shrink-0`}>
          <Icon className={`w-4 h-4 ${iconColor}`} />
        </div>
        <div className="min-w-0">
          <h3 className="text-sm font-bold text-slate-900 dark:text-white">{title}</h3>
          {subtitle && <p className="text-xs text-slate-400 mt-0.5 leading-snug">{subtitle}</p>}
        </div>
      </div>
      <div className="p-6">{children}</div>
    </div>
  );
}

function NarrativeField({ label, hint, value, onChange, placeholder, rows = 4 }) {
  return (
    <div className="space-y-1.5">
      <label className={lbl}>{label}</label>
      {hint && <p className="text-xs text-slate-400 leading-relaxed">{hint}</p>}
      <textarea value={value} onChange={onChange} rows={rows} placeholder={placeholder}
        className={`${inp} resize-y leading-relaxed`} />
    </div>
  );
}

function AddDropdown({ label, options, onAdd }) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState('');
  const ref = useRef(null);

  useEffect(() => {
    const h = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener('mousedown', h);
    return () => document.removeEventListener('mousedown', h);
  }, []);

  const filtered = options.filter(o => o.toLowerCase().includes(search.toLowerCase()));

  return (
    <div className="relative" ref={ref}>
      <button type="button" onClick={() => setOpen(v => !v)}
        className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm border border-dashed border-slate-300 dark:border-slate-600 text-slate-500 dark:text-slate-400 hover:border-slate-400 dark:hover:border-slate-500 hover:text-slate-700 dark:hover:text-slate-300 transition">
        <Plus className="w-3 h-3" /> {label}
      </button>
      {open && (
        <div className="absolute z-20 mt-2 w-64 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl shadow-xl overflow-hidden">
          <div className="p-2 border-b border-slate-100 dark:border-slate-800">
            <input autoFocus placeholder="Search…" value={search} onChange={e => setSearch(e.target.value)}
              className="w-full px-3 py-1.5 text-sm bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg outline-none text-slate-900 dark:text-white placeholder-slate-400" />
          </div>
          <div className="max-h-52 overflow-y-auto">
            {filtered.length === 0 && <p className="px-4 py-3 text-xs text-slate-400">No results</p>}
            {filtered.map(o => (
              <button key={o} type="button"
                className="w-full text-left px-4 py-2 text-sm hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300 transition"
                onClick={() => { onAdd(o); setOpen(false); setSearch(''); }}>
                {o}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function SkillInput({ skills, onChange }) {
  const [input, setInput] = useState('');
  const add = () => {
    const v = input.trim();
    if (v && !skills.includes(v)) onChange([...skills, v]);
    setInput('');
  };
  return (
    <div className="flex flex-wrap gap-2 p-3 border border-slate-200 dark:border-slate-700 rounded-lg bg-slate-50 dark:bg-slate-950 focus-within:ring-2 focus-within:ring-primary/30 focus-within:border-primary/50 transition min-h-[44px]">
      {skills.map(s => (
        <span key={s} className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-700/50 text-xs font-medium">
          {s}
          <button type="button" onClick={() => onChange(skills.filter(x => x !== s))} className="hover:text-blue-900">
            <X className="w-2.5 h-2.5" />
          </button>
        </span>
      ))}
      <input className="flex-1 min-w-[140px] bg-transparent outline-none text-sm text-slate-700 dark:text-slate-300 placeholder-slate-400"
        placeholder={skills.length === 0 ? 'Type a skill and press Enter…' : 'Add another…'}
        value={input} onChange={e => setInput(e.target.value)}
        onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); add(); } }} />
    </div>
  );
}

function LanguageRows({ languages, onChange }) {
  return (
    <div className="space-y-2">
      {languages.map((lang, i) => (
        <div key={i} className="flex gap-2 items-center">
          <input className={inp} placeholder="Language" value={lang.language}
            onChange={e => onChange(languages.map((l, idx) => idx === i ? { ...l, language: e.target.value } : l))} />
          <select className={`${inp} w-36 shrink-0`} value={lang.level}
            onChange={e => onChange(languages.map((l, idx) => idx === i ? { ...l, level: e.target.value } : l))}>
            {LANGUAGE_LEVELS.map(l => <option key={l}>{l}</option>)}
          </select>
          <button type="button" onClick={() => onChange(languages.filter((_, idx) => idx !== i))}
            className="p-2 shrink-0 rounded-lg text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition">
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      ))}
      <button type="button" onClick={() => onChange([...languages, { language: '', level: 'Intermediate' }])}
        className="flex items-center gap-1.5 text-sm text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 border border-dashed border-slate-200 dark:border-slate-700 rounded-lg px-4 py-2 w-full justify-center hover:border-slate-300 transition">
        <Plus className="w-3.5 h-3.5" /> Add language
      </button>
    </div>
  );
}

export default function Profile() {
  const navigate = useNavigate();

  const [loading,       setLoading]       = useState(true);
  const [saving,        setSaving]        = useState(false);
  const [toast,         setToast]         = useState(null);
  const [completion,    setCompletion]    = useState(0);
  const [showSaveBar,   setShowSaveBar]   = useState(false);
  const [avatarPreview, setAvatarPreview] = useState(null);

  // Lookup data — populated from API, never hardcoded in render
  const [countries,              setCountries]              = useState([]); // string[]
  const [tags,                   setTags]                   = useState([]); // [{value, label}]
  const [levels,                 setLevels]                 = useState([]); // [{value, label}]
  const [scholarshipTypeOptions, setScholarshipTypeOptions] = useState([]); // string[]

  const [form, setForm] = useState({
    full_name: '', bio: '', date_of_birth: '', country: '', city: '',
    institution: '', field_of_study: '', graduation_year: '',
    gpa: '', gpa_scale: '4.0',
    leadership_experience: '', academic_achievements: '',
    financial_need_statement: '', career_goals: '', community_impact: '',
    challenges_overcome: '', research_experience: '',
    extracurriculars: '', relevant_coursework: '',
  });

  const [preferredCountries, setPreferredCountries] = useState([]);
  const [scholarshipTypes,   setScholarshipTypes]   = useState([]);
  const [selectedTags,       setSelectedTags]       = useState([]);
  const [selectedLevels,     setSelectedLevels]     = useState([]);
  const [technicalSkills,    setTechnicalSkills]    = useState([]);
  const [languagesSpoken,    setLanguagesSpoken]    = useState([]);

  // Show sticky save bar only when near the bottom of the page
  useEffect(() => {
    const onScroll = () => {
      setShowSaveBar(window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 120);
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  // Fetch all lookup data once on mount
  useEffect(() => {
    // Countries — RestCountries public API (no key required)
    fetch('https://restcountries.com/v3.1/all?fields=name')
      .then(r => r.json())
      .then(data =>
        setCountries(data.map(c => c.name?.common).filter(Boolean).sort((a, b) => a.localeCompare(b)))
      )
      .catch(() =>
        setCountries(['United States', 'United Kingdom', 'Canada', 'Australia', 'Nigeria', 'India', 'Germany', 'France'])
      );

    
    // Shape: { tags: [{value,label}], levels: [{value,label}], scholarship_types: string[] }
    api.get('scholarships/metadata/')
      .then(({ data }) => {
        setTags(data.tags || []);
        setLevels(data.levels || []);
        setScholarshipTypeOptions(data.scholarship_types || []);
      })
      .catch(() => {
        setTags([
          { value: 'international', label: 'International' },
          { value: 'merit',         label: 'Merit'         },
          { value: 'need',          label: 'Need'          },
          { value: 'general',       label: 'General'       },
        ]);
        setLevels([
          { value: 'highschool',    label: 'High School'   },
          { value: 'undergraduate', label: 'Undergraduate' },
          { value: 'postgraduate',  label: 'Postgraduate'  },
          { value: 'phd',           label: 'PhD'           },
          { value: 'other',         label: 'Other'         },
        ]);
        setScholarshipTypeOptions([
          'Merit-based', 'Need-based', 'Research', 'Athletic',
          'Community Service', 'Field-specific', 'Minority',
          'Women in STEM', 'International Student', 'Regional',
        ]);
      });
  }, []);

  useEffect(() => { fetchProfile(); }, []);

  const fetchProfile = async () => {
    try {
      const { data } = await api.get('users/update_profile/');
      const p = Array.isArray(data) ? data[0] : data;

      setForm({
        full_name:                p.full_name                || '',
        bio:                      p.bio                      || '',
        date_of_birth:            p.date_of_birth            || '',
        country:                  p.country                  || '',
        city:                     p.city                     || '',
        institution:              p.institution              || '',
        field_of_study:           p.field_of_study           || '',
        graduation_year:          p.graduation_year          || '',
        gpa:                      p.gpa                      || '',
        gpa_scale:                p.gpa_scale                || '4.0',
        leadership_experience:    p.leadership_experience    || '',
        academic_achievements:    p.academic_achievements    || '',
        financial_need_statement: p.financial_need_statement || '',
        career_goals:             p.career_goals             || '',
        community_impact:         p.community_impact         || '',
        challenges_overcome:      p.challenges_overcome      || '',
        research_experience:      p.research_experience      || '',
        extracurriculars:         p.extracurriculars         || '',
        relevant_coursework:      p.relevant_coursework      || '',
      });

      setCompletion(p.completion_percentage);
      if (p.profile_picture) setAvatarPreview(p.profile_picture);

      // preferred_countries / preferred_scholarship_types can come back as a
      // comma TextField string OR already as an array — handle both safely
      const toArray = (val) =>
        Array.isArray(val) ? val : String(val || '').split(',').map(s => s.trim()).filter(Boolean);

      setPreferredCountries(toArray(p.preferred_countries));
      setScholarshipTypes(toArray(p.preferred_scholarship_types));

      if (Array.isArray(p.tags))             setSelectedTags(p.tags);
      if (Array.isArray(p.level))            setSelectedLevels(p.level);
      if (Array.isArray(p.technical_skills)) setTechnicalSkills(p.technical_skills);
      if (Array.isArray(p.languages_spoken)) setLanguagesSpoken(p.languages_spoken);
    } catch {
      flash('Failed to load profile data.', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (e) => {
    e?.preventDefault();
    setSaving(true);
    try {
      await api.post('users/update_profile/', {
        ...form,
        preferred_countries:         preferredCountries.join(', '),
        preferred_scholarship_types: scholarshipTypes.join(', '),
        tags:             selectedTags,
        level:            selectedLevels,
        technical_skills: technicalSkills,
        languages_spoken: languagesSpoken,
      });
      flash('Profile saved!', 'success');
    } catch {
      flash('Failed to save changes.', 'error');
    } finally {
      setSaving(false);
    }
  };

  const sf    = (key) => (e) => setForm(p => ({ ...p, [key]: e.target.value }));
  const tog   = (list, setList, item) =>
    list.includes(item) ? setList(list.filter(i => i !== item)) : setList([...list, item]);
  const flash = (msg, type = 'success') => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3500);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-950 flex items-center justify-center">
        <div className="flex flex-col items-center gap-2 text-slate-500">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
          <p className="text-sm">Loading profile…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-slate-950 font-display">
      <Navbar onFilter={(f) => navigate('/', { state: { filters: f } })} />

      <main className="w-full max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 pb-28">

        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 dark:text-white">Edit Profile</h1>
            <p className="text-sm text-slate-400 mt-0.5">Your answers power AI essay drafting</p>
          </div>
          <div className="flex items-center gap-3 shrink-0">
            <button type="button" onClick={() => navigate('/dashboard')}
              className="px-4 py-2 text-sm font-medium text-slate-600 dark:text-slate-300 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800 transition">
              Cancel
            </button>
            <button type="button" onClick={handleSave} disabled={saving}
              className="px-4 py-2 text-sm font-semibold text-white bg-primary hover:bg-primary/90 rounded-lg transition flex items-center gap-2 disabled:opacity-50 shadow-sm">
              {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
              {saving ? 'Saving…' : 'Save Changes'}
            </button>
          </div>
        </div>

        <ProfileCompletion percentage={completion} />

        <div className="space-y-5 mt-6">

          {/* ═══ 1. Identity ══════════════════════════════════════════════════ */}
          <SectionCard icon={User} title="Identity" subtitle="Your public profile and personal summary">
            <div className="flex flex-col sm:flex-row gap-6 items-start">
              <div className="relative group shrink-0 mx-auto sm:mx-0">
                <div className="w-24 h-24 rounded-full bg-slate-100 dark:bg-slate-800 flex items-center justify-center overflow-hidden border-2 border-slate-200 dark:border-slate-700">
                  {avatarPreview
                    ? <img src={avatarPreview} alt="Avatar" className="w-full h-full object-cover" />
                    : <span className="text-3xl font-bold text-slate-400">{form.full_name?.[0]?.toUpperCase() || 'U'}</span>
                  }
                </div>
                <label className="absolute inset-0 bg-black/40 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer">
                  <Camera className="w-6 h-6 text-white" />
                  <input type="file" className="hidden" accept="image/*"
                    onChange={e => { const f = e.target.files?.[0]; if (f) setAvatarPreview(URL.createObjectURL(f)); }} />
                </label>
              </div>
              <div className="flex-1 space-y-4 w-full min-w-0">
                <div className="space-y-1.5">
                  <label className={lbl}>Full Name</label>
                  <input className={inp} value={form.full_name} onChange={sf('full_name')} placeholder="Ada Lovelace" />
                </div>
                <NarrativeField label="Bio"
                  hint="2–3 sentences. This is your public summary and the foundation for all AI essay drafts."
                  value={form.bio} onChange={sf('bio')} rows={3}
                  placeholder="Passionate CS student from Nigeria, researching computer vision to solve healthcare problems in Africa…" />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-5">
              <div className="space-y-1.5">
                <label className={lbl}>Date of Birth</label>
                <input className={inp} type="date" value={form.date_of_birth} onChange={sf('date_of_birth')} />
              </div>
              <div className="space-y-1.5">
                <label className={lbl}>Country of Residence</label>
                <select className={inp} value={form.country} onChange={sf('country')}>
                  <option value="">{countries.length === 0 ? 'Loading…' : 'Select country…'}</option>
                  {countries.map(c => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
              <div className="space-y-1.5">
                <label className={lbl}>City</label>
                <input className={inp} value={form.city} onChange={sf('city')} placeholder="Lagos" />
              </div>
            </div>
          </SectionCard>

          {/* ═══ 2. Education ═════════════════════════════════════════════════ */}
          <SectionCard icon={GraduationCap} title="Education" iconColor="text-violet-500" iconBg="bg-violet-500/10">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className={lbl}>Institution</label>
                <input className={inp} value={form.institution} onChange={sf('institution')} placeholder="University of Lagos" />
              </div>
              <div className="space-y-1.5">
                <label className={lbl}>Field of Study</label>
                <input className={inp} value={form.field_of_study} onChange={sf('field_of_study')} placeholder="Computer Science" />
              </div>
              <div className="space-y-1.5">
                <label className={lbl}>Graduation Year</label>
                <input className={inp} type="number" min="2000" max="2040" value={form.graduation_year} onChange={sf('graduation_year')} placeholder="2026" />
              </div>
              <div className="space-y-1.5">
                <label className={lbl}>GPA</label>
                <div className="flex items-center gap-2 max-w-[220px]">
                  <input className={`${inp} w-24 shrink-0`} type="number" step="0.01" min="0" max="10" value={form.gpa} onChange={sf('gpa')} placeholder="3.85" />
                  <span className="text-slate-400 shrink-0">/</span>
                  <select className={`${inp} w-24 shrink-0`} value={form.gpa_scale} onChange={sf('gpa_scale')}>
                    <option value="4.0">4.0</option>
                    <option value="5.0">5.0</option>
                    <option value="7.0">7.0</option>
                    <option value="10.0">10.0</option>
                    <option value="100">100%</option>
                  </select>
                </div>
              </div>
            </div>

            {/* levels[] comes from API → scholarship_metadata */}
            <div className="mt-5 space-y-2">
              <label className={lbl}>Academic Level</label>
              <div className="flex flex-wrap gap-2">
                {levels.map(l => {
                  const on = selectedLevels.includes(l.value);
                  return (
                    <button key={l.value} type="button"
                      onClick={() => tog(selectedLevels, setSelectedLevels, l.value)}
                      className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium border transition ${
                        on
                          ? 'bg-violet-500/10 border-violet-400/40 text-violet-600 dark:text-violet-300'
                          : 'bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-700 text-slate-500 hover:border-slate-300 dark:hover:border-slate-600'
                      }`}
                    >
                      {l.label} {on && <Check className="w-3 h-3" />}
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="mt-5">
              <NarrativeField label="Relevant Coursework" hint="Courses relevant to scholarships you're targeting."
                value={form.relevant_coursework} onChange={sf('relevant_coursework')} rows={3}
                placeholder="Machine Learning (A+), Algorithms (A), Database Systems (A)…" />
            </div>
          </SectionCard>

          {/* ═══ 3. Your Story ════════════════════════════════════════════════ */}
          <SectionCard icon={BookOpen} title="Your Story" iconColor="text-emerald-500" iconBg="bg-emerald-500/10"
            subtitle="Fed directly to the AI when generating essay drafts. Specific, vivid answers produce dramatically better results.">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
              <div className="sm:col-span-2">
                <NarrativeField label="Career Goals" hint="What do you want to do in 5–10 years and why?"
                  value={form.career_goals} onChange={sf('career_goals')}
                  placeholder="In the next decade I plan to build AI-powered diagnostic tools that serve rural hospitals in West Africa…" />
              </div>
              <NarrativeField label="Leadership Experience" hint="Describe a time you led a team or initiative."
                value={form.leadership_experience} onChange={sf('leadership_experience')}
                placeholder="As president of the AI club I organized a 3-day hackathon with 200 students…" />
              <NarrativeField label="Academic Achievements" hint="Awards, honours, distinctions, publications, research prizes."
                value={form.academic_achievements} onChange={sf('academic_achievements')}
                placeholder="First class honours, Dean's list 3 consecutive semesters…" />
              <NarrativeField label="Research Experience" hint="Projects, papers, labs, supervisors, methodologies."
                value={form.research_experience} onChange={sf('research_experience')}
                placeholder="Under Prof. Adeyemi I investigated convolutional approaches to malaria detection…" />
              <NarrativeField label="Community Impact" hint="Volunteering, social initiatives, community work."
                value={form.community_impact} onChange={sf('community_impact')}
                placeholder="I founded CodeBridge which taught programming to 120 underserved youth…" />
              <NarrativeField label="Extracurriculars" hint="Clubs, sports, hobbies, side projects."
                value={form.extracurriculars} onChange={sf('extracurriculars')}
                placeholder="Chess team captain, open-source contributor to TensorFlow…" />
              <NarrativeField label="Challenges Overcome" hint="A significant obstacle you faced and how you dealt with it."
                value={form.challenges_overcome} onChange={sf('challenges_overcome')}
                placeholder="Growing up without reliable electricity, I taught myself programming through downloaded tutorials…" />
              <NarrativeField label="Financial Need Statement" hint="Optional — only include if targeting need-based scholarships."
                value={form.financial_need_statement} onChange={sf('financial_need_statement')}
                placeholder="My family's monthly income of ₦80,000 supports five dependents…" />
            </div>
          </SectionCard>

          {/* ═══ 4. Skills & Languages ════════════════════════════════════════ */}
          <SectionCard icon={Zap} title="Skills & Languages" iconColor="text-amber-500" iconBg="bg-amber-500/10">
            <div className="space-y-5">
              <div className="space-y-1.5">
                <label className={lbl}>Technical Skills</label>
                <p className="text-xs text-slate-400">Type a skill and press Enter to add it.</p>
                <SkillInput skills={technicalSkills} onChange={setTechnicalSkills} />
              </div>
              <div className="space-y-1.5">
                <label className={lbl}>Languages Spoken</label>
                <LanguageRows languages={languagesSpoken} onChange={setLanguagesSpoken} />
              </div>
            </div>
          </SectionCard>

          {/* ═══ 5. Scholarship Preferences ══════════════════════════════════ */}
          <SectionCard icon={Star} title="Scholarship Preferences" iconColor="text-rose-500" iconBg="bg-rose-500/10">
            <div className="space-y-6">

              {/* tags[] from API → scholarship_metadata */}
              <div className="space-y-2">
                <label className={lbl}>Interest Tags</label>
                <div className="flex flex-wrap gap-2 p-4 border border-slate-200 dark:border-slate-700 rounded-xl bg-slate-50 dark:bg-slate-950">
                  {tags.map(tag => {
                    const on = selectedTags.includes(tag.value);
                    return (
                      <button key={tag.value} type="button"
                        onClick={() => tog(selectedTags, setSelectedTags, tag.value)}
                        className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium border transition ${
                          on
                            ? 'bg-primary text-white border-primary shadow-sm'
                            : 'bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400 hover:border-primary/40'
                        }`}
                      >
                        {tag.label} {on && <Check className="w-3 h-3" />}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* countries[] from RestCountries API */}
              <div className="space-y-2">
                <label className={lbl}>Preferred Scholarship Countries</label>
                <p className="text-xs text-slate-400">Where you'd like to study or receive funding.</p>
                <div className="flex flex-wrap gap-2">
                  {preferredCountries.map(c => (
                    <span key={c} className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-700/50 text-sm">
                      {c}
                      <button type="button" onClick={() => tog(preferredCountries, setPreferredCountries, c)}>
                        <X className="w-3 h-3 hover:text-blue-900 dark:hover:text-blue-100" />
                      </button>
                    </span>
                  ))}
                  <AddDropdown label="Add country"
                    options={countries.filter(c => !preferredCountries.includes(c))}
                    onAdd={c => setPreferredCountries(p => [...p, c])} />
                </div>
              </div>

              {/* scholarshipTypeOptions[] from API → scholarship_metadata */}
              <div className="space-y-2">
                <label className={lbl}>Scholarship Types</label>
                <p className="text-xs text-slate-400">Types you're actively targeting.</p>
                <div className="flex flex-wrap gap-2">
                  {scholarshipTypes.map(t => (
                    <span key={t} className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-purple-50 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 border border-purple-200 dark:border-purple-700/50 text-sm">
                      {t}
                      <button type="button" onClick={() => tog(scholarshipTypes, setScholarshipTypes, t)}>
                        <X className="w-3 h-3 hover:text-purple-900 dark:hover:text-purple-100" />
                      </button>
                    </span>
                  ))}
                  <AddDropdown label="Add type"
                    options={scholarshipTypeOptions.filter(t => !scholarshipTypes.includes(t))}
                    onAdd={t => setScholarshipTypes(p => [...p, t])} />
                </div>
              </div>

            </div>
          </SectionCard>

        </div>
      </main>

      {/* Sticky save bar — slides up when near bottom */}
      <div className={`fixed bottom-0 left-0 right-0 z-40 bg-white/90 dark:bg-slate-950/90 backdrop-blur border-t border-slate-200 dark:border-slate-800 px-6 py-3 flex items-center justify-between gap-4 transition-all duration-300 ${
        showSaveBar ? 'translate-y-0 opacity-100' : 'translate-y-full opacity-0 pointer-events-none'
      }`}>
        <p className="text-xs text-slate-400 hidden sm:block">
          {completion}% complete — more detail = better AI drafts
        </p>
        <div className="flex gap-3 ml-auto">
          <button type="button" onClick={() => navigate('/dashboard')}
            className="px-4 py-2 text-sm font-medium text-slate-600 dark:text-slate-300 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800 transition">
            Cancel
          </button>
          <button type="button" onClick={handleSave} disabled={saving}
            className="px-5 py-2 text-sm font-semibold text-white bg-primary hover:bg-primary/90 rounded-lg transition flex items-center gap-2 disabled:opacity-50 shadow-sm">
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            {saving ? 'Saving…' : 'Save Changes'}
          </button>
        </div>
      </div>

      {toast && (
        <div className={`fixed bottom-20 right-6 z-50 flex items-center gap-2.5 px-4 py-3 rounded-xl shadow-xl text-sm font-medium ${
          toast.type === 'success' ? 'bg-emerald-600 text-white' : 'bg-red-600 text-white'
        }`}>
          {toast.type === 'success' ? <Check className="w-4 h-4" /> : <X className="w-4 h-4" />}
          {toast.msg}
        </div>
      )}
    </div>
  );
}
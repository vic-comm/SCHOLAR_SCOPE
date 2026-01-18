import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';
import Navbar from '../components/Navbar';
import { 
  Camera, X, Plus, Check, Loader2, Save, LogOut 
} from 'lucide-react';

// --- Constants ---
const COUNTRIES = [
  'United States', 'Canada', 'United Kingdom', 'Australia', 'Germany', 'France',
  'Netherlands', 'Sweden', 'Norway', 'Denmark', 'Finland', 'Switzerland',
  'Japan', 'South Korea', 'Singapore', 'New Zealand', 'Ireland', 'Belgium',
  'Austria', 'Spain', 'Italy', 'Portugal', 'Poland', 'Czech Republic',
  'Hungary', 'Greece', 'Turkey', 'Israel', 'United Arab Emirates', 'Saudi Arabia',
  'South Africa', 'Nigeria', 'Kenya', 'Ghana', 'Egypt', 'Morocco',
  'Brazil', 'Argentina', 'Chile', 'Mexico', 'Colombia', 'Peru',
  'India', 'China', 'Malaysia', 'Thailand', 'Indonesia', 'Philippines'
];

const TAGS = [
  { value: 'international', label: 'International' },
  { value: 'merit', label: 'Merit' },
  { value: 'need', label: 'Need' },
  { value: 'general', label: 'General' }
];

const LEVELS = [
  { value: 'highschool', label: 'High School' },
  { value: 'undergraduate', label: 'Undergraduate' },
  { value: 'postgraduate', label: 'Postgraduate' },
  { value: 'phd', label: 'PhD' },
  { value: 'other', label: 'Other' }
];

const SCHOLARSHIP_TYPES = [
  'Merit-based', 'Need-based', 'Research', 'Athletic', 'Community Service',
  'Field-specific', 'Minority', 'Women in STEM', 'International Student', 'Regional'
];

export default function Profile() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  
  // UI States
  const [showToast, setShowToast] = useState(false);
  const [toastMessage, setToastMessage] = useState('');
  const [toastType, setToastType] = useState('success');
  const [dropdowns, setDropdowns] = useState({
    country: false,
    type: false,
    tag: false
  });

  // Form Data
  const [formData, setFormData] = useState({
    full_name: '',
    bio: '',
    date_of_birth: '',
    country: '',
    city: '',
    institution: '',
    field_of_study: '',
    graduation_year: '',
    profile_pic: null 
  });

  // Array/List Data
  const [preferredCountries, setPreferredCountries] = useState([]);
  const [scholarshipTypes, setScholarshipTypes] = useState([]);
  const [selectedTags, setSelectedTags] = useState([]);
  const [selectedLevels, setSelectedLevels] = useState([]);

  // --- API Effects ---
  useEffect(() => {
    fetchProfile();
  }, []);

  const fetchProfile = async () => {
    try {
      const res = await api.get('scholarships/update_profile/'); 
      const data = res.data;

      setFormData({
        full_name: data.full_name || '',
        bio: data.bio || '',
        date_of_birth: data.date_of_birth || '',
        country: data.country || '',
        city: data.city || '',
        institution: data.institution || '',
        field_of_study: data.field_of_study || '',
        graduation_year: data.graduation_year || '',
        profile_pic: data.profile_pic || null
      });

      // Handle comma-separated strings if backend stores them that way
      if (data.preferred_countries) {
        setPreferredCountries(data.preferred_countries.split(',').map(c => c.trim()).filter(Boolean));
      }
      if (data.preferred_scholarship_types) {
        setScholarshipTypes(data.preferred_scholarship_types.split(',').map(t => t.trim()).filter(Boolean));
      }

      if (Array.isArray(data.tags)) setSelectedTags(data.tags);
      if (Array.isArray(data.level)) setSelectedLevels(data.level);

    } catch (error) {
      console.error('Error fetching profile:', error);
      showToastMessage('Failed to load profile data', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);

    try {
      const payload = {
        ...formData,
        preferred_countries: preferredCountries.join(', '),
        preferred_scholarship_types: scholarshipTypes.join(', '),
        tags: selectedTags,
        level: selectedLevels
      };

     
    await api.post('scholarships/update_profile/', payload);
      
      showToastMessage('Profile updated successfully!', 'success');
    } catch (error) {
      console.error('Error saving profile:', error);
      showToastMessage('Failed to save changes.', 'error');
    } finally {
      setSaving(false);
    }
  };


  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const toggleDropdown = (key) => {
    setDropdowns(prev => ({
      country: key === 'country' ? !prev.country : false,
      type: key === 'type' ? !prev.type : false,
      tag: key === 'tag' ? !prev.tag : false
    }));
  };

  const showToastMessage = (message, type = 'success') => {
    setToastMessage(message);
    setToastType(type);
    setShowToast(true);
    setTimeout(() => setShowToast(false), 3000);
  };

  const toggleItem = (list, setList, item) => {
    if (list.includes(item)) {
      setList(list.filter(i => i !== item));
    } else {
      setList([...list, item]);
    }
  };


  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-950 flex items-center justify-center">
        <div className="flex flex-col items-center gap-2 text-slate-500">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
          <p>Loading profile...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-slate-950 font-display">
      <Navbar onFilter={(f) => navigate('/', { state: { filters: f } })} />

      <main className="w-full max-w-5xl mx-auto p-4 sm:p-6 lg:p-8">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
          <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 dark:text-white">Edit Profile</h1>
          <div className="flex items-center gap-3">
            <button 
              onClick={() => navigate('/dashboard')}
              className="px-4 py-2 text-slate-700 bg-white border border-slate-300 hover:bg-slate-50 font-medium rounded-lg transition dark:bg-slate-900 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
            >
              Cancel
            </button>
            <button 
              onClick={handleSave}
              disabled={saving}
              className="px-4 py-2 bg-primary text-white font-medium rounded-lg hover:bg-primary/90 transition flex items-center gap-2 disabled:opacity-50"
            >
              {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
              {saving ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </div>

        <div className="space-y-6">
          
          {/* Profile Picture & Basic Info */}
          <div className="bg-white dark:bg-slate-900 rounded-xl shadow-sm border border-slate-200 dark:border-slate-800 p-6">
            <div className="flex flex-col sm:flex-row items-start gap-8">
              {/* Image Upload */}
              <div className="relative group shrink-0 mx-auto sm:mx-0">
                <div className="h-28 w-28 rounded-full bg-slate-100 dark:bg-slate-800 flex items-center justify-center overflow-hidden border-4 border-white dark:border-slate-900 shadow-sm">
                  {formData.profile_pic ? (
                     <img src={formData.profile_pic} alt="Profile" className="w-full h-full object-cover" />
                  ) : (
                     <span className="text-3xl font-bold text-slate-400">
                        {formData.full_name ? formData.full_name.charAt(0).toUpperCase() : "U"}
                     </span>
                  )}
                </div>
                <label className="absolute inset-0 bg-black/40 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer">
                  <Camera className="w-8 h-8 text-white" />
                  <input type="file" className="hidden" accept="image/*" />
                </label>
              </div>

              {/* Basic Fields */}
              <div className="w-full space-y-4">
                <div className="grid gap-2">
                  <label className="text-sm font-semibold text-slate-700 dark:text-slate-300">Full Name</label>
                  <input 
                    name="full_name"
                    value={formData.full_name}
                    onChange={handleInputChange}
                    className="form-input w-full rounded-lg border-slate-300 dark:border-slate-700 dark:bg-slate-950 dark:text-white"
                  />
                </div>
                <div className="grid gap-2">
                  <label className="text-sm font-semibold text-slate-700 dark:text-slate-300">Bio</label>
                  <textarea 
                    name="bio"
                    value={formData.bio}
                    onChange={handleInputChange}
                    rows="3"
                    className="form-textarea w-full rounded-lg border-slate-300 dark:border-slate-700 dark:bg-slate-950 dark:text-white resize-none"
                    placeholder="Tell us a little about yourself..."
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Personal Information */}
          <div className="bg-white dark:bg-slate-900 rounded-xl shadow-sm border border-slate-200 dark:border-slate-800 p-6">
            <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-4">Personal Details</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="grid gap-2">
                <label className="text-sm font-semibold text-slate-700 dark:text-slate-300">Date of Birth</label>
                <input 
                  name="date_of_birth"
                  type="date"
                  value={formData.date_of_birth}
                  onChange={handleInputChange}
                  className="form-input w-full rounded-lg border-slate-300 dark:border-slate-700 dark:bg-slate-950 dark:text-white"
                />
              </div>
              <div className="grid gap-2">
                <label className="text-sm font-semibold text-slate-700 dark:text-slate-300">Country of Residence</label>
                <select 
                  name="country"
                  value={formData.country}
                  onChange={handleInputChange}
                  className="form-select w-full rounded-lg border-slate-300 dark:border-slate-700 dark:bg-slate-950 dark:text-white"
                >
                  <option value="">Select Country</option>
                  {COUNTRIES.map(c => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
              <div className="grid gap-2">
                <label className="text-sm font-semibold text-slate-700 dark:text-slate-300">City</label>
                <input 
                  name="city"
                  value={formData.city}
                  onChange={handleInputChange}
                  className="form-input w-full rounded-lg border-slate-300 dark:border-slate-700 dark:bg-slate-950 dark:text-white"
                />
              </div>
            </div>
          </div>

          {/* Education */}
          <div className="bg-white dark:bg-slate-900 rounded-xl shadow-sm border border-slate-200 dark:border-slate-800 p-6">
            <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-4">Education</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="grid gap-2">
                <label className="text-sm font-semibold text-slate-700 dark:text-slate-300">Institution</label>
                <input 
                  name="institution"
                  value={formData.institution}
                  onChange={handleInputChange}
                  className="form-input w-full rounded-lg border-slate-300 dark:border-slate-700 dark:bg-slate-950 dark:text-white"
                />
              </div>
              <div className="grid gap-2">
                <label className="text-sm font-semibold text-slate-700 dark:text-slate-300">Field of Study</label>
                <input 
                  name="field_of_study"
                  value={formData.field_of_study}
                  onChange={handleInputChange}
                  className="form-input w-full rounded-lg border-slate-300 dark:border-slate-700 dark:bg-slate-950 dark:text-white"
                />
              </div>
              
              <div className="grid gap-2">
                <label className="text-sm font-semibold text-slate-700 dark:text-slate-300">Current Academic Level</label>
                <div className="border border-slate-300 dark:border-slate-700 rounded-lg p-3 bg-slate-50 dark:bg-slate-950 max-h-40 overflow-y-auto">
                  {LEVELS.map(level => (
                    <label key={level.value} className="flex items-center gap-3 p-1 cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-800 rounded">
                      <input
                        type="checkbox"
                        checked={selectedLevels.includes(level.value)}
                        onChange={() => toggleItem(selectedLevels, setSelectedLevels, level.value)}
                        className="rounded border-slate-300 text-primary focus:ring-primary"
                      />
                      <span className="text-sm text-slate-700 dark:text-slate-300">{level.label}</span>
                    </label>
                  ))}
                </div>
              </div>

              <div className="grid gap-2">
                <label className="text-sm font-semibold text-slate-700 dark:text-slate-300">Graduation Year (Expected)</label>
                <input 
                  name="graduation_year"
                  type="number"
                  value={formData.graduation_year}
                  onChange={handleInputChange}
                  className="form-input w-full rounded-lg border-slate-300 dark:border-slate-700 dark:bg-slate-950 dark:text-white"
                />
              </div>
            </div>
          </div>

          {/* Preferences */}
          <div className="bg-white dark:bg-slate-900 rounded-xl shadow-sm border border-slate-200 dark:border-slate-800 p-6">
            <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-6">Scholarship Preferences</h3>
            
            <div className="space-y-6">
              {/* Preferred Countries */}
              <div>
                <label className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2 block">Preferred Countries</label>
                <div className="flex flex-wrap gap-2">
                  {preferredCountries.map(country => (
                    <span key={country} className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-blue-50 text-blue-700 border border-blue-200 text-sm">
                      {country}
                      <button onClick={() => toggleItem(preferredCountries, setPreferredCountries, country)}>
                        <X className="w-3 h-3 hover:text-blue-900" />
                      </button>
                    </span>
                  ))}
                  <div className="relative">
                    <button 
                      onClick={() => toggleDropdown('country')}
                      className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-slate-100 hover:bg-slate-200 text-slate-700 text-sm border border-slate-200 transition"
                    >
                      <Plus className="w-3 h-3" /> Add
                    </button>
                    {dropdowns.country && (
                      <div className="absolute z-10 mt-2 w-64 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg shadow-xl max-h-60 overflow-y-auto">
                        {COUNTRIES.filter(c => !preferredCountries.includes(c)).map(c => (
                          <button
                            key={c}
                            onClick={() => { toggleItem(preferredCountries, setPreferredCountries, c); toggleDropdown('country'); }}
                            className="w-full text-left px-4 py-2 text-sm hover:bg-slate-50 dark:hover:bg-slate-800 dark:text-slate-200"
                          >
                            {c}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Types */}
              <div>
                <label className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2 block">Scholarship Types</label>
                <div className="flex flex-wrap gap-2">
                  {scholarshipTypes.map(type => (
                    <span key={type} className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-purple-50 text-purple-700 border border-purple-200 text-sm">
                      {type}
                      <button onClick={() => toggleItem(scholarshipTypes, setScholarshipTypes, type)}>
                        <X className="w-3 h-3 hover:text-purple-900" />
                      </button>
                    </span>
                  ))}
                  <div className="relative">
                    <button 
                      onClick={() => toggleDropdown('type')}
                      className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-slate-100 hover:bg-slate-200 text-slate-700 text-sm border border-slate-200 transition"
                    >
                      <Plus className="w-3 h-3" /> Add
                    </button>
                    {dropdowns.type && (
                      <div className="absolute z-10 mt-2 w-64 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg shadow-xl max-h-60 overflow-y-auto">
                        {SCHOLARSHIP_TYPES.filter(t => !scholarshipTypes.includes(t)).map(t => (
                          <button
                            key={t}
                            onClick={() => { toggleItem(scholarshipTypes, setScholarshipTypes, t); toggleDropdown('type'); }}
                            className="w-full text-left px-4 py-2 text-sm hover:bg-slate-50 dark:hover:bg-slate-800 dark:text-slate-200"
                          >
                            {t}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Tags */}
              <div>
                <label className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2 block">Interest Tags</label>
                <div className="flex flex-wrap gap-2 p-4 border border-slate-200 dark:border-slate-700 rounded-xl bg-slate-50 dark:bg-slate-950">
                  {TAGS.map(tag => {
                    const isSelected = selectedTags.includes(tag.value);
                    return (
                      <button
                        key={tag.value}
                        onClick={() => toggleItem(selectedTags, setSelectedTags, tag.value)}
                        className={`inline-flex items-center gap-1 px-3 py-1.5 rounded-full text-sm font-medium transition ${
                          isSelected 
                            ? 'bg-primary text-white shadow-md' 
                            : 'bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400 hover:border-primary/50'
                        }`}
                      >
                        {tag.label}
                        {isSelected && <Check className="w-3 h-3" />}
                      </button>
                    );
                  })}
                </div>
              </div>

            </div>
          </div>
        </div>
      </main>

      {/* Backdrop for dropdowns */}
      {(dropdowns.country || dropdowns.type) && (
        <div 
          className="fixed inset-0 z-0" 
          onClick={() => setDropdowns({ country: false, type: false, tag: false })}
        />
      )}

      {/* Toast */}
      {showToast && (
        <div className={`fixed bottom-6 right-6 flex items-center gap-3 px-4 py-3 rounded-lg shadow-lg text-white animate-in slide-in-from-bottom-5 ${
          toastType === 'success' ? 'bg-green-600' : 'bg-red-600'
        }`}>
          {toastType === 'success' ? <Check className="w-5 h-5" /> : <X className="w-5 h-5" />}
          <p className="font-medium text-sm">{toastMessage}</p>
        </div>
      )}
    </div>
  );
};
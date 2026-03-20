import React, { useState } from 'react';
import { Download, Settings, FileArchive, CheckCircle2, X } from 'lucide-react';

const ExtensionPrompt = () => {
  const [isVisible, setIsVisible] = useState(true);

  if (!isVisible) return null;

  return (
    <div className="fixed bottom-4 right-4 md:bottom-8 md:right-8 z-50 max-w-sm w-full">
      <div className="bg-white dark:bg-slate-900 border border-primary/20 shadow-2xl rounded-2xl p-5 relative overflow-hidden">
        
        {/* Close Button */}
        <button 
          onClick={() => setIsVisible(false)}
          className="absolute top-3 right-3 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-3 mb-4">
          <div className="bg-primary/10 p-2 rounded-lg">
            <Download className="w-6 h-6 text-primary" />
          </div>
          <h3 className="font-bold text-slate-900 dark:text-white">
            Install the Extension
          </h3>
        </div>

        <p className="text-sm text-slate-600 dark:text-slate-400 mb-4">
          To extract scholarships and generate essays directly from websites, install our Chrome Extension in Developer Mode.
        </p>

        {/* The Download Button */}
        <a 
          href="/scholarscope-extension.zip" 
          download
          className="w-full flex items-center justify-center gap-2 bg-primary text-white py-2.5 px-4 rounded-xl font-medium hover:bg-primary/90 transition-colors mb-5"
        >
          <FileArchive className="w-4 h-4" />
          Download Extension (.zip)
        </a>

        {/* Instructions */}
        <div className="space-y-3">
          <h4 className="text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider">How to install:</h4>
          
          <div className="flex gap-3 items-start">
            <span className="flex items-center justify-center w-5 h-5 rounded-full bg-slate-100 dark:bg-slate-800 text-xs font-medium text-slate-600 dark:text-slate-400 shrink-0">1</span>
            <p className="text-xs text-slate-600 dark:text-slate-400">
              Extract the downloaded .zip file.
            </p>
          </div>

          <div className="flex gap-3 items-start">
            <span className="flex items-center justify-center w-5 h-5 rounded-full bg-slate-100 dark:bg-slate-800 text-xs font-medium text-slate-600 dark:text-slate-400 shrink-0">2</span>
            <p className="text-xs text-slate-600 dark:text-slate-400">
              Go to <span className="font-mono bg-slate-100 dark:bg-slate-800 px-1 py-0.5 rounded text-[10px] text-slate-800 dark:text-slate-300 select-all">chrome://extensions/</span> and turn on <strong>Developer mode</strong> (top right).
            </p>
          </div>

          <div className="flex gap-3 items-start">
            <span className="flex items-center justify-center w-5 h-5 rounded-full bg-slate-100 dark:bg-slate-800 text-xs font-medium text-slate-600 dark:text-slate-400 shrink-0">3</span>
            <p className="text-xs text-slate-600 dark:text-slate-400">
              Click <strong>"Load unpacked"</strong> and select the extracted folder.
            </p>
          </div>
        </div>

      </div>
    </div>
  );
};

export default ExtensionPrompt;
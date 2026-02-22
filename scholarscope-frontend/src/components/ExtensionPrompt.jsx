import React, { useState, useEffect } from 'react';
import { X } from 'lucide-react'; // Assuming you use Lucide icons

const ExtensionPrompt = () => {
  const [isInstalled, setIsInstalled] = useState(true); // Assume true initially to prevent flash
  const [isVisible, setIsVisible] = useState(true);

  useEffect(() => {
    // 1. Give the extension 500ms to inject its flag
    const checkExtension = setTimeout(() => {
      const hasFlag = document.documentElement.getAttribute('data-scholar-scope-installed');
      const hasWindowVar = window.HAS_SCHOLAR_SCOPE;

      if (!hasFlag && !hasWindowVar) {
        setIsInstalled(false);
      }
    }, 1000);

    return () => clearTimeout(checkExtension);
  }, []);

  // Don't show if installed or user dismissed it
  if (isInstalled || !isVisible) return null;

  return (
    <div className="fixed bottom-0 left-0 right-0 bg-slate-900 text-white p-4 shadow-lg z-50 border-t border-slate-700 animate-slide-up">
      <div className="container mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
        
        <div className="flex items-center gap-4">
          <div className="bg-primary/20 p-2 rounded-lg">
            {/* Replace with your logo */}
            <span className="text-2xl">🎓</span>
          </div>
          <div>
            <h3 className="font-bold text-lg">Don't miss a scholarship!</h3>
            <p className="text-slate-300 text-sm">
              Install the Scholar Scope extension to auto-fill applications instantly.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button 
            onClick={() => setIsVisible(false)}
            className="text-slate-400 hover:text-white px-3 py-2 text-sm"
          >
            Not now
          </button>
          
          <a 
            href="YOUR_CHROME_WEB_STORE_LINK_HERE" 
            target="_blank" 
            rel="noopener noreferrer"
            className="bg-primary hover:bg-primary/90 text-white px-6 py-2.5 rounded-lg font-medium transition-colors shadow-lg shadow-primary/25"
          >
            Add to Chrome - It's Free
          </a>
        </div>
      </div>
    </div>
  );
};

export default ExtensionPrompt;
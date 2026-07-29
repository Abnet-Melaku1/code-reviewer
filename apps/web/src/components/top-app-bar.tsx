import React from "react";

interface TopAppBarProps {
  activeTab: "repositories" | "reviews" | "style" | "settings";
  setActiveTab: (tab: "repositories" | "reviews" | "style" | "settings") => void;
  showLogs: boolean;
  setShowLogs: (show: boolean) => void;
  setSelectedPrId: (id: number | null) => void;
}

export const TopAppBar: React.FC<TopAppBarProps> = ({
  activeTab,
  setActiveTab,
  showLogs,
  setShowLogs,
  setSelectedPrId,
}) => {
  const handleTabClick = (tab: "repositories" | "reviews" | "style" | "settings") => {
    setActiveTab(tab);
    setSelectedPrId(null);
  };

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-background border-b border-hairline flex justify-between items-center w-full px-margin-page h-16 max-w-full mx-auto">
      <div className="flex items-center gap-8">
        <span 
          className="font-headline-md text-headline-md font-semibold text-primary select-none cursor-pointer"
          onClick={() => handleTabClick("repositories")}
        >
          CodeReviewer.ai
        </span>
        <div className="hidden md:flex items-center gap-6">
          <button 
            className={`font-label-md text-label-md transition-colors pb-1 cursor-pointer ${activeTab === "repositories" ? "text-primary font-bold border-b-2 border-primary" : "text-ink-muted hover:text-primary"}`}
            onClick={() => handleTabClick("repositories")}
          >
            Repositories
          </button>
          <button 
            className={`font-label-md text-label-md transition-colors pb-1 cursor-pointer ${activeTab === "reviews" ? "text-primary font-bold border-b-2 border-primary" : "text-ink-muted hover:text-primary"}`}
            onClick={() => handleTabClick("reviews")}
          >
            Review Queue
          </button>
          <button 
            className={`font-label-md text-label-md transition-colors pb-1 cursor-pointer ${activeTab === "style" ? "text-primary font-bold border-b-2 border-primary" : "text-ink-muted hover:text-primary"}`}
            onClick={() => handleTabClick("style")}
          >
            House Style
          </button>
        </div>
      </div>

      <div className="flex items-center gap-4">
        <button 
          onClick={() => setShowLogs(!showLogs)} 
          className={`material-symbols-outlined text-ink-muted p-2 rounded-full hover:bg-surface-container transition-all cursor-pointer ${showLogs ? "text-primary bg-surface-container font-bold" : ""}`}
          title="Toggle Live WebSocket logs"
        >
          history
        </button>
        <button 
          onClick={() => handleTabClick("settings")} 
          className={`material-symbols-outlined text-ink-muted p-2 rounded-full hover:bg-surface-container transition-all cursor-pointer ${activeTab === "settings" ? "text-primary bg-surface-container font-bold" : ""}`}
          title="Webhook settings"
        >
          settings
        </button>
        <img 
          className="w-8 h-8 rounded-full border border-hairline object-cover select-none" 
          alt="Engineer Headshot"
          src="https://lh3.googleusercontent.com/aida-public/AB6AXuAeC6bssh9-2tU6zhdHrIESP2z2hCGts-hrG_uVLW8WvYsER87ZxSyOZcEaI2xAdaXsC5dRk8xvMsdbhN9GVTNiwBs8lNcnIeiWq0rHj1xovS9Iznn2SKXLvRf7350UGPdmO-5fnO7MQwjeUeMZhogCOmQcGboiNI5vyGMTGdUkwVAI9eHyK1faIVcPXfNLG98E5PFgbVSqMcWgXS5ncbqTwtx-dgivrgGZBGZoQBaxjFjnoYG8lnrzZIph-QDwT7oTZDnfffeFYgc"
        />
      </div>
    </nav>
  );
};

import React from "react";

export const Settings: React.FC = () => {
  return (
    <main className="flex-grow bg-background max-w-2xl mx-auto px-margin-page py-12 overflow-y-auto custom-scrollbar">
      <header className="mb-8">
        <h1 className="font-headline-lg text-headline-lg text-ink-primary mb-2">Webhook Settings</h1>
        <p className="font-body-md text-body-md text-ink-muted">To link GitHub pull requests to CodeReviewer, register the following details as a webhook.</p>
      </header>

      <div className="space-y-6">
        <div className="flex flex-col gap-2">
          <label className="font-label-sm text-xs text-ink-muted uppercase tracking-wider">Payload Endpoint URL</label>
          <div className="bg-surface-raised border border-hairline p-4 rounded-lg font-code-md text-sm text-primary select-all">
            https://api.codereviewer.ai/webhooks/github
          </div>
        </div>

        <div className="flex flex-col gap-2">
          <label className="font-label-sm text-xs text-ink-muted uppercase tracking-wider">Webhook Secret Key</label>
          <input
            type="password"
            className="bg-surface-raised border border-hairline rounded-lg px-4 py-2 font-label-sm focus:outline-none focus:border-primary"
            value="••••••••••••••••••••••••••••••••"
            disabled
          />
        </div>
      </div>
    </main>
  );
};

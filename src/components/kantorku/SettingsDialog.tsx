'use client';

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Settings, Key, Wifi, WifiOff } from 'lucide-react';
import { useKantorkuStore } from '@/lib/kantorku/store';
import { useState } from 'react';

export function SettingsDialog() {
  const { apiKey, setApiKey, isBackendConnected, settingsOpen, setSettingsOpen } =
    useKantorkuStore();
  const [tempKey, setTempKey] = useState(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('kantorku_api_key') || apiKey;
    }
    return apiKey;
  });

  const handleSave = () => {
    setApiKey(tempKey);
    localStorage.setItem('kantorku_api_key', tempKey);
    setSettingsOpen(false);
  };

  return (
    <Dialog open={settingsOpen} onOpenChange={setSettingsOpen}>
      <DialogContent className="bg-slate-900 border-slate-700/50 text-white max-w-md">
        <DialogHeader>
          <DialogTitle className="text-cyan-300 flex items-center gap-2">
            <Settings className="h-4 w-4" />
            kantorku Settings
          </DialogTitle>
        </DialogHeader>
        <div className="space-y-4 pt-2">
          {/* API Key */}
          <div className="space-y-2">
            <Label className="text-xs text-slate-400">
              <Key className="h-3 w-3 inline mr-1" />
              API Key (for standalone mode)
            </Label>
            <Input
              value={tempKey}
              onChange={(e) => setTempKey(e.target.value)}
              type="password"
              placeholder="sk-..."
              className="bg-slate-800/60 border-slate-700/50 text-xs text-slate-200"
            />
            <p className="text-[10px] text-slate-600">
              If no API key is set, the app will try to connect to the kantorku Python backend.
            </p>
          </div>

          {/* Connection Status */}
          <div className="flex items-center justify-between p-3 rounded-lg bg-slate-800/60 border border-slate-700/30">
            <div className="flex items-center gap-2">
              {isBackendConnected ? (
                <Wifi className="h-4 w-4 text-green-400" />
              ) : (
                <WifiOff className="h-4 w-4 text-red-400" />
              )}
              <div>
                <p className="text-xs text-slate-300">Backend Status</p>
                <p className="text-[10px] text-slate-500">
                  {isBackendConnected ? 'Connected' : 'Standalone Mode (z-ai-web-dev-sdk)'}
                </p>
              </div>
            </div>
            <Switch checked={isBackendConnected} disabled />
          </div>

          {/* Save */}
          <Button
            onClick={handleSave}
            className="w-full bg-gradient-to-r from-cyan-600 to-teal-600 hover:from-cyan-500 hover:to-teal-500 text-white"
          >
            Save Settings
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

export function SettingsButton() {
  const { setSettingsOpen } = useKantorkuStore();
  return (
    <button
      onClick={() => setSettingsOpen(true)}
      className="p-1.5 rounded-md hover:bg-slate-700/50 transition-colors"
      title="Settings"
    >
      <Settings className="h-4 w-4 text-slate-400" />
    </button>
  );
}

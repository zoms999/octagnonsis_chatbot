'use client';

import React, { useState } from 'react';
import { useAuth } from '@/providers/auth-provider';
import { useETLActions } from '@/hooks/use-etl-actions';
import { Button } from '@/components/ui/button';
import { ConfirmationDialog } from '@/components/ui/confirmation-dialog';
import { Spinner } from '@/components/ui/loading';

interface ReprocessingTriggerProps {
  className?: string;
  variant?: 'default' | 'outline';
  size?: 'default' | 'sm' | 'lg' | 'icon';
}

export function ReprocessingTrigger({ 
  className = '',
  variant = 'default',
  size = 'default'
}: ReprocessingTriggerProps) {
  const { user } = useAuth();
  const [showConfirmDialog, setShowConfirmDialog] = useState(false);
  const [showForceDialog, setShowForceDialog] = useState(false);
  
  const {
    triggerReprocessing,
    isReprocessing,
  } = useETLActions();

  const isUserReprocessing = user?.id ? isReprocessing(user.id) : false;

  const handleNormalReprocess = () => {
    if (user?.id) {
      triggerReprocessing(user.id, false);
      setShowConfirmDialog(false);
    }
  };

  const handleForceReprocess = () => {
    if (user?.id) {
      triggerReprocessing(user.id, true);
      setShowForceDialog(false);
    }
  };

  if (!user?.id) {
    return null;
  }

  return (
    <>
      <div className={`flex items-center space-x-2 ${className}`}>
        <Button
          onClick={() => setShowConfirmDialog(true)}
          disabled={isUserReprocessing}
          variant={variant}
          size={size}
          className={variant === 'default' ? 'bg-green-600 hover:bg-green-700 text-white' : ''}
        >
          {isUserReprocessing ? (
            <>
              <Spinner size="sm" className="mr-2" />
              Processing...
            </>
          ) : (
            <>
              🔄 Reprocess Documents
            </>
          )}
        </Button>

        <Button
          onClick={() => setShowForceDialog(true)}
          disabled={isUserReprocessing}
          variant="outline"
          size={size}
          className="text-orange-600 border-orange-300 hover:bg-orange-50"
        >
          Force Reprocess
        </Button>
      </div>

      {/* Normal Reprocess Confirmation */}
      <ConfirmationDialog
        isOpen={showConfirmDialog}
        onClose={() => setShowConfirmDialog(false)}
        onConfirm={handleNormalReprocess}
        title="Reprocess Documents"
        message="This will reprocess your documents and update the analysis. Only documents that need updating will be processed. This may take several minutes to complete."
        confirmText="Start Reprocessing"
        variant="default"
        isLoading={isUserReprocessing}
      />

      {/* Force Reprocess Confirmation */}
      <ConfirmationDialog
        isOpen={showForceDialog}
        onClose={() => setShowForceDialog(false)}
        onConfirm={handleForceReprocess}
        title="Force Reprocess All Documents"
        message="This will force reprocessing of ALL your documents, even if they haven't changed. This is a more intensive operation and may take longer to complete. Use this only if you're experiencing issues with your current analysis."
        confirmText="Force Reprocess All"
        cancelText="Cancel"
        variant="destructive"
        isLoading={isUserReprocessing}
      />
    </>
  );
}
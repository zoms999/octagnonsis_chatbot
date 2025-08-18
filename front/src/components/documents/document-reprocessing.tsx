'use client';

import React, { useState } from 'react';
import { useAuth } from '@/providers/auth-provider';
import { useReprocessUserDocuments } from '@/hooks/api-hooks';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { ConfirmationDialog } from '@/components/ui/confirmation-dialog';
import { useToast } from '@/components/ui/toast';
import { 
  RefreshCw, 
  AlertTriangle, 
  CheckCircle, 
  XCircle,
  Info
} from 'lucide-react';

interface DocumentReprocessingProps {
  className?: string;
}

export function DocumentReprocessing({ className }: DocumentReprocessingProps) {
  const { user } = useAuth();
  const { toast } = useToast();
  const [showConfirmDialog, setShowConfirmDialog] = useState(false);
  const [forceReprocess, setForceReprocess] = useState(false);

  const reprocessMutation = useReprocessUserDocuments({
    onSuccess: (data) => {
      toast({
        title: '재처리 시작됨',
        description: `문서 재처리가 시작되었습니다. 작업 ID: ${data.job_id}`,
        variant: 'success',
      });
      setShowConfirmDialog(false);
    },
    onError: (error: any) => {
      toast({
        title: '재처리 실패',
        description: error.message || '문서 재처리 중 오류가 발생했습니다.',
        variant: 'destructive',
      });
      setShowConfirmDialog(false);
    },
  });

  const handleReprocess = () => {
    if (!user?.id) {
      toast({
        title: '오류',
        description: '사용자 정보를 찾을 수 없습니다.',
        variant: 'destructive',
      });
      return;
    }

    reprocessMutation.mutate({
      userId: user.id,
      force: forceReprocess,
    });
  };

  const handleConfirmReprocess = (force: boolean = false) => {
    setForceReprocess(force);
    setShowConfirmDialog(true);
  };

  if (!user) {
    return (
      <Card className={`p-6 ${className}`}>
        <div className="text-center text-muted-foreground">
          <XCircle className="h-8 w-8 mx-auto mb-2" />
          <p>사용자 정보를 불러올 수 없습니다.</p>
        </div>
      </Card>
    );
  }

  return (
    <>
      <Card className={`p-6 ${className}`}>
        <div className="space-y-4">
          <div className="flex items-center space-x-2">
            <RefreshCw className="h-5 w-5 text-blue-500" />
            <h3 className="text-lg font-semibold">문서 재처리</h3>
          </div>

          <div className="space-y-3 text-sm text-muted-foreground">
            <div className="flex items-start space-x-2">
              <Info className="h-4 w-4 mt-0.5 text-blue-500 flex-shrink-0" />
              <p>
                문서 재처리를 통해 최신 알고리즘으로 적성 분석 결과를 다시 생성할 수 있습니다.
              </p>
            </div>
            <div className="flex items-start space-x-2">
              <AlertTriangle className="h-4 w-4 mt-0.5 text-yellow-500 flex-shrink-0" />
              <p>
                재처리 중에는 기존 문서가 일시적으로 사용할 수 없을 수 있습니다.
              </p>
            </div>
          </div>

          <div className="flex flex-col sm:flex-row gap-3">
            <Button
              onClick={() => handleConfirmReprocess(false)}
              disabled={reprocessMutation.isPending}
              className="flex items-center space-x-2"
            >
              {reprocessMutation.isPending ? (
                <RefreshCw className="h-4 w-4 animate-spin" />
              ) : (
                <RefreshCw className="h-4 w-4" />
              )}
              <span>일반 재처리</span>
            </Button>

            <Button
              variant="outline"
              onClick={() => handleConfirmReprocess(true)}
              disabled={reprocessMutation.isPending}
              className="flex items-center space-x-2"
            >
              {reprocessMutation.isPending ? (
                <RefreshCw className="h-4 w-4 animate-spin" />
              ) : (
                <AlertTriangle className="h-4 w-4" />
              )}
              <span>강제 재처리</span>
            </Button>
          </div>

          <div className="text-xs text-muted-foreground space-y-1">
            <p>
              <strong>일반 재처리:</strong> 기존 처리 상태를 확인하고 필요한 경우에만 재처리합니다.
            </p>
            <p>
              <strong>강제 재처리:</strong> 기존 상태와 관계없이 모든 문서를 다시 처리합니다.
            </p>
          </div>

          {reprocessMutation.isPending && (
            <div className="flex items-center space-x-2 p-3 bg-blue-50 rounded-md">
              <RefreshCw className="h-4 w-4 animate-spin text-blue-500" />
              <span className="text-sm text-blue-700">
                재처리 작업을 시작하고 있습니다...
              </span>
            </div>
          )}
        </div>
      </Card>

      <ConfirmationDialog
        isOpen={showConfirmDialog}
        onClose={() => setShowConfirmDialog(false)}
        onConfirm={handleReprocess}
        title={forceReprocess ? '강제 재처리 확인' : '재처리 확인'}
        description={
          forceReprocess
            ? '모든 문서를 강제로 재처리하시겠습니까? 이 작업은 시간이 오래 걸릴 수 있으며, 기존 문서가 모두 새로 생성됩니다.'
            : '문서 재처리를 시작하시겠습니까? 필요한 문서만 다시 처리됩니다.'
        }
        confirmText={forceReprocess ? '강제 재처리' : '재처리 시작'}
        cancelText="취소"
        variant={forceReprocess ? 'destructive' : 'default'}
        icon={
          forceReprocess ? (
            <AlertTriangle className="h-6 w-6 text-red-500" />
          ) : (
            <RefreshCw className="h-6 w-6 text-blue-500" />
          )
        }
      />
    </>
  );
}
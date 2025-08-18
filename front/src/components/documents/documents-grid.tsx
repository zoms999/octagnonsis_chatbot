'use client';

import React, { useState } from 'react';
import { useAuth } from '@/providers/auth-provider';
import { useUserDocuments } from '@/hooks/api-hooks';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import { 
  FileText, 
  Search, 
  Filter, 
  ChevronLeft, 
  ChevronRight,
  AlertCircle,
  User,
  Briefcase,
  Target
} from 'lucide-react';
import { UserDocument } from '@/lib/types';

interface DocumentsGridProps {
  className?: string;
}

export function DocumentsGrid({ className }: DocumentsGridProps) {
  const { user } = useAuth();
  const [currentPage, setCurrentPage] = useState(1);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedDocType, setSelectedDocType] = useState<string>('');
  const [itemsPerPage] = useState(12);

  const { 
    data: documentsData, 
    isLoading, 
    error 
  } = useUserDocuments(
    user?.id || '', 
    currentPage, 
    itemsPerPage, 
    selectedDocType || undefined
  );

  // Filter documents by search term
  const filteredDocuments = documentsData?.documents?.filter(doc =>
    doc.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
    doc.doc_type.toLowerCase().includes(searchTerm.toLowerCase())
  ) || [];

  const totalPages = documentsData ? Math.ceil(documentsData.total / itemsPerPage) : 0;

  const getDocumentTypeIcon = (docType: string) => {
    switch (docType) {
      case 'primary_tendency':
        return <User className="h-5 w-5 text-blue-500" />;
      case 'top_skills':
        return <Target className="h-5 w-5 text-green-500" />;
      case 'top_jobs':
        return <Briefcase className="h-5 w-5 text-purple-500" />;
      default:
        return <FileText className="h-5 w-5 text-gray-500" />;
    }
  };

  const getDocumentTypeLabel = (docType: string) => {
    switch (docType) {
      case 'primary_tendency':
        return '주요 성향';
      case 'top_skills':
        return '상위 기술';
      case 'top_jobs':
        return '추천 직업';
      default:
        return docType;
    }
  };

  const getDocumentTypeColor = (docType: string) => {
    switch (docType) {
      case 'primary_tendency':
        return 'bg-blue-100 text-blue-800';
      case 'top_skills':
        return 'bg-green-100 text-green-800';
      case 'top_jobs':
        return 'bg-purple-100 text-purple-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const renderDocumentPreview = (doc: UserDocument) => {
    const { preview } = doc;
    
    if (doc.doc_type === 'primary_tendency' && preview.primary_tendency) {
      return (
        <div className="text-sm text-muted-foreground">
          <p className="font-medium">주요 성향:</p>
          <p className="truncate">{preview.primary_tendency}</p>
        </div>
      );
    }
    
    if (doc.doc_type === 'top_skills' && preview.top_skills) {
      return (
        <div className="text-sm text-muted-foreground">
          <p className="font-medium">상위 기술:</p>
          <div className="flex flex-wrap gap-1 mt-1">
            {preview.top_skills.slice(0, 3).map((skill, index) => (
              <Badge key={index} variant="outline" className="text-xs">
                {skill}
              </Badge>
            ))}
            {preview.top_skills.length > 3 && (
              <Badge variant="outline" className="text-xs">
                +{preview.top_skills.length - 3}
              </Badge>
            )}
          </div>
        </div>
      );
    }
    
    if (doc.doc_type === 'top_jobs' && preview.top_jobs) {
      return (
        <div className="text-sm text-muted-foreground">
          <p className="font-medium">추천 직업:</p>
          <div className="flex flex-wrap gap-1 mt-1">
            {preview.top_jobs.slice(0, 2).map((job, index) => (
              <Badge key={index} variant="outline" className="text-xs">
                {job}
              </Badge>
            ))}
            {preview.top_jobs.length > 2 && (
              <Badge variant="outline" className="text-xs">
                +{preview.top_jobs.length - 2}
              </Badge>
            )}
          </div>
        </div>
      );
    }
    
    if (preview.summary) {
      return (
        <div className="text-sm text-muted-foreground">
          <p className="line-clamp-3">{preview.summary}</p>
        </div>
      );
    }
    
    return (
      <div className="text-sm text-muted-foreground">
        <p>미리보기를 사용할 수 없습니다.</p>
      </div>
    );
  };

  if (!user) {
    return (
      <Card className={`p-6 ${className}`}>
        <div className="text-center text-muted-foreground">
          <AlertCircle className="h-8 w-8 mx-auto mb-2" />
          <p>사용자 정보를 불러올 수 없습니다.</p>
        </div>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className={`p-6 ${className}`}>
        <div className="text-center text-destructive">
          <AlertCircle className="h-8 w-8 mx-auto mb-2" />
          <p>문서를 불러오는 중 오류가 발생했습니다.</p>
          <p className="text-sm text-muted-foreground mt-1">
            잠시 후 다시 시도해주세요.
          </p>
        </div>
      </Card>
    );
  }

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Search and Filter Controls */}
      <Card className="p-4">
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="문서 제목이나 유형으로 검색..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10"
            />
          </div>
          <div className="flex items-center gap-2">
            <Filter className="h-4 w-4 text-muted-foreground" />
            <select
              value={selectedDocType}
              onChange={(e) => setSelectedDocType(e.target.value)}
              className="px-3 py-2 border border-input rounded-md text-sm bg-background"
            >
              <option value="">모든 유형</option>
              <option value="primary_tendency">주요 성향</option>
              <option value="top_skills">상위 기술</option>
              <option value="top_jobs">추천 직업</option>
            </select>
          </div>
        </div>
      </Card>

      {/* Documents Grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => (
            <Card key={i} className="p-4">
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <Skeleton className="h-4 w-20" />
                  <Skeleton className="h-6 w-16" />
                </div>
                <Skeleton className="h-5 w-full" />
                <div className="space-y-2">
                  <Skeleton className="h-3 w-full" />
                  <Skeleton className="h-3 w-3/4" />
                </div>
                <Skeleton className="h-3 w-24" />
              </div>
            </Card>
          ))}
        </div>
      ) : filteredDocuments.length > 0 ? (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredDocuments.map((doc) => (
              <Card key={doc.id} className="p-4 hover:shadow-md transition-shadow cursor-pointer">
                <div className="space-y-3">
                  {/* Document Header */}
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      {getDocumentTypeIcon(doc.doc_type)}
                      <span className="text-sm font-medium">{doc.title}</span>
                    </div>
                    <Badge 
                      variant="secondary" 
                      className={getDocumentTypeColor(doc.doc_type)}
                    >
                      {getDocumentTypeLabel(doc.doc_type)}
                    </Badge>
                  </div>

                  {/* Document Preview */}
                  <div className="min-h-[80px]">
                    {renderDocumentPreview(doc)}
                  </div>

                  {/* Document Metadata */}
                  <div className="flex justify-between items-center text-xs text-muted-foreground">
                    <span>생성: {new Date(doc.created_at).toLocaleDateString('ko-KR')}</span>
                    <span>수정: {new Date(doc.updated_at).toLocaleDateString('ko-KR')}</span>
                  </div>
                </div>
              </Card>
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-center space-x-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
                disabled={currentPage === 1}
              >
                <ChevronLeft className="h-4 w-4" />
                이전
              </Button>
              
              <div className="flex items-center space-x-1">
                {[...Array(Math.min(5, totalPages))].map((_, i) => {
                  const pageNum = Math.max(1, Math.min(totalPages - 4, currentPage - 2)) + i;
                  if (pageNum > totalPages) return null;
                  
                  return (
                    <Button
                      key={pageNum}
                      variant={currentPage === pageNum ? "default" : "outline"}
                      size="sm"
                      onClick={() => setCurrentPage(pageNum)}
                      className="w-8 h-8 p-0"
                    >
                      {pageNum}
                    </Button>
                  );
                })}
              </div>

              <Button
                variant="outline"
                size="sm"
                onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
                disabled={currentPage === totalPages}
              >
                다음
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          )}
        </>
      ) : (
        <Card className="p-8">
          <div className="text-center text-muted-foreground">
            <FileText className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <h3 className="text-lg font-medium mb-2">문서가 없습니다</h3>
            <p className="text-sm">
              {searchTerm || selectedDocType 
                ? '검색 조건에 맞는 문서를 찾을 수 없습니다.' 
                : '아직 처리된 문서가 없습니다. ETL 처리를 통해 문서를 생성해보세요.'
              }
            </p>
          </div>
        </Card>
      )}
    </div>
  );
}
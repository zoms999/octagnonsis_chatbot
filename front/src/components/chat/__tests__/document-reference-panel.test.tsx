import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi } from 'vitest';
import { DocumentReferencePanel } from '../document-reference-panel';
import { DocumentReference } from '@/lib/types';

// Mock data
const mockDocuments: DocumentReference[] = [
  {
    id: '1',
    title: '적성 검사 결과 - 주요 성향',
    preview: '당신의 주요 성향은 분석적이고 체계적인 사고를 선호하며, 문제 해결에 있어서 논리적 접근을 중시합니다. 이러한 성향은 IT 분야나 연구직에 매우 적합합니다.',
    relevance_score: 0.95,
    type: 'primary_tendency'
  },
  {
    id: '2',
    title: '추천 직업군 - IT 분야',
    preview: '소프트웨어 개발자, 데이터 분석가, 시스템 엔지니어 등의 직업이 당신의 성향과 잘 맞습니다.',
    relevance_score: 0.87,
    type: 'top_jobs'
  },
  {
    id: '3',
    title: '핵심 역량 분석',
    preview: '논리적 사고, 문제 해결 능력, 분석력이 뛰어납니다.',
    relevance_score: 0.72,
    type: 'top_skills'
  }
];

describe('DocumentReferencePanel', () => {
  it('renders empty state when no documents provided', () => {
    render(<DocumentReferencePanel documents={[]} />);
    
    expect(screen.getByText('참조된 문서가 없습니다')).toBeInTheDocument();
    expect(screen.getByText('질문을 하시면 관련 문서가 여기에 표시됩니다')).toBeInTheDocument();
  });

  it('displays document count in header', () => {
    render(<DocumentReferencePanel documents={mockDocuments} />);
    
    expect(screen.getByText('참조 문서')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
    expect(screen.getByText('총 3개의 문서에서 정보를 참조했습니다')).toBeInTheDocument();
  });

  it('renders all documents with correct information', () => {
    render(<DocumentReferencePanel documents={mockDocuments} />);
    
    // Check document titles
    expect(screen.getByText('적성 검사 결과 - 주요 성향')).toBeInTheDocument();
    expect(screen.getByText('추천 직업군 - IT 분야')).toBeInTheDocument();
    expect(screen.getByText('핵심 역량 분석')).toBeInTheDocument();
    
    // Check document types
    expect(screen.getByText('주요 성향')).toBeInTheDocument();
    expect(screen.getByText('추천 직업')).toBeInTheDocument();
    expect(screen.getByText('핵심 역량')).toBeInTheDocument();
    
    // Check relevance scores
    expect(screen.getByText('95%')).toBeInTheDocument();
    expect(screen.getByText('87%')).toBeInTheDocument();
    expect(screen.getByText('72%')).toBeInTheDocument();
  });

  it('expands and collapses document details', async () => {
    render(<DocumentReferencePanel documents={mockDocuments} />);
    
    const firstDocument = mockDocuments[0];
    const expandButton = screen.getAllByLabelText('펼치기')[0];
    
    // Initially, full preview should not be visible (truncated)
    expect(screen.getByText(firstDocument.preview.substring(0, 50), { exact: false })).toBeInTheDocument();
    
    // Click expand button
    fireEvent.click(expandButton);
    
    // Now full preview should be visible
    await waitFor(() => {
      expect(screen.getByText(firstDocument.preview)).toBeInTheDocument();
    });
    
    // Check if document metadata is shown
    expect(screen.getByText(`문서 ID: ${firstDocument.id}`)).toBeInTheDocument();
    expect(screen.getByText('관련도: 95%')).toBeInTheDocument();
    
    // Click collapse button
    const collapseButton = screen.getByLabelText('접기');
    fireEvent.click(collapseButton);
    
    // Metadata should be hidden again
    await waitFor(() => {
      expect(screen.queryByText(`문서 ID: ${firstDocument.id}`)).not.toBeInTheDocument();
    });
  });

  it('handles panel collapse and expand', () => {
    const mockToggle = vi.fn();
    render(
      <DocumentReferencePanel 
        documents={mockDocuments} 
        isCollapsed={false}
        onToggle={mockToggle}
      />
    );
    
    const toggleButton = screen.getByLabelText('패널 닫기');
    fireEvent.click(toggleButton);
    
    expect(mockToggle).toHaveBeenCalledTimes(1);
  });

  it('shows collapsed state correctly', () => {
    render(
      <DocumentReferencePanel 
        documents={mockDocuments} 
        isCollapsed={true}
      />
    );
    
    // Should show document count in collapsed state
    expect(screen.getByText('3')).toBeInTheDocument();
    expect(screen.getByText(/참조/)).toBeInTheDocument();
    expect(screen.getByText(/문서/)).toBeInTheDocument();
    
    // Should not show document details
    expect(screen.queryByText('적성 검사 결과 - 주요 성향')).not.toBeInTheDocument();
  });

  it('applies correct relevance score colors', () => {
    render(<DocumentReferencePanel documents={mockDocuments} />);
    
    // High relevance (95%) should have green color
    const highRelevanceElement = screen.getByText('95%').closest('div');
    expect(highRelevanceElement).toHaveClass('text-green-600', 'bg-green-50');
    
    // Medium relevance (87%) should have green color (>= 0.8)
    const mediumRelevanceElement = screen.getByText('87%').closest('div');
    expect(mediumRelevanceElement).toHaveClass('text-green-600', 'bg-green-50');
    
    // Lower relevance (72%) should have yellow color (>= 0.6 && < 0.8)
    const lowRelevanceElement = screen.getByText('72%').closest('div');
    expect(lowRelevanceElement).toHaveClass('text-yellow-600', 'bg-yellow-50');
  });

  it('shows "더 보기" button for long previews', () => {
    const longPreviewDoc: DocumentReference = {
      id: '4',
      title: 'Long Document',
      preview: 'This is a very long preview text that should be truncated and show a "더 보기" button when displayed in the panel because it exceeds the normal length limit.',
      relevance_score: 0.8,
      type: 'test'
    };
    
    render(<DocumentReferencePanel documents={[longPreviewDoc]} />);
    
    expect(screen.getByText('더 보기')).toBeInTheDocument();
  });

  it('handles document type labels correctly', () => {
    const customTypeDoc: DocumentReference = {
      id: '5',
      title: 'Custom Type Document',
      preview: 'Test preview',
      relevance_score: 0.8,
      type: 'unknown_type'
    };
    
    render(<DocumentReferencePanel documents={[customTypeDoc]} />);
    
    // Should show default label for unknown type
    expect(screen.getByText('문서')).toBeInTheDocument();
  });
});
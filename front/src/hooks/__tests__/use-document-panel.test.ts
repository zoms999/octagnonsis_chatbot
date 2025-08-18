import { renderHook, act } from '@testing-library/react';
import { useDocumentPanel } from '../use-document-panel';
import { DocumentReference } from '@/lib/types';

// Mock window.innerWidth for responsive tests
const mockInnerWidth = (width: number) => {
  Object.defineProperty(window, 'innerWidth', {
    writable: true,
    configurable: true,
    value: width,
  });
};

// Mock documents
const mockDocuments: DocumentReference[] = [
  {
    id: '1',
    title: 'Document 1',
    preview: 'Preview 1',
    relevance_score: 0.95,
    type: 'primary_tendency'
  },
  {
    id: '2',
    title: 'Document 2',
    preview: 'Preview 2',
    relevance_score: 0.87,
    type: 'top_jobs'
  },
  {
    id: '3',
    title: 'Document 3',
    preview: 'Preview 3',
    relevance_score: 0.72,
    type: 'top_skills'
  }
];

describe('useDocumentPanel', () => {
  beforeEach(() => {
    // Reset window width to desktop size
    mockInnerWidth(1200);
  });

  it('initializes with default state', () => {
    const { result } = renderHook(() => useDocumentPanel());
    
    expect(result.current.documents).toEqual([]);
    expect(result.current.isCollapsed).toBe(false);
    expect(result.current.selectedDocumentId).toBe(null);
    expect(result.current.hasDocuments).toBe(false);
    expect(result.current.documentCount).toBe(0);
  });

  it('initializes with custom options', () => {
    const { result } = renderHook(() => 
      useDocumentPanel({ 
        initialCollapsed: true,
        autoCollapseOnMobile: false 
      })
    );
    
    expect(result.current.isCollapsed).toBe(true);
  });

  it('updates documents correctly', () => {
    const { result } = renderHook(() => useDocumentPanel());
    
    act(() => {
      result.current.updateDocuments(mockDocuments);
    });
    
    expect(result.current.documents).toEqual(mockDocuments);
    expect(result.current.hasDocuments).toBe(true);
    expect(result.current.documentCount).toBe(3);
    expect(result.current.isCollapsed).toBe(false); // Should auto-expand on desktop
  });

  it('clears documents correctly', () => {
    const { result } = renderHook(() => useDocumentPanel());
    
    act(() => {
      result.current.updateDocuments(mockDocuments);
    });
    
    expect(result.current.hasDocuments).toBe(true);
    
    act(() => {
      result.current.clearDocuments();
    });
    
    expect(result.current.documents).toEqual([]);
    expect(result.current.hasDocuments).toBe(false);
    expect(result.current.selectedDocumentId).toBe(null);
  });

  it('toggles collapsed state', () => {
    const { result } = renderHook(() => useDocumentPanel());
    
    expect(result.current.isCollapsed).toBe(false);
    
    act(() => {
      result.current.toggleCollapsed();
    });
    
    expect(result.current.isCollapsed).toBe(true);
    
    act(() => {
      result.current.toggleCollapsed();
    });
    
    expect(result.current.isCollapsed).toBe(false);
  });

  it('sets collapsed state explicitly', () => {
    const { result } = renderHook(() => useDocumentPanel());
    
    act(() => {
      result.current.setCollapsed(true);
    });
    
    expect(result.current.isCollapsed).toBe(true);
    
    act(() => {
      result.current.setCollapsed(false);
    });
    
    expect(result.current.isCollapsed).toBe(false);
  });

  it('selects documents correctly', () => {
    const { result } = renderHook(() => useDocumentPanel());
    
    act(() => {
      result.current.updateDocuments(mockDocuments);
    });
    
    act(() => {
      result.current.selectDocument('1');
    });
    
    expect(result.current.selectedDocumentId).toBe('1');
    expect(result.current.selectedDocument).toEqual(mockDocuments[0]);
    
    act(() => {
      result.current.selectDocument(null);
    });
    
    expect(result.current.selectedDocumentId).toBe(null);
    expect(result.current.selectedDocument).toBe(null);
  });

  it('gets document by ID', () => {
    const { result } = renderHook(() => useDocumentPanel());
    
    act(() => {
      result.current.updateDocuments(mockDocuments);
    });
    
    const document = result.current.getDocument('2');
    expect(document).toEqual(mockDocuments[1]);
    
    const nonExistentDocument = result.current.getDocument('999');
    expect(nonExistentDocument).toBeUndefined();
  });

  it('sorts documents by relevance', () => {
    const { result } = renderHook(() => useDocumentPanel());
    
    act(() => {
      result.current.updateDocuments(mockDocuments);
    });
    
    const sortedDocuments = result.current.getDocumentsSortedByRelevance();
    
    expect(sortedDocuments[0].relevance_score).toBe(0.95);
    expect(sortedDocuments[1].relevance_score).toBe(0.87);
    expect(sortedDocuments[2].relevance_score).toBe(0.72);
  });

  it('filters documents by type', () => {
    const { result } = renderHook(() => useDocumentPanel());
    
    act(() => {
      result.current.updateDocuments(mockDocuments);
    });
    
    const primaryTendencyDocs = result.current.getDocumentsByType('primary_tendency');
    expect(primaryTendencyDocs).toHaveLength(1);
    expect(primaryTendencyDocs[0].id).toBe('1');
    
    const nonExistentTypeDocs = result.current.getDocumentsByType('non_existent');
    expect(nonExistentTypeDocs).toHaveLength(0);
  });

  it('calculates document statistics correctly', () => {
    const { result } = renderHook(() => useDocumentPanel());
    
    act(() => {
      result.current.updateDocuments(mockDocuments);
    });
    
    const stats = result.current.getDocumentStats();
    
    expect(stats.total).toBe(3);
    expect(stats.averageRelevance).toBeCloseTo(0.8467, 4);
    expect(stats.highRelevanceCount).toBe(2); // >= 0.8 (0.95, 0.87)
    expect(stats.mediumRelevanceCount).toBe(1); // >= 0.6 && < 0.8 (0.72)
    expect(stats.lowRelevanceCount).toBe(0); // < 0.6
    expect(stats.typeGroups).toEqual({
      'primary_tendency': 1,
      'top_jobs': 1,
      'top_skills': 1
    });
  });

  it('handles mobile responsiveness', () => {
    // Mock mobile width
    mockInnerWidth(500);
    
    const { result } = renderHook(() => useDocumentPanel());
    
    // Trigger resize event
    act(() => {
      window.dispatchEvent(new Event('resize'));
    });
    
    expect(result.current.isMobile).toBe(true);
    
    // When updating documents on mobile, should stay collapsed
    act(() => {
      result.current.updateDocuments(mockDocuments);
    });
    
    expect(result.current.isCollapsed).toBe(true);
  });

  it('auto-collapses on mobile when autoCollapseOnMobile is enabled', () => {
    const { result } = renderHook(() => 
      useDocumentPanel({ autoCollapseOnMobile: true })
    );
    
    // Start with expanded state
    act(() => {
      result.current.setCollapsed(false);
    });
    
    expect(result.current.isCollapsed).toBe(false);
    
    // Switch to mobile
    mockInnerWidth(500);
    act(() => {
      window.dispatchEvent(new Event('resize'));
    });
    
    expect(result.current.isCollapsed).toBe(true);
  });

  it('does not auto-collapse on mobile when autoCollapseOnMobile is disabled', () => {
    const { result } = renderHook(() => 
      useDocumentPanel({ autoCollapseOnMobile: false })
    );
    
    // Start with expanded state
    act(() => {
      result.current.setCollapsed(false);
    });
    
    expect(result.current.isCollapsed).toBe(false);
    
    // Switch to mobile
    mockInnerWidth(500);
    act(() => {
      window.dispatchEvent(new Event('resize'));
    });
    
    // Should remain expanded
    expect(result.current.isCollapsed).toBe(false);
  });
});
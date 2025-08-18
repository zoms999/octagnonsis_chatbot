'use client';

import { useState, useCallback, useEffect } from 'react';
import { DocumentReference } from '@/lib/types';

interface DocumentPanelState {
  documents: DocumentReference[];
  isCollapsed: boolean;
  selectedDocumentId: string | null;
}

interface UseDocumentPanelOptions {
  initialCollapsed?: boolean;
  autoCollapseOnMobile?: boolean;
}

export function useDocumentPanel(options: UseDocumentPanelOptions = {}) {
  const { initialCollapsed = false, autoCollapseOnMobile = true } = options;
  
  const [state, setState] = useState<DocumentPanelState>({
    documents: [],
    isCollapsed: initialCollapsed,
    selectedDocumentId: null,
  });

  const [isMobile, setIsMobile] = useState(false);

  // Handle responsive behavior
  useEffect(() => {
    if (!autoCollapseOnMobile) return;

    const checkMobile = () => {
      const mobile = window.innerWidth < 1024; // lg breakpoint
      setIsMobile(mobile);
      
      // Auto-collapse on mobile
      if (mobile && !state.isCollapsed) {
        setState(prev => ({ ...prev, isCollapsed: true }));
      }
    };

    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, [autoCollapseOnMobile, state.isCollapsed]);

  // Update documents from chat response
  const updateDocuments = useCallback((documents: DocumentReference[]) => {
    setState(prev => ({
      ...prev,
      documents,
      // Auto-expand panel when new documents arrive (unless on mobile)
      isCollapsed: isMobile ? true : (documents.length === 0 ? prev.isCollapsed : false)
    }));
  }, [isMobile]);

  // Clear documents
  const clearDocuments = useCallback(() => {
    setState(prev => ({
      ...prev,
      documents: [],
      selectedDocumentId: null,
    }));
  }, []);

  // Toggle panel collapse state
  const toggleCollapsed = useCallback(() => {
    setState(prev => ({
      ...prev,
      isCollapsed: !prev.isCollapsed,
    }));
  }, []);

  // Set collapsed state explicitly
  const setCollapsed = useCallback((collapsed: boolean) => {
    setState(prev => ({
      ...prev,
      isCollapsed: collapsed,
    }));
  }, []);

  // Select a specific document
  const selectDocument = useCallback((documentId: string | null) => {
    setState(prev => ({
      ...prev,
      selectedDocumentId: documentId,
    }));
  }, []);

  // Get document by ID
  const getDocument = useCallback((documentId: string): DocumentReference | undefined => {
    return state.documents.find(doc => doc.id === documentId);
  }, [state.documents]);

  // Get documents sorted by relevance
  const getDocumentsSortedByRelevance = useCallback((): DocumentReference[] => {
    return [...state.documents].sort((a, b) => b.relevance_score - a.relevance_score);
  }, [state.documents]);

  // Get documents filtered by type
  const getDocumentsByType = useCallback((type: string): DocumentReference[] => {
    return state.documents.filter(doc => doc.type === type);
  }, [state.documents]);

  // Get document statistics
  const getDocumentStats = useCallback(() => {
    const total = state.documents.length;
    const avgRelevance = total > 0 
      ? state.documents.reduce((sum, doc) => sum + doc.relevance_score, 0) / total 
      : 0;
    
    const typeGroups = state.documents.reduce((acc, doc) => {
      acc[doc.type] = (acc[doc.type] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);

    return {
      total,
      averageRelevance: avgRelevance,
      typeGroups,
      highRelevanceCount: state.documents.filter(doc => doc.relevance_score >= 0.8).length,
      mediumRelevanceCount: state.documents.filter(doc => doc.relevance_score >= 0.6 && doc.relevance_score < 0.8).length,
      lowRelevanceCount: state.documents.filter(doc => doc.relevance_score < 0.6).length,
    };
  }, [state.documents]);

  return {
    // State
    documents: state.documents,
    isCollapsed: state.isCollapsed,
    selectedDocumentId: state.selectedDocumentId,
    isMobile,
    
    // Actions
    updateDocuments,
    clearDocuments,
    toggleCollapsed,
    setCollapsed,
    selectDocument,
    
    // Getters
    getDocument,
    getDocumentsSortedByRelevance,
    getDocumentsByType,
    getDocumentStats,
    
    // Computed values
    hasDocuments: state.documents.length > 0,
    documentCount: state.documents.length,
    selectedDocument: state.selectedDocumentId ? getDocument(state.selectedDocumentId) : null,
  };
}
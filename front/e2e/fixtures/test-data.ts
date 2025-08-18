// Test data fixtures for E2E tests

export const testUsers = {
  personal: {
    username: 'test_personal_user',
    password: 'test_password_123',
    loginType: 'personal' as const,
  },
  organization: {
    username: 'test_org_user',
    password: 'test_password_123',
    loginType: 'organization' as const,
    sessionCode: 'TEST_SESSION_001',
  },
  admin: {
    username: 'test_admin_user',
    password: 'admin_password_123',
    loginType: 'organization' as const,
    sessionCode: 'ADMIN_SESSION_001',
  },
};

export const mockApiResponses = {
  loginSuccess: {
    user: {
      id: 'test-user-123',
      name: 'Test User',
      type: 'personal',
      ac_id: 'AC123456',
      sex: 'M',
      isPaid: true,
      productType: 'premium',
      isExpired: false,
      state: 'active',
    },
    tokens: {
      access: 'mock-access-token',
      refresh: 'mock-refresh-token',
    },
    expires_at: '2024-12-31T23:59:59Z',
  },
  
  chatResponse: {
    conversation_id: 'conv-123',
    response: 'Based on your aptitude test results, you show strong analytical skills...',
    retrieved_documents: [
      {
        id: 'doc-1',
        type: 'primary_tendency',
        title: 'Primary Aptitude Analysis',
        preview: 'Your primary tendency shows...',
        relevance_score: 0.95,
      },
    ],
    confidence_score: 0.87,
    processing_time: 1.2,
    timestamp: '2024-01-15T10:30:00Z',
  },

  conversationHistory: {
    conversations: [
      {
        id: 'conv-1',
        title: 'Career Path Discussion',
        last_message: 'What are my strongest skills?',
        created_at: '2024-01-15T09:00:00Z',
        message_count: 5,
      },
      {
        id: 'conv-2',
        title: 'Job Recommendations',
        last_message: 'Which jobs suit my profile?',
        created_at: '2024-01-14T14:30:00Z',
        message_count: 8,
      },
    ],
    total: 2,
    page: 1,
    limit: 10,
  },

  etlJobs: {
    jobs: [
      {
        job_id: 'job-123',
        status: 'completed',
        progress: 100,
        current_step: 'Completed',
        created_at: '2024-01-15T08:00:00Z',
        updated_at: '2024-01-15T08:05:00Z',
      },
      {
        job_id: 'job-124',
        status: 'running',
        progress: 65,
        current_step: 'Processing documents',
        estimated_completion_time: '2024-01-15T10:45:00Z',
        created_at: '2024-01-15T10:30:00Z',
        updated_at: '2024-01-15T10:35:00Z',
      },
    ],
    total: 2,
  },

  userProfile: {
    user_id: 'test-user-123',
    document_count: 15,
    conversation_count: 8,
    available_document_types: ['primary_tendency', 'top_skills', 'top_jobs'],
    last_conversation_at: '2024-01-15T10:30:00Z',
    processing_status: 'completed',
  },

  userDocuments: {
    documents: [
      {
        id: 'doc-1',
        doc_type: 'primary_tendency',
        title: 'Primary Aptitude Analysis',
        preview: {
          primary_tendency: 'Analytical and Problem-Solving',
          summary: 'Strong analytical capabilities with excellent problem-solving skills.',
        },
        created_at: '2024-01-10T12:00:00Z',
        updated_at: '2024-01-10T12:00:00Z',
      },
      {
        id: 'doc-2',
        doc_type: 'top_skills',
        title: 'Top Skills Assessment',
        preview: {
          top_skills: ['Data Analysis', 'Critical Thinking', 'Research'],
          summary: 'Exceptional skills in data analysis and research methodologies.',
        },
        created_at: '2024-01-10T12:00:00Z',
        updated_at: '2024-01-10T12:00:00Z',
      },
    ],
    total: 2,
    page: 1,
    limit: 10,
  },
};

export const testMessages = {
  questions: [
    'What are my strongest aptitudes?',
    'Which career paths suit my profile?',
    'How do my skills compare to industry standards?',
    'What areas should I focus on for improvement?',
  ],
  
  responses: [
    'Based on your aptitude test results, your strongest areas are analytical thinking and problem-solving.',
    'Your profile suggests excellent fit for careers in data science, research, and strategic planning.',
    'Your analytical skills rank in the top 15% compared to industry benchmarks.',
    'Consider developing your communication skills to complement your strong technical abilities.',
  ],
};
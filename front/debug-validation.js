// Debug validation logic
const { validateLoginCredentials } = require('./src/lib/auth.ts');

// Test case 1: Organization login without session code
const credentials1 = {
  username: 'testuser',
  password: 'password123',
  loginType: 'organization',
  sessionCode: ''
};

console.log('Test 1 - Organization without session code:');
console.log('Credentials:', credentials1);
console.log('Validation errors:', validateLoginCredentials(credentials1));

// Test case 2: Personal login (should pass)
const credentials2 = {
  username: 'testuser',
  password: 'password123',
  loginType: 'personal',
  sessionCode: undefined
};

console.log('\nTest 2 - Personal login:');
console.log('Credentials:', credentials2);
console.log('Validation errors:', validateLoginCredentials(credentials2));
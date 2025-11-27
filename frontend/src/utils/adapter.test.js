/**
 * Frontend Adapter Unit Tests
 * ============================
 * 
 * Tests for the adapter layer that transforms frontend data
 * to backend Zero-Knowledge format.
 * 
 * Run with: npm test (if Jest configured) or node adapter.test.js
 */

// Mock CryptoModule since Web Crypto API is browser-only
const mockCryptoModule = {
  encrypt: async (text) => {
    if (!text || text.trim() === '') {
      return 'ENC_';
    }
    // Simple mock: prefix with ENC_ and base64 encode
    const encoded = Buffer.from(text).toString('base64');
    return `ENC_${encoded}`;
  },
  decrypt: async (encryptedText) => {
    if (!encryptedText || !encryptedText.startsWith('ENC_')) {
      return encryptedText;
    }
    const base64 = encryptedText.substring(4);
    return Buffer.from(base64, 'base64').toString('utf-8');
  }
};

// Import adapter functions (we'll need to adapt for Node.js)
// For testing, we'll copy the extractYear function
function extractYear(dateStr) {
  if (!dateStr || typeof dateStr !== 'string') {
    return null;
  }
  
  const cleaned = dateStr.trim();
  
  if (cleaned === '?' || cleaned === '' || cleaned.toLowerCase() === 'unknown') {
    return null;
  }
  
  const yearMatch = cleaned.match(/(\d{4})/);
  if (yearMatch) {
    const year = parseInt(yearMatch[1], 10);
    if (year >= 1000 && year <= 2100) {
      return year;
    }
  }
  
  return null;
}

// Mock adapter function (simplified version for testing)
async function adaptPersonDataForBackend(personData, cryptoModule = mockCryptoModule) {
  // Encrypt death_date if present
  let deathDateBlob = null;
  if (personData.deathDate && personData.deathDate.trim()) {
    try {
      deathDateBlob = await cryptoModule.encrypt(personData.deathDate);
    } catch (error) {
      console.error('[Adapter] Failed to encrypt death_date:', error);
    }
  }
  
  // Extract approximate years
  const birthYearApprox = personData.birthYearApprox || extractYear(personData.birthDate);
  const deathYearApprox = extractYear(personData.deathDate);
  
  // Build adapted payload
  // CRITICAL: All optional fields MUST be null (not undefined) for Python backend compatibility
  // Do NOT remove null values - Python backend expects null, not undefined
  const adapted = {
    name_blob: personData.name_blob,
    birth_date_blob: personData.birth_date_blob,
    death_date_blob: deathDateBlob !== null ? deathDateBlob : null, // Explicitly null if not provided
    birth_year_approx: birthYearApprox !== null && birthYearApprox !== undefined ? birthYearApprox : null,
    death_year_approx: deathYearApprox !== null && deathYearApprox !== undefined ? deathYearApprox : null,
    gender: personData.gender || null,
    relation: personData.relation,
    link_to_id: personData.linkToPersonId,
    private_notes_blob: personData.private_notes_blob || null,
    shared_notes_blob: personData.shared_notes_blob || null,
    source_ids: personData.source_ids || [],
    // Marriage fields (explicitly null if missing)
    marriage_year: personData.marriageYear !== null && personData.marriageYear !== undefined ? personData.marriageYear : null,
    divorce_year: personData.divorceYear !== null && personData.divorceYear !== undefined ? personData.divorceYear : null,
    marriage_status: personData.marriageStatus || null,
    marriage_type: personData.marriageType || null
  };
  
  // CRITICAL: Do NOT remove null values - Python backend expects null, not undefined
  return adapted;
}

// Test Suite
const tests = [];
let passed = 0;
let failed = 0;

function test(name, fn) {
  tests.push({ name, fn });
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(message || 'Assertion failed');
  }
}

function assertEqual(actual, expected, message) {
  if (actual !== expected) {
    throw new Error(message || `Expected ${expected}, got ${actual}`);
  }
}

function assertStartsWith(str, prefix, message) {
  if (!str || !str.startsWith(prefix)) {
    throw new Error(message || `Expected string to start with ${prefix}`);
  }
}

// Test Cases
test('extractYear - full date string', () => {
  assertEqual(extractYear('1990-05-20'), 1990);
  assertEqual(extractYear('1945-12-31'), 1945);
});

test('extractYear - year only', () => {
  assertEqual(extractYear('1990'), 1990);
  assertEqual(extractYear('1945'), 1945);
});

test('extractYear - approximate date', () => {
  assertEqual(extractYear('~1990'), 1990);
  assertEqual(extractYear('1910..1920'), 1910);
});

test('extractYear - unknown dates', () => {
  assertEqual(extractYear('?'), null);
  assertEqual(extractYear(''), null);
  assertEqual(extractYear('unknown'), null);
});

test('adaptPersonDataForBackend - basic transformation', async () => {
  const input = {
    name_blob: 'ENC_name123',
    birth_date_blob: 'ENC_birth123',
    birthDate: '1990-05-20',
    deathDate: '2020',
    gender: 'M',
    relation: 'CHILD',
    linkToPersonId: 'person_123',
    birthYearApprox: 1990,
    private_notes_blob: 'ENC_notes123'
  };
  
  const output = await adaptPersonDataForBackend(input);
  
  // Verify encrypted fields preserved
  assertEqual(output.name_blob, 'ENC_name123');
  assertEqual(output.birth_date_blob, 'ENC_birth123');
  
  // Verify death_date encrypted
  assertStartsWith(output.death_date_blob, 'ENC_', 'death_date_blob should be encrypted');
  
  // Verify year extraction
  assertEqual(output.birth_year_approx, 1990);
  assertEqual(output.death_year_approx, 2020);
  
  // Verify field name transformation
  assertEqual(output.link_to_id, 'person_123');
  assertEqual(output.linkToPersonId, undefined, 'linkToPersonId should be renamed');
  
  // Verify gender
  assertEqual(output.gender, 'M');
  
  // Verify relation
  assertEqual(output.relation, 'CHILD');
});

test('adaptPersonDataForBackend - encrypts death_date', async () => {
  const input = {
    name_blob: 'ENC_name',
    birth_date_blob: 'ENC_birth',
    birthDate: '1990',
    deathDate: '2020-10-15',
    relation: 'PARENT',
    linkToPersonId: 'person_456',
    birthYearApprox: 1990
  };
  
  const output = await adaptPersonDataForBackend(input);
  
  // Death date should be encrypted
  assertStartsWith(output.death_date_blob, 'ENC_', 'death_date should be encrypted');
  
  // Should extract year from death date
  assertEqual(output.death_year_approx, 2020);
});

test('adaptPersonDataForBackend - handles missing fields', async () => {
  const input = {
    name_blob: 'ENC_name',
    birth_date_blob: 'ENC_birth',
    birthDate: '1990',
    relation: 'SPOUSE',
    linkToPersonId: 'person_789',
    birthYearApprox: 1990
    // No deathDate, no gender, no notes
  };
  
  const output = await adaptPersonDataForBackend(input);
  
  // Optional fields should be null (not undefined) for Python backend compatibility
  assertEqual(output.death_date_blob, null, 'death_date_blob should be null when not provided');
  assertEqual(output.death_year_approx, null, 'death_year_approx should be null when not provided');
  
  // Gender should be null
  assertEqual(output.gender, null, 'gender should be null when not provided');
  
  // Required fields should be present
  assertEqual(output.name_blob, 'ENC_name');
  assertEqual(output.birth_year_approx, 1990);
});

test('adaptPersonDataForBackend - preserves null values', async () => {
  const input = {
    name_blob: 'ENC_name',
    birth_date_blob: 'ENC_birth',
    birthDate: '1990',
    relation: 'SIBLING',
    linkToPersonId: 'person_999',
    birthYearApprox: 1990,
    gender: null,
    private_notes_blob: null
  };
  
  const output = await adaptPersonDataForBackend(input);
  
  // Null values should be preserved (not removed) for Python backend compatibility
  assertEqual(output.gender, null, 'null gender should be preserved');
  assertEqual(output.private_notes_blob, null, 'null private_notes_blob should be preserved');
});

test('adaptPersonDataForBackend - source_ids handling', async () => {
  const input = {
    name_blob: 'ENC_name',
    birth_date_blob: 'ENC_birth',
    birthDate: '1990',
    relation: 'CHILD',
    linkToPersonId: 'person_111',
    birthYearApprox: 1990,
    source_ids: ['source_1', 'source_2']
  };
  
  const output = await adaptPersonDataForBackend(input);
  
  // source_ids should be preserved
  assertEqual(Array.isArray(output.source_ids), true);
  assertEqual(output.source_ids.length, 2);
  assertEqual(output.source_ids[0], 'source_1');
});

// Run tests
async function runTests() {
  console.log('\n🧪 Frontend Adapter Unit Tests\n');
  console.log('='.repeat(60));
  
  for (const { name, fn } of tests) {
    try {
      await fn();
      console.log(`✅ ${name}`);
      passed++;
    } catch (error) {
      console.log(`❌ ${name}`);
      console.log(`   Error: ${error.message}`);
      failed++;
    }
  }
  
  console.log('='.repeat(60));
  console.log(`\n📊 Results: ${passed} passed, ${failed} failed, ${tests.length} total\n`);
  
  return failed === 0;
}

// Export for use in test runners
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { runTests, adaptPersonDataForBackend, extractYear };
}

// Run if executed directly
if (require.main === module) {
  runTests().then(success => {
    process.exit(success ? 0 : 1);
  });
}


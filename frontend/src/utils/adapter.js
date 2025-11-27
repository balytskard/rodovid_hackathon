/**
 * Frontend-Backend Adapter Layer
 * ===============================
 * Bridges PARTNER_PROJECT frontend format to MY_BACKEND backend API expectations.
 */

import { CryptoModule } from './crypto';

/**
 * Extract year from date string (flexible format support)
 */
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

export function extractYearFromDate(dateStr) {
  return extractYear(dateStr);
}

/**
 * Adapt frontend person data to backend API format
 */
export async function adaptPersonDataForBackend(personData) {
  // Encrypt death_date if present
  let deathDateBlob = null;
  if (personData.deathDate && personData.deathDate.trim()) {
    try {
      deathDateBlob = await CryptoModule.encrypt(personData.deathDate);
    } catch (error) {
      console.error('[Adapter] Failed to encrypt death_date:', error);
    }
  }
  
  const birthYearApprox = personData.birthYearApprox || extractYear(personData.birthDate);
  const deathYearApprox = extractYear(personData.deathDate);
  
  // Build adapted payload
  // IMPORTANT: All optional fields MUST be null (not undefined) for Python backend compatibility
  const adapted = {
    // Encrypted fields (required)
    name_blob: personData.name_blob,
    birth_date_blob: personData.birth_date_blob,
    
    // Optional encrypted fields - explicitly set to null if missing
    death_date_blob: deathDateBlob !== null ? deathDateBlob : null,
    birth_place_blob: personData.birth_place_blob || null,
    death_place_blob: personData.death_place_blob || null,
    private_notes_blob: personData.private_notes_blob || null,
    shared_notes_blob: personData.shared_notes_blob || null,
    
    // Validation fields (required)
    birth_year_approx: birthYearApprox !== null && birthYearApprox !== undefined ? birthYearApprox : null,
    death_year_approx: deathYearApprox !== null && deathYearApprox !== undefined ? deathYearApprox : null,
    gender: personData.gender || null,
    
    // Relationship fields (required)
    relation: personData.relation,
    link_to_id: personData.linkToPersonId,
    
    // Sources (always array, empty if not provided)
    source_ids: personData.source_ids || [],
    
    // Marriage fields (optional - explicitly null if missing)
    marriage_year: personData.marriageYear !== null && personData.marriageYear !== undefined ? personData.marriageYear : null,
    divorce_year: personData.divorceYear !== null && personData.divorceYear !== undefined ? personData.divorceYear : null,
    marriage_status: personData.marriageStatus || null,
    marriage_type: personData.marriageType || null
  };
  
  // CRITICAL: Do NOT remove null values - Python backend expects null, not undefined
  // All optional fields are explicitly set to null when missing
  return adapted;
}

export function validateAdaptedPayload(adapted) {
  const errors = [];
  
  if (!adapted.name_blob || !adapted.name_blob.startsWith('ENC_')) {
    errors.push('name_blob must be encrypted (start with ENC_)');
  }
  
  if (!adapted.birth_date_blob || !adapted.birth_date_blob.startsWith('ENC_')) {
    errors.push('birth_date_blob must be encrypted (start with ENC_)');
  }
  
  if (!adapted.relation) {
    errors.push('relation is required');
  }
  
  if (!adapted.link_to_id) {
    errors.push('link_to_id is required');
  }
  
  if (adapted.birth_year_approx === null || adapted.birth_year_approx === undefined) {
    errors.push('birth_year_approx is required for validation');
  }
  
  if (adapted.gender && !['M', 'F'].includes(adapted.gender)) {
    errors.push('gender must be M or F');
  }
  
  return {
    valid: errors.length === 0,
    errors
  };
}

/**
 * Crypto Module для E2E шифрування
 * Використовує Web Crypto API
 */

let encryptionKey = null;

async function generateKey(password = 'demo-key-родовід-2025') {
    const encoder = new TextEncoder();
    const data = encoder.encode(password);
    const hash = await crypto.subtle.digest('SHA-256', data);
    
    encryptionKey = await crypto.subtle.importKey(
        'raw',
        hash,
        { name: 'AES-GCM' },
        false,
        ['encrypt', 'decrypt']
    );
    
    return encryptionKey;
}

async function encrypt(text) {
    if (!encryptionKey) {
        await generateKey();
    }

    if (!text || text.trim() === '') {
        return 'ENC_'; // Повертаємо мінімальний blob для порожніх значень
    }

    try {
        const encoder = new TextEncoder();
        const data = encoder.encode(text);
        const iv = crypto.getRandomValues(new Uint8Array(12));
        
        const encrypted = await crypto.subtle.encrypt(
            { name: 'AES-GCM', iv },
            encryptionKey,
            data
        );

        const combined = new Uint8Array(iv.length + encrypted.byteLength);
        combined.set(iv);
        combined.set(new Uint8Array(encrypted), iv.length);

        const result = 'ENC_' + btoa(String.fromCharCode(...combined));
        console.log(`[Crypto] Encrypted: "${text.substring(0, 20)}..." -> "${result.substring(0, 30)}..."`);
        return result;
    } catch (error) {
        console.error('Encryption error:', error);
        // Не повертаємо незашифрований текст - це небезпечно
        throw new Error(`Помилка шифрування: ${error.message}`);
    }
}

async function decrypt(encryptedText) {
    if (!encryptionKey) {
        await generateKey();
    }

    if (!encryptedText) {
        return '';
    }

    // Якщо це не encrypted blob, повертаємо як є
    if (!encryptedText.startsWith('ENC_')) {
        console.warn('[Crypto] Attempting to decrypt non-encrypted text:', encryptedText.substring(0, 20));
        return encryptedText;
    }

    try {
        const base64 = encryptedText.substring(4);
        const combined = Uint8Array.from(atob(base64), c => c.charCodeAt(0));
        
        if (combined.length < 12) {
            console.error('[Crypto] Invalid encrypted data - too short');
            return '[Помилка: невалідні дані]';
        }

        const iv = combined.slice(0, 12);
        const data = combined.slice(12);

        const decrypted = await crypto.subtle.decrypt(
            { name: 'AES-GCM', iv },
            encryptionKey,
            data
        );

        const result = new TextDecoder().decode(decrypted);
        console.log(`[Crypto] Decrypted successfully: "${encryptedText.substring(0, 20)}..." -> "${result.substring(0, 20)}..."`);
        return result;
    } catch (error) {
        console.error('[Crypto] Decryption error:', error);
        return '[Помилка розшифрування]';
    }
}

function isEncrypted(text) {
    return text && text.startsWith('ENC_');
}

// Ініціалізація при завантаженні
generateKey();

export const CryptoModule = {
    generateKey,
    encrypt,
    decrypt,
    isEncrypted
};


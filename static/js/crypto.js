class GroupChatCrypto {
    constructor() {
        this.rsaKeyPair = null; // RSA key pair for the user
        this.participants = {}; // Stores public RSA keys of all participants
        this.aesKey = null; // Group AES key
    }

    // Generate RSA key pair for the user
    async generateRSAKeyPair() {
        this.rsaKeyPair = await window.crypto.subtle.generateKey(
            {
                name: "RSA-OAEP",
                modulusLength: 2048,
                publicExponent: new Uint8Array([1, 0, 1]),
                hash: "SHA-256",
            },
            true,
            ["encrypt", "decrypt"]
        );
    }

    // Export the user's public RSA key
    async exportPublicKey() {
        const exported = await window.crypto.subtle.exportKey("spki", this.rsaKeyPair.publicKey);
        return btoa(String.fromCharCode(...new Uint8Array(exported)));
    }

    // Import a participant's public RSA key
    async importPublicKey(base64Key, participantId) {
        const keyBuffer = Uint8Array.from(atob(base64Key), (c) => c.charCodeAt(0));
        const publicKey = await window.crypto.subtle.importKey(
            "spki",
            keyBuffer,
            { name: "RSA-OAEP", hash: "SHA-256" },
            true,
            ["encrypt"]
        );
        this.participants[participantId] = publicKey;
    }

    // Generate a group AES key (for the group creator)
    async generateAESKey() {
        this.aesKey = await window.crypto.subtle.generateKey(
            {
                name: "AES-GCM",
                length: 256,
            },
            true,
            ["encrypt", "decrypt"]
        );
    }

    // Encrypt the AES key for a participant
    async encryptAESKeyForParticipant(participantId) {
        if (!this.aesKey || !this.participants[participantId]) {
            throw new Error("Missing AES key or participant public key");
        }

        const rawAESKey = await window.crypto.subtle.exportKey("raw", this.aesKey);
        const encryptedAESKey = await window.crypto.subtle.encrypt(
            { name: "RSA-OAEP" },
            this.participants[participantId],
            rawAESKey
        );
        return btoa(String.fromCharCode(...new Uint8Array(encryptedAESKey)));
    }

    // Decrypt the AES key using the user's private RSA key
    async decryptAESKey(encryptedAESKeyBase64) {
        const encryptedKeyBuffer = Uint8Array.from(
            atob(encryptedAESKeyBase64),
            (c) => c.charCodeAt(0)
        );
        const rawAESKey = await window.crypto.subtle.decrypt(
            { name: "RSA-OAEP" },
            this.rsaKeyPair.privateKey,
            encryptedKeyBuffer
        );
        this.aesKey = await window.crypto.subtle.importKey(
            "raw",
            rawAESKey,
            { name: "AES-GCM" },
            true,
            ["encrypt", "decrypt"]
        );
    }

    // Encrypt a message using the AES key
    async encryptMessage(message) {
        if (!this.aesKey) throw new Error("AES key is not set");

        const iv = crypto.getRandomValues(new Uint8Array(12)); // Generate a random IV
        const encodedMessage = new TextEncoder().encode(message);
        const encryptedData = await window.crypto.subtle.encrypt(
            { name: "AES-GCM", iv: iv },
            this.aesKey,
            encodedMessage
        );

        return {
            ciphertext: btoa(String.fromCharCode(...new Uint8Array(encryptedData))),
            iv: btoa(String.fromCharCode(...iv)),
        };
    }

    // Decrypt a message using the AES key
    async decryptMessage(ciphertextBase64, ivBase64) {
        if (!this.aesKey) throw new Error("AES key is not set");

        const ciphertextBuffer = Uint8Array.from(atob(ciphertextBase64), (c) => c.charCodeAt(0));
        const ivBuffer = Uint8Array.from(atob(ivBase64), (c) => c.charCodeAt(0));
        const decryptedData = await window.crypto.subtle.decrypt(
            { name: "AES-GCM", iv: ivBuffer },
            this.aesKey,
            ciphertextBuffer
        );

        return new TextDecoder().decode(decryptedData);
    }
}
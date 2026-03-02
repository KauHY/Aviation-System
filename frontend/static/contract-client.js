class SignatureUtils {
    static async importPrivateKey(pem) {
        const pemHeader = "-----BEGIN PRIVATE KEY-----";
        const pemFooter = "-----END PRIVATE KEY-----";
        
        // 移除 PEM 头部和尾部
        let pemContents = pem.substring(pemHeader.length, pem.length - pemFooter.length);
        
        // 逐个字符过滤，只保留Base64字符
        const base64Chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=';
        let cleanPem = '';
        for (let i = 0; i < pemContents.length; i++) {
            const char = pemContents[i];
            if (base64Chars.includes(char)) {
                cleanPem += char;
            }
        }
        
        // 使用 Base64 解码
        const binaryDerString = window.atob(cleanPem);
        const binaryDer = new Uint8Array(binaryDerString.length);
        for (let i = 0; i < binaryDerString.length; i++) {
            binaryDer[i] = binaryDerString.charCodeAt(i);
        }
        
        return await window.crypto.subtle.importKey(
            "pkcs8",
            binaryDer.buffer,
            {
                name: "RSASSA-PKCS1-v1_5",
                hash: "SHA-256"
            },
            false,
            ["sign"]
        );
    }

    static async importPublicKey(pem) {
        const pemHeader = "-----BEGIN PUBLIC KEY-----";
        const pemFooter = "-----END PUBLIC KEY-----";
        
        let pemContents = pem.substring(pemHeader.length, pem.length - pemFooter.length);
        
        const base64Chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=';
        let cleanPem = '';
        for (let i = 0; i < pemContents.length; i++) {
            const char = pemContents[i];
            if (base64Chars.includes(char)) {
                cleanPem += char;
            }
        }
        
        const binaryDerString = window.atob(cleanPem);
        const binaryDer = new Uint8Array(binaryDerString.length);
        for (let i = 0; i < binaryDerString.length; i++) {
            binaryDer[i] = binaryDerString.charCodeAt(i);
        }
        
        return await window.crypto.subtle.importKey(
            "spki",
            binaryDer.buffer,
            {
                name: "RSASSA-PKCS1-v1_5",
                hash: "SHA-256"
            },
            false,
            ["verify"]
        );
    }

    static sortObjectKeys(obj) {
        if (typeof obj !== 'object' || obj === null) {
            return obj;
        }
        
        if (Array.isArray(obj)) {
            return obj.map(item => this.sortObjectKeys(item));
        }
        
        return Object.keys(obj)
            .sort()
            .reduce((sorted, key) => {
                sorted[key] = this.sortObjectKeys(obj[key]);
                return sorted;
            }, {});
    }

    static async sign(privateKey, data) {
        const sortedData = this.sortObjectKeys(data);
        console.log('[DEBUG] sign - 原始数据:', data);
        console.log('[DEBUG] sign - 排序后数据:', sortedData);
        const jsonString = JSON.stringify(sortedData);
        console.log('[DEBUG] sign - JSON字符串:', jsonString);
        
        const encoder = new TextEncoder();
        const dataBuffer = encoder.encode(jsonString);
        console.log('[DEBUG] sign - 数据缓冲区长度:', dataBuffer.length);
        console.log('[DEBUG] sign - 数据缓冲区前20字节:', Array.from(dataBuffer.slice(0, 20)).map(b => b.toString(16).padStart(2, '0')).join(' '));
        
        const signature = await window.crypto.subtle.sign(
            "RSASSA-PKCS1-v1_5",
            privateKey,
            dataBuffer
        );
        
        return Array.from(new Uint8Array(signature))
            .map(b => b.toString(16).padStart(2, '0'))
            .join('');
    }

    static async verify(publicKey, signature, data) {
        const sortedData = this.sortObjectKeys(data);
        console.log('[DEBUG] verify - 原始数据:', data);
        console.log('[DEBUG] verify - 排序后数据:', sortedData);
        const jsonString = JSON.stringify(sortedData);
        console.log('[DEBUG] verify - JSON字符串:', jsonString);
        
        const encoder = new TextEncoder();
        const dataBuffer = encoder.encode(jsonString);
        console.log('[DEBUG] verify - 数据缓冲区长度:', dataBuffer.length);
        console.log('[DEBUG] verify - 数据缓冲区前20字节:', Array.from(dataBuffer.slice(0, 20)).map(b => b.toString(16).padStart(2, '0')).join(' '));
        
        const signatureArray = new Uint8Array(signature.match(/.{1,2}/g).map(byte => parseInt(byte, 16)));
        console.log('[DEBUG] verify - 签名数组长度:', signatureArray.length);
        
        const result = await window.crypto.subtle.verify(
            "RSASSA-PKCS1-v1_5",
            publicKey,
            signatureArray,
            dataBuffer
        );
        
        console.log('[DEBUG] verify - 验证结果:', result);
        return result;
    }

    static generateNonce() {
        const timestamp = Math.floor(Date.now() / 1000);
        const random = Math.random().toString(36).substring(2, 10);
        return `${timestamp}_${random}`;
    }

    static createSignData(contractAddress, method, params, timestamp, nonce) {
        return {
            contract_address: contractAddress,
            method: method,
            params: params,
            timestamp: timestamp,
            nonce: nonce
        };
    }
}

class ContractClient {
    constructor() {
        this.masterContractAddress = null;
        this.currentUser = null;
    }

    async init() {
        await this.loadCurrentUser();
        await this.loadMasterContractAddress();
    }

    async loadCurrentUser() {
        const token = localStorage.getItem('access_token');
        if (token) {
            try {
                const payload = JSON.parse(atob(token.split('.')[1]));
                this.currentUser = {
                    address: payload.sub,
                    username: payload.username,
                    role: payload.role,
                    public_key: payload.public_key
                };
            } catch (e) {
                console.error('加载用户信息失败:', e);
            }
        }
    }

    async loadMasterContractAddress() {
        try {
            const response = await fetch('/api/contract/stats');
            const data = await response.json();
            if (data.success && data.stats) {
                this.masterContractAddress = data.stats.master_contract_address;
            }
        } catch (e) {
            console.error('加载主链地址失败:', e);
        }
    }

    async createRecord(aircraftRegistration, maintenanceType, description, technicianAddress) {
        if (!this.currentUser) {
            throw new Error('用户未登录');
        }

        const privateKey = localStorage.getItem('private_key');
        if (!privateKey) {
            throw new Error('私钥不存在，请重新登录');
        }

        const privateKeyObj = await SignatureUtils.importPrivateKey(privateKey);
        const nonce = SignatureUtils.generateNonce();
        const timestamp = Math.floor(Date.now() / 1000);

        const signData = SignatureUtils.createSignData(
            this.masterContractAddress,
            'createRecord',
            {
                aircraft_registration: aircraftRegistration,
                maintenance_type: maintenanceType,
                description: description,
                technician_address: technicianAddress
            },
            timestamp,
            nonce
        );

        const signature = await SignatureUtils.sign(privateKeyObj, signData);

        console.log('[DEBUG] 签名数据:', signData);
        console.log('[DEBUG] 签名结果:', signature);
        console.log('[DEBUG] 签名长度:', signature.length);

        const token = localStorage.getItem('access_token');
        
        const publicKey = await SignatureUtils.importPublicKey(this.currentUser.public_key);
        
        console.log('[DEBUG] 测试私钥和公钥是否匹配...');
        const testData = { test: 'data', timestamp: Date.now() };
        const testSignature = await SignatureUtils.sign(privateKeyObj, testData);
        const testValid = await SignatureUtils.verify(publicKey, testSignature, testData);
        console.log('[DEBUG] 测试签名验证结果:', testValid);
        
        if (!testValid) {
            console.error('[ERROR] 私钥和公钥不匹配！');
            throw new Error('私钥和公钥不匹配，请重新登录');
        }
        
        const isValid = await SignatureUtils.verify(publicKey, signature, signData);
        console.log('[DEBUG] 前端验证签名结果:', isValid);
        
        if (!isValid) {
            console.error('[ERROR] 前端签名验证失败！');
            throw new Error('签名验证失败');
        }

        const response = await fetch('/api/contract/create-record', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                aircraft_registration: aircraftRegistration,
                maintenance_type: maintenanceType,
                description: description,
                technician_address: technicianAddress,
                signature: signature,
                nonce: nonce,
                timestamp: timestamp
            })
        });

        return await response.json();
    }

    async approveRecord(recordId, approverAddress) {
        if (!this.currentUser) {
            throw new Error('用户未登录');
        }

        const privateKey = localStorage.getItem('private_key');
        if (!privateKey) {
            throw new Error('私钥不存在，请重新登录');
        }

        const privateKeyObj = await SignatureUtils.importPrivateKey(privateKey);
        const nonce = SignatureUtils.generateNonce();
        const timestamp = Math.floor(Date.now() / 1000);

        const signData = SignatureUtils.createSignData(
            this.masterContractAddress,
            'approveRecord',
            {
                record_id: recordId,
                approver_address: approverAddress
            },
            timestamp,
            nonce
        );

        const signature = await SignatureUtils.sign(privateKeyObj, signData);

        const token = localStorage.getItem('access_token');
        const response = await fetch('/api/contract/approve-record', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                record_id: recordId,
                approver_address: approverAddress,
                signature: signature,
                nonce: nonce,
                timestamp: timestamp
            })
        });

        return await response.json();
    }

    async releaseRecord(recordId, approverAddress) {
        if (!this.currentUser) {
            throw new Error('用户未登录');
        }

        const privateKey = localStorage.getItem('private_key');
        if (!privateKey) {
            throw new Error('私钥不存在，请重新登录');
        }

        const privateKeyObj = await SignatureUtils.importPrivateKey(privateKey);
        const nonce = SignatureUtils.generateNonce();
        const timestamp = Math.floor(Date.now() / 1000);

        const signData = SignatureUtils.createSignData(
            this.masterContractAddress,
            'releaseRecord',
            {
                record_id: recordId,
                approver_address: approverAddress
            },
            timestamp,
            nonce
        );

        const signature = await SignatureUtils.sign(privateKeyObj, signData);

        const token = localStorage.getItem('access_token');
        const response = await fetch('/api/contract/release-record', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                record_id: recordId,
                approver_address: approverAddress,
                signature: signature,
                nonce: nonce,
                timestamp: timestamp
            })
        });

        return await response.json();
    }

    async getRecord(recordId) {
        const response = await fetch(`/api/contract/records/${recordId}`);
        return await response.json();
    }

    async getAircraftRecords(aircraftRegistration, status = null) {
        let url = `/api/contract/aircraft/${aircraftRegistration}`;
        if (status) {
            url += `?status=${status}`;
        }
        const response = await fetch(url);
        return await response.json();
    }

    async getStats() {
        const response = await fetch('/api/contract/stats');
        return await response.json();
    }

    async getBlocks() {
        const response = await fetch('/api/contract/blocks');
        return await response.json();
    }

    async getEvents(contractAddress = null) {
        let url = '/api/contract/events';
        if (contractAddress) {
            url += `?contract_address=${contractAddress}`;
        }
        const response = await fetch(url);
        return await response.json();
    }

    async verifyBlockchain() {
        const response = await fetch('/api/contract/verify');
        return await response.json();
    }
}

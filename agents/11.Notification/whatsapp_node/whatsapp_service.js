const express = require('express');
const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');

const app = express();
app.use(express.json());

const port = process.env.PORT || 3000;

// Initialize WhatsApp client
const client = new Client({
    authStrategy: new LocalAuth(),
    puppeteer: {
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    }
});

let qrCodeData = null;
let isReady = false;

client.on('qr', (qr) => {
    qrCodeData = qr;
    qrcode.generate(qr, { small: true });
    console.log('WhatsApp QR Code generated. Scan this QR code with your phone to link account.');
});

client.on('ready', () => {
    isReady = true;
    console.log('WhatsApp Web Client is ready!');
});

client.on('auth_failure', msg => {
    console.error('AUTHENTICATION FAILURE', msg);
});

client.on('disconnected', (reason) => {
    isReady = false;
    console.log('WhatsApp Client was logged out', reason);
});

client.initialize();

app.post('/send', async (req, res) => {
    const { phone, message } = req.body;
    
    if (!phone || !message) {
        return res.status(400).json({ error: 'Missing phone or message parameter' });
    }

    if (!isReady) {
        // Fallback: log the message locally if the QR code hasn't been scanned yet
        console.log(`[WhatsApp Sandbox Mode - NOT LINKED] Message to ${phone}: ${message}`);
        return res.json({ 
            status: 'SANDBOX_LOGGED', 
            note: 'WhatsApp Web client is not authenticated yet. Logged message to console.',
            message 
        });
    }

    try {
        // Format phone to WhatsApp jid: e.g. +918610500527 -> 918610500527@c.us
        const cleanPhone = phone.replace(/[^0-9]/g, '');
        const jid = `${cleanPhone}@c.us`;
        
        await client.sendMessage(jid, message);
        console.log(`Successfully sent WhatsApp alert to ${phone}`);
        return res.json({ status: 'SENT', phone, message });
    } catch (err) {
        console.error('Error sending WhatsApp message:', err);
        return res.status(500).json({ error: err.message });
    }
});

app.get('/status', (req, res) => {
    res.json({ ready: isReady, qr: qrCodeData });
});

app.listen(port, () => {
    console.log(`WhatsApp Web Service listening on port ${port}`);
});

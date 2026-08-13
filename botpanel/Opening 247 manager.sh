const express = require('express');
const session = require('express-session');
const path = require('path');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(express.urlencoded({ extended: true }));
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

app.use(session({
    secret: process.env.SESSION_SECRET || 'default-secret-string',
    resave: false,
    saveUninitialized: false
}));

// Authentication Middleware
function isAuthenticated(req, res, next) {
    if (req.session && req.session.loggedIn) {
        return next();
    }
    res.redirect('/login.html');
}

// Routes
app.post('/api/login', (req, res) => {
    const { password } = req.body;
    const adminPassword = process.env.PANEL_PASSWORD || 'change-me';

    if (password === adminPassword) {
        req.session.loggedIn = true;
        return res.json({ success: true, redirect: '/index.html' });
    }
    res.status(401).json({ success: false, message: 'Invalid password' });
});

app.get('/api/logout', (req, res) => {
    req.session.destroy(() => {
        res.redirect('/login.html');
    });
});

// Protected Panel View
app.get('/index.html', isAuthenticated, (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

// Import Bot Controller Routes if available
try {
    const botController = require('./botController');
    app.post('/api/bot/start', isAuthenticated, botController.startBot);
    app.post('/api/bot/stop', isAuthenticated, botController.stopBot);
    app.post('/api/bot/restart', isAuthenticated, botController.restartBot);
    app.get('/api/bot/logs', isAuthenticated, botController.getLogs);
} catch (e) {
    console.log('⚠️ botController.js not linked yet.');
}

app.listen(PORT, () => {
    console.log(`🚀 Server is running smoothly on http://localhost:${PORT}`);
});

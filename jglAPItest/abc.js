
const axios = require('axios');

async function authenticateWildApricot(apiKey, clientSecret) {
    try {
        const authString = Buffer.from(`${apiKey}:${clientSecret}`).toString('base64');
        const response = await axios.post('https://oauth.wildapricot.org/auth/token', null, {
            headers: {
                'Authorization': `Basic ${authString}`,
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            params: {
                grant_type: 'client_credentials',
                scope: 'auto'
            }
        });
        return response.data.access_token;
    } catch (error) {
        console.warn('Authentication with client secret failed, trying API key only...');
        const fallbackAuthString = Buffer.from(`APIKEY:${apiKey}`).toString('base64');
        const fallbackResponse = await axios.post('https://oauth.wildapricot.org/auth/token', null, {
            headers: {
                'Authorization': `Basic ${fallbackAuthString}`,
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            params: {
                grant_type: 'client_credentials',
                scope: 'auto'
            }
        });
        return fallbackResponse.data.access_token;
    }
}

async function getAccountId(apiKey, clientSecret) {
    try {
        const accessToken = await authenticateWildApricot(apiKey, clientSecret);
        const response = await axios.get('https://api.wildapricot.org/v2.2/accounts', {
            headers: { 'Authorization': `Bearer ${accessToken}` }
        });
        console.log('Available Accounts:');
        response.data.forEach(account => {
            console.log(`ID: ${account.Id}, Name: ${account.Name}, URL: ${account.Url}`);
        });
        return response.data;
    } catch (error) {
        console.error('Error fetching accounts:', error.response?.data?.error_description || error.message);
        throw error;
    }
}

// Example usage
const apiKey = '1bh9vtebz08j5rz0ql4lyi5imkjpxq'; // Replace with your API key
const clientSecret = 's9wq6e5v5eel3ey1llmxov664t6brv'; // Replace with your client secret

getAccountId(apiKey, clientSecret)
    .then(accounts => console.log('Successfully retrieved account list!'))
    .catch(err => console.error('Failed to retrieve accounts:', err));
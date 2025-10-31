const axios = require('axios');

async function getWildApricotContacts(apiKey, accountId) {
    try {
        // Step 1: Obtain an access token
        const authResponse = await axios.post('https://oauth.wildapricot.org/auth/token', null, {
            headers: {
                'Authorization': 'Basic ' + Buffer.from(`APIKEY:${apiKey}`).toString('base64'),
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            params: {
                grant_type: 'client_credentials',
                scope: 'auto'
            }
        });

        const accessToken = authResponse.data.access_token;

        // Step 2: Fetch all contacts
        let allContacts = [];
        let continuationToken = null;
        const selectFields = 'FirstName,LastName,Email'; // Adjust fields as needed
        const filter = 'Archived eq false'; // Exclude archived contacts

        do {
            const params = {
                $async: false, // Synchronous request
                $select: selectFields,
                $filter: filter
            };

            if (continuationToken) {
                params.$continuationToken = continuationToken;
            }

            const contactsResponse = await axios.get(`https://api.wildapricot.org/v2.2/accounts/${accountId}/contacts`, {
                headers: {
                    'Authorization': `Bearer ${accessToken}`
                },
                params: params
            });

            const contactsData = contactsResponse.data;
            allContacts = allContacts.concat(contactsData.Contacts);

            // Check for continuation token for pagination
            continuationToken = contactsData.ResultContinuation;

        } while (continuationToken);

        // Output the contacts
        console.log(`Retrieved ${allContacts.length} contacts:`);
        allContacts.forEach(contact => {
            console.log(`${contact.FirstName} ${contact.LastName} - ${contact.Email}`);
        });

        return allContacts;

    } catch (error) {
        console.error('Error fetching contacts:', error.response ? error.response.data : error.message);
        throw error;
    }
}

// Example usage
const apiKey = '1bh9vtebz08j5rz0ql4lyi5imkjpxq'; // Replace with your Wild Apricot API key
const accountId = 'ID1'; // Replace with your Wild Apricot account ID

getWildApricotContacts(apiKey, accountId)
    .then(contacts => console.log('All contacts retrieved successfully!'))
    .catch(err => console.error('Failed to retrieve contacts:', err));

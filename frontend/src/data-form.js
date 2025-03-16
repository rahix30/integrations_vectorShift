import { useState } from 'react';
import {
    Box,
    TextField,
    Button,
    List,
    ListItem,
    ListItemText,
    Typography,
    Paper,
} from '@mui/material';
import axios from 'axios';

const endpointMapping = {
    'Notion': 'notion',
    'Airtable': 'airtable',
    'HubSpot': 'hubspot'
};

export const DataForm = ({ integrationType, credentials }) => {
    const [loadedData, setLoadedData] = useState(null);
    const endpoint = endpointMapping[integrationType];

    const handleLoad = async () => {
        try {
            const formData = new FormData();
            formData.append('credentials', JSON.stringify(credentials));
            const response = await axios.post(`http://localhost:8000/integrations/${endpoint}/load`, formData);
            const data = response.data;
            setLoadedData(data);
        } catch (e) {
            alert(e?.response?.data?.detail);
        }
    }

    const formatDate = (dateString) => {
        if (!dateString) return 'N/A';
        return new Date(dateString).toLocaleString();
    };

    return (
        <Box display='flex' justifyContent='center' alignItems='center' flexDirection='column' width='100%'>
            <Box display='flex' flexDirection='column' width='100%'>
                {loadedData && (
                    <Paper elevation={3} sx={{ mt: 2, p: 2, maxHeight: 400, overflow: 'auto' }}>
                        <Typography variant="h6" gutterBottom>
                            HubSpot Contacts
                        </Typography>
                        <List>
                            {loadedData.map((contact, index) => (
                                <ListItem key={index} divider>
                                    <ListItemText
                                        primary={contact.name}
                                        secondary={
                                            <>
                                                <Typography component="span" variant="body2">
                                                    Created: {formatDate(contact.creation_time)}
                                                </Typography>
                                                <br />
                                                <Typography component="span" variant="body2">
                                                    Last Modified: {formatDate(contact.last_modified_time)}
                                                </Typography>
                                                <br />
                                                <Typography component="span" variant="body2">
                                                    <a href={contact.url} target="_blank" rel="noopener noreferrer">
                                                        View in HubSpot
                                                    </a>
                                                </Typography>
                                            </>
                                        }
                                    />
                                </ListItem>
                            ))}
                        </List>
                    </Paper>
                )}
                <Button
                    onClick={handleLoad}
                    sx={{mt: 2}}
                    variant='contained'
                >
                    Load Data
                </Button>
                <Button
                    onClick={() => setLoadedData(null)}
                    sx={{mt: 1}}
                    variant='contained'
                >
                    Clear Data
                </Button>
            </Box>
        </Box>
    );
}

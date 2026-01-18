import { useEffect, useRef } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import api from '../api'; 

export default function GoogleCallback() {
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();
    const code = searchParams.get('code');
    const processedRef = useRef(false);

    useEffect(() => {
        if (code && !processedRef.current) {
            processedRef.current = true; 
            api.post('/v1/auth/google/', { code: code })
                .then(res => {
                    localStorage.setItem('access_token', res.data.access);
                    localStorage.setItem('refresh_token', res.data.refresh);
                    window.location.href = "/dashboard"; 
                })
                .catch(err => {
                    console.error("Login Failed:", err);
                });
        }
    }, [code, navigate]);

    return <div>Processing Google Login...</div>;
}
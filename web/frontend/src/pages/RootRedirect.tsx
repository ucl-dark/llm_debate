
import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useUser } from '../hooks/userProvider';

export default function RootRedirect() {
  const navigate = useNavigate();
  const { user, loading } = useUser();

  useEffect(() => {
    if (loading) {
      return
    }
    if (!user) {
      navigate('/login');
    } else if (user.admin) {
      navigate('/files');
    } else {
      navigate('/experiments');
    }
  }, [user, loading, navigate]);

  return null;
};

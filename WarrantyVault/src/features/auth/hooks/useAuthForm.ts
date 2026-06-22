import { useState } from 'react';

import { authService } from '../services/authService';

type Mode = 'signIn' | 'signUp' | 'reset';

/** Drives the auth screens: local field state, submission, and error display. */
export function useAuthForm(mode: Mode) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);

  async function submit(): Promise<void> {
    setLoading(true);
    setError(null);
    setInfo(null);

    const result =
      mode === 'signUp'
        ? await authService.signUp(email, password)
        : mode === 'reset'
          ? await authService.resetPassword(email)
          : await authService.signIn(email, password);

    setLoading(false);
    if (!result.ok) {
      setError(result.error.message);
      return;
    }
    if (mode === 'reset') setInfo('Check your email for a reset link.');
    if (mode === 'signUp') setInfo('Account created. Check your email to confirm.');
  }

  return { email, setEmail, password, setPassword, loading, error, info, submit };
}

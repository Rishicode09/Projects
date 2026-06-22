import type { Session, User } from '@supabase/supabase-js';
import { create } from 'zustand';

import { supabase } from '@/lib/supabase';

interface AuthState {
  session: Session | null;
  user: User | null;
  /** True until the initial session has been restored from storage. */
  initializing: boolean;
  setSession: (session: Session | null) => void;
  initialize: () => Promise<void>;
  signOut: () => Promise<void>;
}

/**
 * Global auth store. `initialize` restores any persisted session and subscribes
 * to Supabase auth changes so the UI reacts to sign-in / sign-out / refresh.
 */
export const useAuthStore = create<AuthState>((set) => ({
  session: null,
  user: null,
  initializing: true,

  setSession: (session) => set({ session, user: session?.user ?? null }),

  initialize: async () => {
    const { data } = await supabase.auth.getSession();
    set({ session: data.session, user: data.session?.user ?? null, initializing: false });

    supabase.auth.onAuthStateChange((_event, session) => {
      set({ session, user: session?.user ?? null });
    });
  },

  signOut: async () => {
    await supabase.auth.signOut();
    set({ session: null, user: null });
  },
}));

import type { Session, User } from '@supabase/supabase-js';
import { create } from 'zustand';

import { demoAuth } from '@/lib/demo/demoAuth';
import { env } from '@/lib/env';
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
    if (!env.isConfigured) {
      // Demo mode: local session + subscription. The demo session shape is a
      // structural subset of Supabase's Session for the fields the app reads.
      const session = await demoAuth.getSession();
      set({
        session: session as unknown as Session | null,
        user: (session?.user ?? null) as unknown as User | null,
        initializing: false,
      });
      demoAuth.onChange((s) =>
        set({
          session: s as unknown as Session | null,
          user: (s?.user ?? null) as unknown as User | null,
        })
      );
      return;
    }

    const { data } = await supabase.auth.getSession();
    set({ session: data.session, user: data.session?.user ?? null, initializing: false });

    supabase.auth.onAuthStateChange((_event, session) => {
      set({ session, user: session?.user ?? null });
    });
  },

  signOut: async () => {
    if (!env.isConfigured) {
      await demoAuth.signOut();
      set({ session: null, user: null });
      return;
    }
    await supabase.auth.signOut();
    set({ session: null, user: null });
  },
}));

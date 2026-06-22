import AsyncStorage from '@react-native-async-storage/async-storage';

import { uid } from '@/lib/id';

import { seedDemoData } from './demoDb';

/**
 * Local, offline auth backend used when Supabase isn't configured. It stores
 * accounts + the active session in AsyncStorage and notifies subscribers on
 * change, mirroring the shape the app expects from Supabase auth. This lets the
 * whole app be used and demoed without any backend setup.
 */
export interface DemoUser {
  id: string;
  email: string;
}

export interface DemoSession {
  user: DemoUser;
  access_token: string;
}

const USERS_KEY = 'demo:auth:users';
const SESSION_KEY = 'demo:auth:session';

type Listener = (session: DemoSession | null) => void;
const listeners = new Set<Listener>();

function notify(session: DemoSession | null): void {
  listeners.forEach((l) => l(session));
}

type StoredUser = { id: string; password: string };

async function readUsers(): Promise<Record<string, StoredUser>> {
  const raw = await AsyncStorage.getItem(USERS_KEY);
  return raw ? (JSON.parse(raw) as Record<string, StoredUser>) : {};
}

async function writeUsers(users: Record<string, StoredUser>): Promise<void> {
  await AsyncStorage.setItem(USERS_KEY, JSON.stringify(users));
}

async function setSession(session: DemoSession | null): Promise<void> {
  if (session) {
    await AsyncStorage.setItem(SESSION_KEY, JSON.stringify(session));
  } else {
    await AsyncStorage.removeItem(SESSION_KEY);
  }
  notify(session);
}

export const demoAuth = {
  async signUp(email: string, password: string): Promise<void> {
    const key = email.trim().toLowerCase();
    const users = await readUsers();
    if (users[key]) {
      throw new Error('An account with this email already exists. Try signing in.');
    }
    const id = uid();
    users[key] = { id, password };
    await writeUsers(users);
    await seedDemoData(id); // give new demo accounts sample products
    await setSession({ user: { id, email: key }, access_token: 'demo-token' });
  },

  async signIn(email: string, password: string): Promise<void> {
    const key = email.trim().toLowerCase();
    const users = await readUsers();
    const found = users[key];
    if (!found || found.password !== password) {
      throw new Error('Invalid email or password.');
    }
    await setSession({ user: { id: found.id, email: key }, access_token: 'demo-token' });
  },

  async signOut(): Promise<void> {
    await setSession(null);
  },

  async getSession(): Promise<DemoSession | null> {
    const raw = await AsyncStorage.getItem(SESSION_KEY);
    return raw ? (JSON.parse(raw) as DemoSession) : null;
  },

  onChange(cb: Listener): () => void {
    listeners.add(cb);
    return () => listeners.delete(cb);
  },
};

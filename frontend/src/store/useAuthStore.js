import { create } from 'zustand';
import { persist } from 'zustand/middleware';

const useAuthStore = create(
  persist(
    (set) => ({
      user: null,
      token: null,
      refreshToken: null,
      setAuth: (user, token, refreshToken) => set({ user, token, refreshToken }),
      setToken: (token) => set({ token }),
      setUser: (user) => set({ user }),
      logout: () => set({ user: null, token: null, refreshToken: null }),
    }),
    { name: 'auth-storage' }
  )
);

export default useAuthStore;

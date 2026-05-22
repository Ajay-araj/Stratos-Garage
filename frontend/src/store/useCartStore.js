import { create } from 'zustand';
import { persist } from 'zustand/middleware';

/**
 * Lightweight local cache — only tracks item count for the navbar badge.
 * The authoritative cart lives in the backend (orders/cart/).
 * Cart.jsx and Checkout.jsx both fetch from the backend directly.
 */
const useCartStore = create(
  persist(
    (set, get) => ({
      itemCount: 0,
      // Called after a successful backend cart/add response to refresh the badge
      setItemCount: (count) => set({ itemCount: count }),
      incrementCount: () => set({ itemCount: get().itemCount + 1 }),
      decrementCount: () => set({ itemCount: Math.max(0, get().itemCount - 1) }),
      clearCount: () => set({ itemCount: 0 }),

      // Legacy local cart kept for unauthenticated guest mode (not used in authenticated flow)
      items: [],
      addItem: (product, quantity = 1) => {
        const items = get().items;
        const existingItem = items.find(item => item.product?.id === product.id);
        if (existingItem) {
          set({ items: items.map(item => item.product?.id === product.id ? { ...item, quantity: item.quantity + quantity } : item) });
        } else {
          set({ items: [...items, { product, quantity }] });
        }
        set({ itemCount: get().items.reduce((sum, i) => sum + i.quantity, 0) + (existingItem ? 0 : quantity) });
      },
      removeItem: (productId) => {
        set({ items: get().items.filter(item => item.product?.id !== productId) });
        set({ itemCount: get().items.reduce((sum, i) => sum + i.quantity, 0) });
      },
      clearCart: () => set({ items: [], itemCount: 0 }),
    }),
    { name: 'cart-storage' }
  )
);

export default useCartStore;

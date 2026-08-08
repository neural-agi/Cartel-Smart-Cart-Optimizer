import type { Product } from "./product";

export interface CartItem {
  itemId: string;
  product: Product;
  quantity: number;
}

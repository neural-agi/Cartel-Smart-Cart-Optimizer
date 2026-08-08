export interface ProductMoney {
  currency: string;
  minorUnits: number;
}

/** Frontend projection of a product/listing result from Product Intelligence. */
export interface Product {
  productId: string;
  variantId?: string;
  listingId?: string;
  name: string;
  brand?: string;
  pack?: string;
  platform: string;
  price?: ProductMoney;
  availability?: string;
  imageUrl?: string;
}
